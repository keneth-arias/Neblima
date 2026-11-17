import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from airaware.catalog import Catalog, CatalogError, Source, load_catalog


def candidate(**changes: object) -> dict[str, object]:
    return {
        "source_id": "senamhi-lima",
        "name": "SENAMHI Lima",
        "catalog_url": "https://example.org/catalog",
        **changes,
    }


def test_discovery_preserves_unknowns_without_claiming_verification():
    source = Source.model_validate(candidate())
    assert source.status == "discovered"
    assert source.last_verified_at is None
    assert source.license is None
    assert source.redistribution == "unknown"
    assert source.historical_coverage is None
    assert source.data_category == "unknown"


def test_duplicate_source_ids_are_rejected():
    with pytest.raises(ValidationError, match="únicos"):
        Catalog.model_validate({"schema_version": 1, "sources": [candidate(), candidate()]})


@pytest.mark.parametrize("status", ["verified", "downloaded", "profiled", "integrated"])
def test_progress_requires_verification_evidence(status):
    with pytest.raises(ValidationError):
        Source.model_validate(candidate(status=status))


def test_integration_requires_rights_and_verified_measurement_semantics():
    with pytest.raises(ValidationError):
        Source.model_validate(
            candidate(
                status="integrated",
                last_verified_at="2026-11-15T00:00:00Z",
                notes="Archivo revisado",
            )
        )


@pytest.mark.parametrize("status", ["blocked", "excluded", "duplicate"])
def test_nonactive_sources_require_an_explanation(status):
    with pytest.raises(ValidationError):
        Source.model_validate(candidate(status=status))


@pytest.mark.parametrize("url", ["file:///tmp/data", "https://user:credential@example.org/data"])
def test_catalog_urls_reject_non_http_and_embedded_credentials(url):
    with pytest.raises(ValidationError):
        Source.model_validate(candidate(catalog_url=url))


def test_typo_fields_fail_instead_of_silently_disappearing():
    with pytest.raises(ValidationError):
        Source.model_validate(candidate(licence="CC-BY-4.0"))


@given(
    st.text().filter(
        lambda value: (
            value
            not in {
                "discovered",
                "verified",
                "downloaded",
                "profiled",
                "integrated",
                "blocked",
                "duplicate",
                "excluded",
            }
        )
    )
)
def test_unknown_status_is_never_accepted(status):
    with pytest.raises(ValidationError):
        Source.model_validate(candidate(status=status))


def test_unsafe_yaml_is_not_executed(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text("!!python/object/apply:os.system ['false']")
    with pytest.raises(CatalogError):
        load_catalog(path)


def test_errors_do_not_include_config_values(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "sources": [candidate(status="private-value")]})
    )
    with pytest.raises(CatalogError) as error:
        load_catalog(path)
    assert "private-value" not in str(error.value)


def test_repository_catalog_is_valid_and_has_candidates():
    catalog = load_catalog(Path(__file__).resolve().parents[1] / "configs/sources.yaml")
    assert len(catalog.sources) >= 30
    assert {"senamhi-lima", "oefa-national"} <= {s.source_id for s in catalog.sources}


def test_verified_source_with_timestamped_evidence_is_accepted():
    source = Source.model_validate(
        candidate(
            status="verified",
            last_verified_at="2026-11-15T12:00:00-05:00",
            notes="Catálogo oficial revisado y metodología de medición registrada.",
        )
    )
    assert source.status == "verified"
    assert source.redistribution == "unknown"


def test_integration_accepts_documented_rights_and_measurement_category():
    source = Source.model_validate(
        candidate(
            status="integrated",
            last_verified_at="2026-11-15T17:00:00Z",
            notes="Solo muestra de prueba: archivo y términos revisados.",
            license="CC-BY-4.0",
            license_url="https://example.org/license",
            redistribution="allowed",
            data_category="ground_measured",
        )
    )
    assert source.status == "integrated"


