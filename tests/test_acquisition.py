import hashlib
import json
from datetime import datetime
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from airaware.acquisition import AcquisitionError, AcquisitionSpec, ingest_file

CSV = b"fecha,valor\n20260101,12.5\n"


def spec(**changes):
    return AcquisitionSpec.model_validate(
        {
            "source_id": "demo",
            "resource_url": "https://example.org/data.csv",
            "method": "lightpanda",
            "format": "csv",
            "max_bytes": 1024,
            **changes,
        }
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"source_id": "../escape"},
        {"max_bytes": 0},
        {"max_bytes": True},
        {"resource_url": "https://user:secret@example.org/file"},
        {"resource_url": "https://example.org/file?api_key=secret"},
        {"resource_url": "https://example.org/file#secret"},
        {"expected_sha256": "incorrecta"},
        {"format": "exe"},
        {"acquired_at": "2026-01-01T00:00:00"},
        {"format": "json"},
    ],
)
def test_invalid_contract_is_rejected(changes):
    with pytest.raises(ValidationError):
        spec(**changes)


def test_local_import_is_atomic_and_preserves_provenance(tmp_path):
    original = tmp_path / "input.csv"
    original.write_bytes(CSV)
    request = spec(expected_sha256=hashlib.sha256(CSV).hexdigest())
    result = ingest_file(request, original, tmp_path / "data")
    assert original.read_bytes() == result.artifact.read_bytes() == CSV
    manifest = json.loads(result.manifest.read_text())
    assert manifest["sha256"] == hashlib.sha256(CSV).hexdigest()
    assert manifest["size_bytes"] == len(CSV)
    assert manifest["spec"]["method"] == "lightpanda"
    assert manifest["spec"]["acquired_at"] is None
    assert datetime.fromisoformat(manifest["verified_at"]).tzinfo is not None
    assert manifest["http_status"] is None
    assert manifest["storage"] == "bundle"
    assert not result.reused
    assert not list(result.manifest.parent.parent.glob(".pending-*"))
    second = ingest_file(request, original, tmp_path / "data")
    assert second.reused
    assert second.manifest.read_bytes() == result.manifest.read_bytes()


def test_existing_raw_file_is_referenced_without_copy_or_modification(tmp_path):
    raw = tmp_path / "data/raw/demo"
    raw.mkdir(parents=True)
    original = raw / "legacy.csv"
    original.write_bytes(CSV)
    before = original.stat()
    result = ingest_file(spec(), original, tmp_path / "data")
    assert result.artifact == original
    assert result.reused
    assert json.loads(result.manifest.read_text())["storage"] == "reference"
    assert original.stat().st_mtime_ns == before.st_mtime_ns
    assert len(list(raw.rglob("*.csv"))) == 1


@pytest.mark.parametrize(
    "content,changes",
    [
        (b"<html><body>Acceso denegado</body></html>", {}),
        (b"a,b\n1,2,3\n", {}),
        (b"a,a\n1,2\n", {}),
        (b"", {}),
        (CSV, {"max_bytes": 3}),
        (CSV, {"expected_sha256": "0" * 64}),
        (b'{"value":NaN}', {"format": "json", "json_required_keys": ("value",)}),
        (b'{"other":2}', {"format": "json", "json_required_keys": ("value",)}),
        (b'{"value":1,"value":2}', {"format": "json", "json_required_keys": ("value",)}),
    ],
)
def test_invalid_artifact_is_never_published(tmp_path, content, changes):
    original = tmp_path / "input"
    original.write_bytes(content)
    with pytest.raises(AcquisitionError):
        ingest_file(spec(**changes), original, tmp_path / "data")
    assert not list((tmp_path / "data").rglob("manifest.json"))
    assert not list((tmp_path / "data").rglob(".pending-*"))


def test_json_contract_preserves_bytes(tmp_path):
    original = tmp_path / "input.json"
    original.write_bytes(b'{"measurements": []}\n')
    result = ingest_file(
        spec(format="json", json_required_keys=("measurements",)), original, tmp_path / "data"
    )
    assert result.artifact.read_bytes() == original.read_bytes()


