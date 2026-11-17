import csv
import json
from typing import Literal

import duckdb
import pytest
from pydantic import ValidationError

from airaware.acquisition.models import AcquisitionSpec
from airaware.acquisition.store import ingest_file
from airaware.comparison.inputs import digest
from airaware.comparison.models import OperatingSelection, Policy
from airaware.comparison.runner import compare
from airaware.profiling.engine import ProfileSpec
from tests.test_profiling import HEADER

UNKNOWN: list[Literal["interval_position_unverified", "quality_flags_unverified"]] = [
    "interval_position_unverified",
    "quality_flags_unverified",
]


def fixture(tmp_path, hours=48):
    p = tmp_path / "input.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for i in range(hours):
            w.writerow(
                [
                    "demo",
                    "-77",
                    "-12",
                    "10",
                    "LIMA",
                    "LIMA",
                    "demo",
                    f"202401{1 + i // 24:02}",
                    f"{i % 24:02}0000",
                    "10",
                ]
            )
    acq = AcquisitionSpec(
        source_id="fixture",
        resource_url="https://example.org/data",
        method="local",
        format="csv",
        max_bytes=100000,
    )
    result = ingest_file(acq, p, tmp_path / "data")
    return ProfileSpec(
        source_id="fixture",
        kind="senamhi",
        manifest=result.manifest,
        raw_root=tmp_path / "data/raw",
        sha256=digest(p),
        columns=HEADER,
        signals=["PM2_5"],
    )


def selection(sha):
    return OperatingSelection(
        source_id="fixture",
        input_sha256=sha,
        geography="lima",
        signal="pm25",
        authorized_by="keneth-arias",
        approval_reference="fixture:approval",
        timestamp_basis="published_utc",
        accepted_unknowns=UNKNOWN,
        quality="unknown",
        interval_position="unknown",
        daily_regulatory_labels=False,
    )


def test_approved_selection_accepts_forecast_without_claiming_scientific_validation(tmp_path):
    spec = fixture(tmp_path)
    policy = Policy(
        version="comparison-v3",
        histories=[24],
        horizons=[6],
        geographies=["lima"],
        signals=["pm25"],
        blockers={"fixture": UNKNOWN},
        operating_selection=selection(spec.sha256),
    )
    run = compare([spec], policy, tmp_path / "reports")
    s = json.loads((run / "summary.json").read_text())
    assert s["selected_source"] == "fixture"
    assert s["selection_status"] == "selected_under_operating_policy"
    assert s["sources"][0]["accepted_forecasting_windows"] == 19
    assert s["sources"][0]["scientific_score"] is None
    with duckdb.connect() as c:
        assert c.execute(
            "SELECT scientific_valid_windows,accepted_forecasting_windows FROM read_parquet(?)",
            [str(run / "forecasting-readiness.parquet")],
        ).fetchone() == (None, 19)


@pytest.mark.parametrize("change", [{"input_sha256": "b" * 64}, {"signal": "pm10"}])
def test_approval_does_not_transfer_to_another_input_or_target(tmp_path, change):
    spec = fixture(tmp_path)
    selected = OperatingSelection.model_validate(selection(spec.sha256).model_dump() | change)
    with pytest.raises(ValueError):
        compare(
            [spec],
            Policy(
                version="comparison-v3",
                signals=["pm25"],
                blockers={"fixture": UNKNOWN},
                operating_selection=selected,
            ),
            tmp_path / "reports",
        )


def test_approval_cannot_bypass_unaccepted_blocker_or_enable_regulatory_labels(tmp_path):
    spec = fixture(tmp_path)
    with pytest.raises(ValueError):
        compare(
            [spec],
            Policy(
                version="comparison-v3",
                blockers={"fixture": UNKNOWN + ["rights_unknown"]},
                operating_selection=selection(spec.sha256),
            ),
            tmp_path / "reports",
        )
    with pytest.raises(ValidationError):
        OperatingSelection.model_validate(
            selection(spec.sha256).model_dump() | {"daily_regulatory_labels": True}
        )


def test_selection_requires_at_least_one_complete_forecasting_window(tmp_path):
    spec = fixture(tmp_path, hours=24)
    policy = Policy(
        version="comparison-v3",
        histories=[24],
        horizons=[6],
        signals=["pm25"],
        blockers={"fixture": UNKNOWN},
        operating_selection=selection(spec.sha256),
    )
    with pytest.raises(ValueError, match="ventanas completas"):
        compare([spec], policy, tmp_path / "reports")