def test_naive_verification_timestamp_is_rejected():
    with pytest.raises(ValidationError, match="zona horaria"):
        Source.model_validate(
            candidate(status="verified", last_verified_at="2026-11-15T17:00:00", notes="Revisado")
        )


def test_missing_catalog_is_a_safe_error(tmp_path):
    with pytest.raises(CatalogError, match="No se pudo leer o validar"):
        load_catalog(tmp_path / "absent.yaml")


def test_inventory_has_dated_access_evidence_for_every_candidate():
    root = Path(__file__).resolve().parents[1]
    catalog = load_catalog(root / "configs/sources.yaml")
    evidence = json.loads((root / "metadata/source-access.json").read_text())
    rows = evidence["resources"]
    assert len(rows) == len(catalog.sources)
    assert len(catalog.sources) >= 40
    indexed = {row["source_id"]: row for row in rows}
    assert len(indexed) == len(rows)
    assert set(indexed) == {source.source_id for source in catalog.sources}
    for source in catalog.sources:
        row = indexed[source.source_id]
        assert row["requested_url"] == str(source.catalog_url)
        assert datetime.fromisoformat(row["checked_at"]).tzinfo is not None
        assert row["method"].startswith("Lightpanda")
        assert row["outcome"] in {"accessible", "partial", "blocked"}
        assert row["next_action"]
        assert source.last_verified_at is not None
        assert source.last_verified_at >= datetime.fromisoformat(row["checked_at"])
        assert source.notes
        if row["outcome"] == "partial":
            assert source.status == "discovered"
            assert row["reason"]
        if row["outcome"] == "accessible":
            if source.source_id == "oefa-csv":
                latest = json.loads((root / "metadata/oefa-lightpanda-download.json").read_text())
                assert source.status == "downloaded"
                assert latest["download_method"] == "Lightpanda download"
                assert latest["source_url"] in {str(u) for u in source.resource_urls}
                assert source.last_verified_at == datetime.fromisoformat(latest["verified_at_utc"])
                assert "metadata/oefa-lightpanda-download.json" in source.notes
                assert source.size_bytes == latest["size_bytes"] > 0
                assert len(latest["sha256"]) == 64
                assert latest["data_rows"] > 0 and latest["csv_delimiter"] == ";"
                assert latest["reused"] and latest["manifest_unchanged"]
            else:
                assert source.status in {"verified", "downloaded"}
        if row["outcome"] == "blocked":
            assert source.status == "blocked"
            assert row["reason"]
        if source.size_bytes is not None:
            assert source.source_id in {
                "senamhi-lima-csv",
                "senamhi-data-dictionary",
                "senamhi-metadata",
                "oefa-csv",
                "oefa-eas-aire",
            }
        assert source.redistribution == (
            "allowed"
            if source.source_id
            in {"senamhi-lima-csv", "senamhi-data-dictionary", "senamhi-metadata", "senamhi-lima"}
            else "unknown"
        )


def test_senamhi_download_has_public_provenance_without_bundling_raw_data():
    root = Path(__file__).resolve().parents[1]
    catalog = load_catalog(root / "configs/sources.yaml")
    source = next(s for s in catalog.sources if s.source_id == "senamhi-lima-csv")
    evidence = json.loads((root / "metadata/senamhi-lima-download.json").read_text())
    assert source.status == "downloaded"
    assert str(source.resource_urls[0]) == evidence["source_url"]
    assert source.size_bytes == evidence["size_bytes"] == 68501558
    assert len(evidence["sha256"]) == 64
    assert evidence["csv_validation"]["data_rows"] == 577794
    assert evidence["normalization"] == "none"
    assert source.license == "ODC-BY-1.0"
    assert source.redistribution == "allowed"
    assert source.units == {"PM10": "ug/m3", "PM2_5": "ug/m3", "NO2": "ug/m3"}