@pytest.mark.parametrize(
    "format,member,root",
    [
        ("xlsx", "xl/workbook.xml", "http://schemas.openxmlformats.org/spreadsheetml/2006/main"),
        (
            "docx",
            "word/document.xml",
            "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        ),
    ],
)
def test_office_container_requires_real_xml_members(tmp_path, format, member, root):
    original = tmp_path / "document.zip"
    with ZipFile(original, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
        )
        archive.writestr(
            member, f'<{"workbook" if format == "xlsx" else "document"} xmlns="{root}"/>'
        )
    result = ingest_file(spec(format=format, max_bytes=4096), original, tmp_path / "data")
    assert result.artifact.read_bytes() == original.read_bytes()
    with ZipFile(original, "w") as archive:
        archive.writestr(member, "<html/>")
    with pytest.raises(AcquisitionError):
        ingest_file(spec(format=format), original, tmp_path / "data")


def test_corrupt_existing_bundle_is_not_reused_or_overwritten(tmp_path):
    original = tmp_path / "input.csv"
    original.write_bytes(CSV)
    result = ingest_file(spec(), original, tmp_path / "data")
    result.artifact.write_bytes(b"corrupto")
    with pytest.raises(AcquisitionError):
        ingest_file(spec(), original, tmp_path / "data")
    assert result.artifact.read_bytes() == b"corrupto"


def test_symlinked_destination_is_rejected(tmp_path):
    original = tmp_path / "input.csv"
    original.write_bytes(CSV)
    external = tmp_path / "external"
    external.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    (data / "raw").symlink_to(external, target_is_directory=True)
    with pytest.raises(AcquisitionError):
        ingest_file(spec(), original, data)
    assert not list(external.iterdir())


def test_office_doctype_cannot_bypass_checks_with_utf16(tmp_path):
    original = tmp_path / "document.zip"
    with ZipFile(original, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("_rels/.rels", "<Relationships/>")
        xml = (
            '<?xml version="1.0" encoding="UTF-16"?>'
            '<!DOCTYPE workbook [<!ENTITY value "expanded">]>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "&value;</workbook>"
        )
        archive.writestr("xl/workbook.xml", xml.encode("utf-16"))
    with pytest.raises(AcquisitionError):
        ingest_file(spec(format="xlsx", max_bytes=4096), original, tmp_path / "data")


def test_csv_nul_bytes_are_rejected(tmp_path):
    original = tmp_path / "input.csv"
    original.write_bytes(b"a,b\n1,\x00\n")
    with pytest.raises(AcquisitionError):
        ingest_file(spec(), original, tmp_path / "data")


def test_interrupted_copy_removes_pending_files(tmp_path):
    from airaware.acquisition.store import ingest_chunks

    def interrupted():
        yield b"fecha,valor\n"
        raise OSError("private-path")

    with pytest.raises(AcquisitionError) as error:
        ingest_chunks(spec(), interrupted(), tmp_path / "data")
    assert "private-path" not in str(error.value)
    assert not list((tmp_path / "data").rglob("manifest.json"))
    assert not list((tmp_path / "data").rglob(".pending-*"))


def test_failed_publish_preserves_original_and_leaves_no_visible_bundle(tmp_path, monkeypatch):
    original = tmp_path / "input.csv"
    original.write_bytes(CSV)

    def fail_publish(*args):
        raise OSError("disco lleno")

    monkeypatch.setattr("airaware.acquisition.store.os.rename", fail_publish)
    with pytest.raises(AcquisitionError):
        ingest_file(spec(), original, tmp_path / "data")
    assert original.read_bytes() == CSV
    assert not list((tmp_path / "data").rglob("manifest.json"))
    assert not list((tmp_path / "data").rglob(".pending-*"))


def test_malformed_manifest_does_not_destroy_existing_bytes(tmp_path):
    original = tmp_path / "input.csv"
    original.write_bytes(CSV)
    result = ingest_file(spec(), original, tmp_path / "data")
    result.manifest.write_text('{"artifact_path": "../escape"}')
    with pytest.raises(AcquisitionError):
        ingest_file(spec(), original, tmp_path / "data")
    assert result.artifact.read_bytes() == CSV
    assert result.manifest.read_text() == '{"artifact_path": "../escape"}'


def test_competing_writer_fails_without_overwriting(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from airaware.acquisition.store import ingest_chunks

    reading, release = Event(), Event()
    original = tmp_path / "input.csv"
    original.write_bytes(CSV)

    def slow_bytes():
        reading.set()
        assert release.wait(5)
        yield CSV

    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(ingest_chunks, spec(), slow_bytes(), tmp_path / "data")
        try:
            assert reading.wait(5)
            with pytest.raises(AcquisitionError):
                ingest_file(spec(), original, tmp_path / "data")
        finally:
            release.set()
        result = first.result(timeout=5)
    assert result.artifact.read_bytes() == CSV
    assert len(list((tmp_path / "data").rglob("manifest.json"))) == 1


def test_reference_detects_external_change_on_reuse(tmp_path):
    original = tmp_path / "data/raw/demo/legacy.csv"
    original.parent.mkdir(parents=True)
    original.write_bytes(CSV)
    result = ingest_file(spec(), original, tmp_path / "data")
    original.write_bytes(b"fecha,valor\n20260101,99\n")
    # Comprobar el paquete anterior detecta cambios sin confiar solo en el nombre SHA.
    from airaware.acquisition.store import verify_bundle

    with pytest.raises(AcquisitionError):
        verify_bundle(spec(), tmp_path / "data/raw", result.manifest.parent)
