import json

import pytest
from pydantic import ValidationError

from airaware.acquisition.batch import AcquisitionJob, select_jobs
from airaware.acquisition.cache import TransferCache
from airaware.acquisition.models import AcquisitionError, AcquisitionSpec
from airaware.acquisition.store import ingest_file, verify_bundle


def spec(**changes):
    return AcquisitionSpec.model_validate(
        {
            "source_id": "dialect-demo",
            "resource_url": "https://example.org/data.csv",
            "method": "local",
            "format": "csv",
            "max_bytes": 1024,
            **changes,
        }
    )


def test_semicolon_csv_preserves_quoted_fields_and_original_bytes(tmp_path):
    data = b'name;value\n"station;one";"1,25"\n'
    f = tmp_path / "source.csv"
    f.write_bytes(data)
    result = ingest_file(spec(csv_delimiter=";"), f, tmp_path / "data")
    assert result.artifact.read_bytes() == data
    assert json.loads(result.manifest.read_text())["spec"]["csv_delimiter"] == ";"
    assert ingest_file(spec(csv_delimiter=";"), f, tmp_path / "data").reused


@pytest.mark.parametrize("data", [b"a;b\n1\n", b"a;a\n1;2\n", b"a;b\n1;2;3\n"])
def test_invalid_semicolon_structure_is_not_accepted(tmp_path, data):
    f = tmp_path / "bad.csv"
    f.write_bytes(data)
    with pytest.raises(AcquisitionError):
        ingest_file(spec(csv_delimiter=";"), f, tmp_path / "data")


def test_wrong_delimiter_cannot_reuse_a_verified_bundle(tmp_path):
    f = tmp_path / "data.csv"
    f.write_bytes(b"a;b\n1;2\n")
    result = ingest_file(spec(csv_delimiter=";"), f, tmp_path / "data")
    with pytest.raises(AcquisitionError):
        verify_bundle(spec(), tmp_path / "data/raw", result.manifest.parent)
    assert (
        TransferCache(spec(), tmp_path / "data").key
        != TransferCache(spec(csv_delimiter=";"), tmp_path / "data").key
    )


def test_legacy_comma_manifest_is_verified_without_rewrite(tmp_path):
    f = tmp_path / "data.csv"
    f.write_bytes(b"a,b\n1,2\n")
    result = ingest_file(spec(), f, tmp_path / "data")
    manifest = json.loads(result.manifest.read_text())
    manifest["spec"].pop("csv_delimiter")
    result.manifest.write_text(json.dumps(manifest))
    before = result.manifest.read_bytes()
    assert ingest_file(spec(), f, tmp_path / "data").reused
    assert result.manifest.read_bytes() == before
    # Clave de caché histórica de #7: identidad sin campos nuevos.
    import hashlib

    legacy = json.dumps(
        ("dialect-demo", "https://example.org/data.csv", "local", "csv", (), None),
        ensure_ascii=True,
    ).encode()
    assert TransferCache(spec(), tmp_path / "data").key == hashlib.sha256(legacy).hexdigest()


def test_batch_does_not_deduplicate_different_dialects(tmp_path):
    a = AcquisitionJob(spec=spec(), local_file=tmp_path / "a.csv")
    b = AcquisitionJob(spec=spec(csv_delimiter=";"), local_file=tmp_path / "b.csv")
    assert len(select_jobs([a, b])) == 2


@pytest.mark.parametrize("delimiter", ["", ";;", "\n", "|"])
def test_only_declared_supported_delimiters_are_allowed(delimiter):
    with pytest.raises(ValidationError):
        spec(csv_delimiter=delimiter)


def test_delimiter_does_not_describe_office_files():
    with pytest.raises(ValidationError):
        spec(format="xlsx", csv_delimiter=";")