def test_senamhi_documentation_preserves_field_and_document_provenance():
    root = Path(__file__).resolve().parents[1]
    review = json.loads((root / "metadata/senamhi-documentation.json").read_text())
    original = json.loads((root / "metadata/senamhi-lima-download.json").read_text())
    assert [field["name"] for field in review["fields"]] == original["csv_validation"]["columns"]
    assert len({field["name"] for field in review["fields"]}) == 15
    for field in review["fields"]:
        assert field["reference"].startswith("DiccionarioDatos!")
        assert field["definition"]
    catalog = load_catalog(root / "configs/sources.yaml")
    sources = {s.source_id: s for s in catalog.sources}
    for document in review["documents"]:
        assert document["size_bytes"] > 0
        assert len(document["sha256"]) == 64
        assert datetime.fromisoformat(document["verified_at_utc"]).tzinfo is not None
        if document["source_id"] in sources:
            source = sources[document["source_id"]]
            assert source.size_bytes == document["size_bytes"]
            assert source.status == "downloaded"
            assert document["source_url"] in [str(url) for url in source.resource_urls]
    assert review["license"]["identifier"] == "ODC-BY-1.0"
    assert review["license"]["redistribution_decision"] == "pending_clarification"
    assert review["temporal_interpretation"]["csv_timezone_confirmed"] is None
    assert review["temporal_interpretation"]["corroboration_only"] is True
    assert len(review["no2_crosscheck"]) == 5
    assert review["consultation"]["sent"] is True
    assert review["consultation"]["follow_up_issue"] == 43
    assert review["consultation"]["recipient_receipt_confirmed"] is False
    assert review["consultation"]["sender"] == "keneth.arias@outlook.com"
    assert review["consultation"]["reviewed"] is True


def test_oefa_download_preserves_historical_channel_failure():
    root = Path(__file__).resolve().parents[1]
    old = json.loads((root / "metadata/oefa-acquisition-check.json").read_text())
    new = json.loads((root / "metadata/oefa-lightpanda-download.json").read_text())
    assert old["csv"]["status"] == "blocked" and old["csv"]["http_status"] == 418
    assert "artifact" not in old["csv"]
    assert datetime.fromisoformat(new["verified_at_utc"]) > datetime.fromisoformat(
        old["finished_at_utc"]
    )
    assert old["csv"]["resource_url"] == new["source_url"]
    assert new["http_status"] is None  # Lightpanda no expuso el código exacto del archivo.
    assert new["normalization"] == "none"


def test_oefa_eas_air_is_a_separate_user_supplied_long_format_candidate():
    root = Path(__file__).resolve().parents[1]
    evidence = json.loads((root / "metadata/oefa-eas-aire-local.json").read_text())
    plan = json.loads((root / "configs/acquisition/oefa-eas-aire-local.json").read_text())
    job = plan["jobs"][0]
    assert job["spec"]["source_id"] == "oefa-eas-aire" != "oefa-csv"
    assert job["spec"]["method"] == "local" and evidence["supplied_by"] == "user"
    assert job["spec"]["resource_url"].endswith("/EAS_Aire_0.csv")
    assert job["spec"]["expected_sha256"] == evidence["sha256"]
    assert job["expected_size_bytes"] == evidence["size_bytes"] > 0
    assert job["local_file"] == evidence["local_path"]
    assert len(evidence["sha256"]) == 64 and evidence["data_rows"] > 0
    assert len(evidence["columns"]) == 23
    assert {"Valor", "Parámetro", "Fecha.inicio", "Hora.inicio"} <= set(evidence["columns"])
    assert evidence["network_http_status_for_file"] is None
    assert evidence["scientific_ready"] is False
    assert evidence["date_encoding_confirmed"] is False
    sources = {s.source_id: s for s in load_catalog(root / "configs/sources.yaml").sources}
    assert sources["oefa-eas-aire"].status == "downloaded"
    assert sources["oefa-eas-aire"].size_bytes == evidence["size_bytes"]
    notes = sources["oefa-eas-aire"].notes
    assert notes is not None and "metadata/oefa-eas-aire-local.json" in notes
