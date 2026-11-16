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
    assert len(rows) == len(catalog.sources) == 37
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
        assert source.last_verified_at == datetime.fromisoformat(row["checked_at"])
        assert source.notes
        if row["outcome"] == "partial":
            assert source.status == "discovered"
            assert row["reason"]
        if row["outcome"] == "accessible":
            assert source.status in {"verified", "downloaded"}
        if row["outcome"] == "blocked":
            assert source.status == "blocked"
            assert row["reason"]
        assert source.size_bytes is None or source.source_id == "senamhi-lima-csv"
        assert source.redistribution == "unknown"


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
    assert source.license is None
