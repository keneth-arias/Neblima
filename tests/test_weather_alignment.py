"""Regresiones de la alineación meteorología y PM2.5 sin información futura (#17).

Todas las fechas son sintéticas y en UTC; ninguna prueba consulta la red.
"""

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from typer.testing import CliRunner

from airaware.acquisition.batch import BatchPlan
from airaware.acquisition.models import AcquisitionSpec
from airaware.acquisition.store import ingest_chunks
from airaware.cli import app
from airaware.derived_artifacts import sha256_file
from airaware.senamhi_timeline import TIMELINE_VERSION
from airaware.senamhi_windows import build_windows
from airaware.weather_alignment import (
    WEATHER_ALIGNMENT_VERSION,
    WEATHER_ROWS_SCHEMA,
    AlignmentConfig,
    join_weather,
)

RUNNER = CliRunner()
STATION_A = "a" * 64
STATION_B = "b" * 64
LAT_A, LON_A = -12.1, -77.03
LAT_B, LON_B = -12.2, -77.04
CELL_LAT, CELL_LON = -12.124954, -76.99219
VARIABLE = "temperature_2m_previous_day1"
REALIZED = "temperature_2m"
BASE = "2024-01-01 00:00:00+00"


def gfs_payload(
    prev_day1: list[float | None],
    realized: list[float],
    cell: tuple[float, float] = (CELL_LAT, CELL_LON),
    elevation: float = 120.0,
    utc_offset_seconds: int = 0,
) -> dict:
    times = [
        (datetime(2022, 3, 9, tzinfo=UTC) + timedelta(hours=index)).strftime("%Y-%m-%dT%H:%M")
        for index in range(len(prev_day1))
    ]
    return {
        "latitude": cell[0],
        "longitude": cell[1],
        "generationtime_ms": 1.0,
        "utc_offset_seconds": utc_offset_seconds,
        "timezone": "GMT",
        "timezone_abbreviation": "GMT",
        "elevation": elevation,
        "hourly_units": {"time": "iso8601", REALIZED: "°C", VARIABLE: "°C"},
        "hourly": {"time": times, REALIZED: realized, VARIABLE: prev_day1},
    }


def gfs_spec(lat: float, lon: float, digest: str | None = None) -> AcquisitionSpec:
    return AcquisitionSpec(
        source_id="open-meteo-previous-model-runs",
        resource_url=(
            "https://previous-runs-api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&start_date=2022-03-09&end_date=2022-03-15"
            "&hourly=temperature_2m,temperature_2m_previous_day1&models=gfs_seamless"
        ),
        api_documentation_url="https://open-meteo.com/en/docs/previous-runs-api",
        method="api",
        format="json",
        max_bytes=65536,
        json_required_keys=("latitude", "longitude", "hourly"),
        expected_sha256=digest,
        acquired_at=datetime(2026, 11, 17, 23, 41, 47, tzinfo=UTC),
    )


def store_gfs_bundle(data_dir: Path, payload: dict, lat: float, lon: float) -> AcquisitionSpec:
    body = json.dumps(payload).encode("utf-8")
    spec = gfs_spec(lat, lon)
    ingest_chunks(spec, [body], data_dir)
    return spec.model_copy(
        update={
            "expected_sha256": sha256(body).hexdigest(),
            "acquired_at": datetime(2026, 11, 17, 23, 41, 47, tzinfo=UTC),
        }
    )


def station_entry(key: str, name: str, lat: float, lon: float) -> dict:
    return {
        "station_key": key,
        "name": name,
        "latitude": lat,
        "longitude": lon,
        "altitude_m": 150.0,
        "coordinate_reference": "undeclared",
    }


def make_config(stations: list[dict]) -> AlignmentConfig:
    return AlignmentConfig.model_validate(
        {
            "version": 1,
            "comparison_policy": "configs/benchmark.yaml",
            "weather_variant": {
                "name": "pm25_gfs_previous_day1",
                "source_id": "open-meteo-previous-model-runs",
                "variable": VARIABLE,
                "excluded_realized_variables": [REALIZED],
                "unit": "°C",
                "nominal_lead_hours": 24,
                "issued_at_rule": "previous_day1_nominal_lead",
                "available_at_policy": "undocumented_null",
                "product_class": "archived_forecast",
                "experiment_class": "retrospective_issue_time",
                "acquisition_plan": "configs/acquisition/weather-lima-sample-plan.json",
                "coverage_utc": "2022-03-09T00:00Z/2022-03-15T23:00Z",
            },
            "stations": stations,
        }
    )


def two_station_config() -> AlignmentConfig:
    return make_config(
        [
            station_entry(STATION_A, "ESTACION_A", LAT_A, LON_A),
            station_entry(STATION_B, "ESTACION_B", LAT_B, LON_B),
        ]
    )


def single_station_config() -> AlignmentConfig:
    return make_config([station_entry(STATION_A, "ESTACION_A", LAT_A, LON_A)])


def frozen_chain(tmp_path: Path, keys: list[str]) -> tuple[Path, Path, Path]:
    timeline = tmp_path / "timeline"
    timeline.mkdir()
    size = len(keys) * 45
    table = pa.table(
        {
            "series_id": pa.array(
                [f"serie-{index}" for index, _ in enumerate(keys) for _ in range(45)], pa.string()
            ),
            "station_key": pa.array([key for _ in keys for key in [_] * 45][:size], pa.string()),
            "parameter_raw": pa.array(["PM2_5"] * size, pa.string()),
            "unit": pa.array(["ug/m3"] * size, pa.string()),
            "observed_at": pa.array(
                [
                    datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=hour)
                    for _ in keys
                    for hour in range(45)
                ],
                pa.timestamp("us", tz="UTC"),
            ),
            "available_at": pa.array([None] * size, pa.timestamp("us", tz="UTC")),
            "value": pa.array([float(hour) for _ in keys for hour in range(45)], pa.float64()),
            "status": pa.array(["observed"] * size, pa.string()),
            "is_missing": pa.array([False] * size, pa.bool_()),
            "is_imputed": pa.array([False] * size, pa.bool_()),
        }
    )
    pq.write_table(table, timeline / "hours.parquet")
    (timeline / "manifest.json").write_text(
        json.dumps(
            {"version": TIMELINE_VERSION, "output_sha256": sha256_file(timeline / "hours.parquet")}
        )
    )
    windows = tmp_path / "windows"
    build_windows(timeline, windows, history=2, horizon=2, step=1)
    splits = tmp_path / "splits"
    run = RUNNER.invoke(
        app,
        [
            "benchmark",
            "split",
            "--input",
            str(windows),
            "--timeline",
            str(timeline),
            "--output",
            str(splits),
        ],
    )
    assert run.exit_code == 0, run.output
    return timeline, windows, splits


def write_plan(tmp_path: Path, specs: list[AcquisitionSpec]) -> Path:
    path = tmp_path / "plan.json"
    path.write_text(
        BatchPlan.model_validate(
            {"jobs": [{"spec": spec.model_dump()} for spec in specs]}
        ).model_dump_json()
    )
    return path


def write_config(tmp_path: Path, config: AlignmentConfig) -> Path:
    path = tmp_path / "weather-alignment.yaml"
    path.write_text(yaml.safe_dump(config.model_dump(mode="json")), encoding="utf-8")
    return path


def align_arguments(config_path: Path, plan_path: Path, data_dir: Path, output: Path) -> list[str]:
    return [
        "align",
        "weather",
        "--config",
        str(config_path),
        "--plan",
        str(plan_path),
        "--data-dir",
        str(data_dir),
        "--output",
        str(output),
    ]


def join_arguments(windows: Path, timeline: Path, splits: Path) -> list[str]:
    return [
        "--windows",
        str(windows),
        "--timeline",
        str(timeline),
        "--splits",
        str(splits),
    ]


def synthetic_rows(rows: list[dict]) -> list[dict]:
    defaults = {
        "station_key": STATION_A,
        "station_name": "ESTACION_A",
        "requested_latitude": LAT_A,
        "requested_longitude": LON_A,
        "returned_cell_latitude": CELL_LAT,
        "returned_cell_longitude": CELL_LON,
        "returned_cell_elevation_m": 120.0,
        "distance_km_haversine": 7.5,
        "spatial_method": "open_meteo_grid_cell_lookup",
        "distance_note": "Aproximación haversine; CRS sin declarar",
        "available_at": None,
        "lead_hours": 24,
        "variable": VARIABLE,
        "unit": "°C",
        "product_class": "archived_forecast",
        "value_status": "present",
        "source_id": "open-meteo-previous-model-runs",
        "original_sha256": "c" * 64,
        "acquired_at": datetime(2026, 11, 17, 23, 41, tzinfo=UTC),
        "issued_at_rule": "previous_day1_nominal_lead",
        "experiment_class": "retrospective_issue_time",
    }
    return [defaults | row for row in rows]


def write_weather_bundle(bundle: Path, rows: list[dict]) -> Path:
    bundle.mkdir(parents=True)
    table = pa.Table.from_pylist(rows, schema=WEATHER_ROWS_SCHEMA)
    pq.write_table(table, bundle / "weather_rows.parquet")
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "version": WEATHER_ALIGNMENT_VERSION,
                "output_sha256": sha256_file(bundle / "weather_rows.parquet"),
            }
        )
    )
    return bundle


def chain_rows(bundle: Path) -> list[dict]:
    return pq.read_table(bundle / "window_weather.parquet").to_pylist()


def summary_rows(bundle: Path) -> list[dict]:
    return pq.read_table(bundle / "windows_weather_summary.parquet").to_pylist()


def hour(value: int) -> datetime:
    return datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=value)


def test_conversion_records_temporal_semantics_and_provenance(tmp_path):
    payload = gfs_payload([25.9, None], [25.6, 25.7])
    data = tmp_path / "data"
    spec = store_gfs_bundle(data, payload, LAT_A, LON_A)
    plan_path = write_plan(tmp_path, [spec])
    config_path = write_config(tmp_path, single_station_config())
    output = tmp_path / "weather"
    run = RUNNER.invoke(app, align_arguments(config_path, plan_path, data, output))
    assert run.exit_code == 0, run.output
    rows = pq.read_table(output / "weather_rows.parquet").to_pylist()
    assert len(rows) == 2
    first = rows[0]
    assert first["valid_at"] == datetime(2022, 3, 9, tzinfo=UTC)
    assert first["issued_at"] == first["valid_at"] - timedelta(hours=24)
    assert first["lead_hours"] == 24
    assert first["issued_at_rule"] == "previous_day1_nominal_lead"
    assert first["available_at"] is None
    assert first["acquired_at"] == datetime(2026, 11, 17, 23, 41, 47, tzinfo=UTC)
    assert first["variable"] == VARIABLE
    assert first["unit"] == "°C"
    assert first["product_class"] == "archived_forecast"
    assert first["experiment_class"] == "retrospective_issue_time"
    assert first["value_status"] == "present"
    assert rows[1]["value"] is None
    assert rows[1]["value_status"] == "missing"
    assert all(row["spatial_method"] == "open_meteo_grid_cell_lookup" for row in rows)
    assert all(row["distance_km_haversine"] > 0 for row in rows)
    assert all(row["requested_latitude"] == LAT_A for row in rows)
    assert all(
        (row["returned_cell_latitude"], row["returned_cell_longitude"]) == (CELL_LAT, CELL_LON)
        for row in rows
    )
    assert {row["variable"] for row in rows} == {VARIABLE}
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["reconciliation"]["rows_value_missing"] == 1
    assert manifest["weather"]["excluded_realized_variables"] == [REALIZED]
    assert manifest["weather"]["available_at"] is None
    assert any("retrospectivo" in item for item in manifest["limitations"])
    assert manifest["version"] == WEATHER_ALIGNMENT_VERSION
    assert manifest["output_sha256"] == sha256_file(output / "weather_rows.parquet")


def test_conversion_maps_requested_stations_to_shared_grid_cells(tmp_path):
    data = tmp_path / "data"
    specs = [
        store_gfs_bundle(data, gfs_payload([1.0] * 2, [1.0] * 2), LAT_A, LON_A),
        store_gfs_bundle(data, gfs_payload([2.0] * 2, [2.0] * 2), LAT_B, LON_B),
    ]
    plan_path = write_plan(tmp_path, specs)
    config_path = write_config(tmp_path, two_station_config())
    output = tmp_path / "weather"
    run = RUNNER.invoke(app, align_arguments(config_path, plan_path, data, output))
    assert run.exit_code == 0, run.output
    rows = pq.read_table(output / "weather_rows.parquet").to_pylist()
    assert {row["station_key"] for row in rows} == {STATION_A, STATION_B}
    assert {(row["returned_cell_latitude"], row["returned_cell_longitude"]) for row in rows} == {
        (CELL_LAT, CELL_LON)
    }
    manifest = json.loads((output / "manifest.json").read_text())
    cells = manifest["reconciliation"]["distinct_returned_cells"]
    assert len(cells) == 1
    assert cells[0]["stations"] == [STATION_A, STATION_B]
    assert manifest["reconciliation"]["timestamps_per_station"] == {STATION_A: 2, STATION_B: 2}
    assert manifest["reconciliation"]["stations_requested"] == 2
    assert manifest["reconciliation"]["stations_matched"] == 2


def test_conversion_reports_observed_grid_spacing_per_dimension(tmp_path):
    cells = [(CELL_LAT, CELL_LON), (CELL_LAT + 0.12, CELL_LON), (CELL_LAT + 0.24, CELL_LON)]
    data = tmp_path / "data"
    specs = [
        store_gfs_bundle(
            data, gfs_payload([1.0] * 2, [1.0] * 2, cell=cell), -12.1 + index * 0.1, LON_A
        )
        for index, cell in enumerate(cells)
    ]
    # Tres coordenadas solicitadas distintas, una por celda, con la misma longitud.
    stations = [
        station_entry(f"{index:x}" * 64, f"ESTACION_{index}", -12.1 + index * 0.1, LON_A)
        for index in range(3)
    ]
    plan_path = write_plan(tmp_path, specs)
    config_path = write_config(tmp_path, make_config(stations))
    output = tmp_path / "weather"
    run = RUNNER.invoke(app, align_arguments(config_path, plan_path, data, output))
    assert run.exit_code == 0, run.output
    manifest = json.loads((output / "manifest.json").read_text())
    spacing = manifest["reconciliation"]["observed_grid_spacing_deg"]
    assert abs(spacing["latitude"] - 0.12) < 1e-9
    assert spacing["longitude"] is None
    assert manifest["reconciliation"]["declared_grid_resolution"] is None


def test_conversion_is_deterministic_and_refuses_existing_output(tmp_path):
    data = tmp_path / "data"
    spec = store_gfs_bundle(data, gfs_payload([25.9], [25.6]), LAT_A, LON_A)
    plan_path = write_plan(tmp_path, [spec])
    config_path = write_config(tmp_path, single_station_config())
    arguments = align_arguments(config_path, plan_path, data, tmp_path / "unused")
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert RUNNER.invoke(app, arguments[:-1] + [str(first)]).exit_code == 0
    assert RUNNER.invoke(app, arguments[:-1] + [str(second)]).exit_code == 0
    assert pq.read_table(first / "weather_rows.parquet").equals(
        pq.read_table(second / "weather_rows.parquet")
    )
    assert (first / "manifest.json").read_bytes() == (second / "manifest.json").read_bytes()
    repeat = RUNNER.invoke(app, arguments[:-1] + [str(first)])
    assert repeat.exit_code != 0


def test_conversion_verifies_pinned_bytes_and_detects_tampering(tmp_path):
    data = tmp_path / "data"
    spec = store_gfs_bundle(data, gfs_payload([25.9], [25.6]), LAT_A, LON_A)
    config_path = write_config(tmp_path, single_station_config())

    mispinned = spec.model_copy(update={"expected_sha256": "0" * 64})
    bad_plan = write_plan(tmp_path, [mispinned])
    failed = RUNNER.invoke(app, align_arguments(config_path, bad_plan, data, tmp_path / "failed"))
    assert failed.exit_code != 0
    assert not (tmp_path / "failed").exists()

    plan_path = write_plan(tmp_path, [spec])
    output = tmp_path / "weather"
    ok = RUNNER.invoke(app, align_arguments(config_path, plan_path, data, output))
    assert ok.exit_code == 0, ok.output
    original = (
        data / "raw" / "open-meteo-previous-model-runs" / spec.expected_sha256 / "original.json"
    )
    assert json.loads(original.read_text()) == gfs_payload([25.9], [25.6])
    original.write_bytes(b"{}")
    tampered = RUNNER.invoke(
        app, align_arguments(config_path, plan_path, data, tmp_path / "tampered")
    )
    assert tampered.exit_code != 0
    assert not (tmp_path / "tampered").exists()


def test_conversion_rejects_uncovered_station_and_extra_bundle(tmp_path):
    data = tmp_path / "data"
    spec = store_gfs_bundle(data, gfs_payload([1.0], [1.0]), LAT_B, LON_B)
    plan_path = write_plan(tmp_path, [spec])
    config_path = write_config(tmp_path, single_station_config())
    run = RUNNER.invoke(app, align_arguments(config_path, plan_path, data, tmp_path / "weather"))
    assert run.exit_code != 0

    duplicate = store_gfs_bundle(
        data, gfs_payload([2.0], [2.0], cell=(CELL_LAT + 0.1, CELL_LON)), LAT_A, LON_A
    )
    both_plan = write_plan(tmp_path, [spec, duplicate])
    run = RUNNER.invoke(app, align_arguments(config_path, both_plan, data, tmp_path / "weather2"))
    assert run.exit_code != 0


def test_join_rejects_issue_after_origin_and_accepts_boundary_equality(tmp_path):
    timeline, windows, splits = frozen_chain(tmp_path, [STATION_A])
    rows = synthetic_rows([{"valid_at": hour(20), "issued_at": hour(20), "value": 21.5}])
    bundle = write_weather_bundle(tmp_path / "weather", rows)
    output = tmp_path / "joined"
    join_weather(single_station_config(), bundle, windows, timeline, splits, output)
    joined = {row["origin_at"]: row for row in chain_rows(output) if row["valid_at"] == hour(20)}
    assert joined[hour(19)]["alignment_status"] == "rejected_issue_after_origin"
    assert joined[hour(19)]["value"] is None
    assert joined[hour(20)]["alignment_status"] == "admissible"
    assert joined[hour(20)]["value"] == 21.5
    assert joined[hour(21)]["alignment_status"] == "admissible"
    assert joined[hour(21)]["value"] == 21.5
    summary = {row["origin_at"]: row for row in summary_rows(output)}
    assert summary[hour(19)]["weather_hours_rejected"] == 1
    assert summary[hour(20)]["weather_hours_admissible"] >= 1
    assert summary[hour(19)]["weather_hours_admissible"] == 0


def test_join_rejects_late_publication_with_earlier_valid_time(tmp_path):
    timeline, windows, splits = frozen_chain(tmp_path, [STATION_A])
    rows = synthetic_rows(
        [
            {
                "valid_at": hour(24),
                "issued_at": hour(12),
                "available_at": hour(25),
                "value": 21.5,
            }
        ]
    )
    bundle = write_weather_bundle(tmp_path / "weather", rows)
    output = tmp_path / "joined"
    join_weather(single_station_config(), bundle, windows, timeline, splits, output)
    joined = {row["origin_at"]: row for row in chain_rows(output) if row["valid_at"] == hour(24)}
    assert joined[hour(23)]["alignment_status"] == "rejected_available_after_origin"
    assert joined[hour(23)]["value"] is None
    assert joined[hour(24)]["alignment_status"] == "rejected_available_after_origin"
    assert joined[hour(24)]["value"] is None
    assert joined[hour(25)]["alignment_status"] == "admissible"
    assert joined[hour(25)]["value"] == 21.5
    assert joined[hour(23)]["issued_at"] <= joined[hour(23)]["origin_at"]
    assert joined[hour(25)]["available_at"] == joined[hour(25)]["origin_at"]


def test_join_masks_feature_value_of_late_issue_and_late_publication(tmp_path):
    timeline, windows, splits = frozen_chain(tmp_path, [STATION_A])
    rows = synthetic_rows(
        [
            {"valid_at": hour(20), "issued_at": hour(21), "value": 21.5},
            {
                "valid_at": hour(24),
                "issued_at": hour(12),
                "available_at": hour(25),
                "value": 19.5,
            },
            {"valid_at": hour(19), "issued_at": hour(19), "value": 18.0},
        ]
    )
    bundle = write_weather_bundle(tmp_path / "weather", rows)
    output = tmp_path / "joined"
    join_weather(single_station_config(), bundle, windows, timeline, splits, output)
    joined = {(row["origin_at"], row["valid_at"]): row for row in chain_rows(output)}
    for origin in (hour(19), hour(20)):
        late_issue = joined[(origin, hour(20))]
        assert late_issue["alignment_status"] == "rejected_issue_after_origin"
        assert late_issue["value"] is None
        assert late_issue["issued_at"] == hour(21)
    for origin in (hour(23), hour(24)):
        late_publication = joined[(origin, hour(24))]
        assert late_publication["alignment_status"] == "rejected_available_after_origin"
        assert late_publication["value"] is None
        assert late_publication["available_at"] == hour(25)
    equal_issue = joined[(hour(21), hour(20))]
    assert equal_issue["alignment_status"] == "admissible"
    assert equal_issue["value"] == 21.5
    equal_publication = joined[(hour(25), hour(24))]
    assert equal_publication["alignment_status"] == "admissible"
    assert equal_publication["value"] == 19.5
    control = joined[(hour(19), hour(19))]
    assert control["alignment_status"] == "admissible"
    assert control["value"] == 18.0
    summary = {row["origin_at"]: row for row in summary_rows(output)}
    assert summary[hour(19)]["weather_hours_rejected"] == 1
    assert summary[hour(19)]["weather_hours_admissible"] == 1
    assert summary[hour(19)]["weather_status"] == "partial"


def test_join_classifies_present_rows_without_usable_value_as_missing(tmp_path):
    timeline, windows, splits = frozen_chain(tmp_path, [STATION_A])
    rows = synthetic_rows(
        [
            {
                "valid_at": hour(19),
                "issued_at": hour(19),
                "value": None,
                "value_status": "missing",
            },
            {"valid_at": hour(20), "issued_at": hour(19), "value": None},
        ]
    )
    bundle = write_weather_bundle(tmp_path / "weather", rows)
    output = tmp_path / "joined"
    join_weather(single_station_config(), bundle, windows, timeline, splits, output)
    joined = {(row["origin_at"], row["valid_at"]): row for row in chain_rows(output)}
    covered = (
        (hour(19), hour(19)),
        (hour(19), hour(20)),
        (hour(20), hour(19)),
        (hour(20), hour(20)),
        (hour(21), hour(20)),
    )
    for origin, valid_at in covered:
        row = joined[(origin, valid_at)]
        assert row["alignment_status"] == "missing_weather"
        assert row["value"] is None
        assert row["issued_at"] == hour(19)
    summary = {row["origin_at"]: row for row in summary_rows(output)}
    for origin in (hour(19), hour(20), hour(21)):
        assert summary[origin]["weather_hours_admissible"] == 0
        assert summary[origin]["weather_hours_missing"] == 4
        assert summary[origin]["weather_status"] == "missing"


def test_join_fails_closed_when_issue_time_is_unknown(tmp_path):
    timeline, windows, splits = frozen_chain(tmp_path, [STATION_A])
    rows = synthetic_rows(
        [
            {"valid_at": hour(20), "issued_at": None, "value": 21.5},
            {"valid_at": hour(19), "issued_at": hour(19), "value": 18.0},
        ]
    )
    bundle = write_weather_bundle(tmp_path / "weather", rows)
    output = tmp_path / "joined"
    join_weather(single_station_config(), bundle, windows, timeline, splits, output)
    joined = {(row["origin_at"], row["valid_at"]): row for row in chain_rows(output)}
    for origin in (hour(19), hour(20), hour(21)):
        unknown = joined[(origin, hour(20))]
        assert unknown["alignment_status"] == "rejected_issue_unknown"
        assert unknown["value"] is None
        assert unknown["issued_at"] is None
        assert unknown["valid_at"] == hour(20)
    control = joined[(hour(19), hour(19))]
    assert control["alignment_status"] == "admissible"
    assert control["value"] == 18.0
    summary = {row["origin_at"]: row for row in summary_rows(output)}
    assert summary[hour(19)]["weather_hours_rejected"] == 1
    assert summary[hour(19)]["weather_hours_admissible"] == 1
    assert summary[hour(19)]["weather_status"] == "partial"


def test_join_allows_future_valid_time_only_as_forecast(tmp_path):
    timeline, windows, splits = frozen_chain(tmp_path, [STATION_A])
    rows = synthetic_rows([{"valid_at": hour(30), "issued_at": hour(5), "value": 20.0}])
    bundle = write_weather_bundle(tmp_path / "weather", rows)
    output = tmp_path / "joined"
    join_weather(single_station_config(), bundle, windows, timeline, splits, output)
    joined = chain_rows(output)
    history = [row for row in joined if row["hour_role"] == "history_input"]
    forecast = [row for row in joined if row["hour_role"] == "target_forecast"]
    assert history and forecast
    assert all(row["valid_at"] <= row["origin_at"] for row in history)
    assert all(row["valid_at"] > row["origin_at"] for row in forecast)
    future = [row for row in forecast if row["valid_at"] == hour(30)]
    assert future and {row["alignment_status"] for row in future} == {"admissible"}
    present = [row for row in forecast if row["variable"] == VARIABLE]
    assert present and {row["alignment_status"] for row in present} == {"admissible"}
    assert all(row["issued_at"] <= row["origin_at"] for row in present)


def test_missing_weather_stays_null_with_explicit_mask(tmp_path):
    timeline, windows, splits = frozen_chain(tmp_path, [STATION_A])
    rows = synthetic_rows(
        [
            {"valid_at": hour(value), "issued_at": hour(19), "value": 20.0 + value}
            for value in (19, 20, 21, 22)
        ]
    )
    bundle = write_weather_bundle(tmp_path / "weather", rows)
    output = tmp_path / "joined"
    join_weather(single_station_config(), bundle, windows, timeline, splits, output)
    joined = chain_rows(output)
    summary = summary_rows(output)
    splits_table = pq.read_table(splits / "splits.parquet")
    assert len(summary) == splits_table.num_rows
    assert {row["window_id"] for row in summary} == set(
        splits_table.column("window_id").to_pylist()
    )
    missing = [row for row in joined if row["alignment_status"] == "missing_weather"]
    assert missing
    assert all(row["value"] is None and row["issued_at"] is None for row in missing)
    admissible = [row for row in joined if row["alignment_status"] == "admissible"]
    assert admissible
    assert all(row["value"] == 20.0 + row["valid_at"].hour for row in admissible)
    counts: dict[str, int] = {}
    for row in joined:
        counts[row["window_id"]] = counts.get(row["window_id"], 0) + 1
    for row in summary:
        assert row["span_hours"] == 4
        assert counts[row["window_id"]] == 4
        assert (
            row["weather_hours_admissible"]
            + row["weather_hours_rejected"]
            + row["weather_hours_missing"]
            == 4
        )
    statuses = {row["weather_status"] for row in summary}
    assert statuses == {"complete", "partial", "missing"}


def test_full_chain_end_to_end_is_deterministic_and_parity_holds(tmp_path):
    timeline, windows, splits = frozen_chain(tmp_path, [STATION_A, STATION_B])
    data = tmp_path / "data"
    specs = [
        store_gfs_bundle(data, gfs_payload([1.0] * 2, [1.0] * 2), LAT_A, LON_A),
        store_gfs_bundle(data, gfs_payload([2.0] * 2, [2.0] * 2), LAT_B, LON_B),
    ]
    plan_path = write_plan(tmp_path, specs)
    config_path = write_config(tmp_path, two_station_config())
    base = align_arguments(config_path, plan_path, data, tmp_path / "unused")[:-2]
    arguments = base + join_arguments(windows, timeline, splits)
    first = tmp_path / "first"
    second = tmp_path / "second"
    initial = RUNNER.invoke(app, arguments + ["--output", str(first)])
    assert initial.exit_code == 0, initial.output
    repeat = RUNNER.invoke(app, arguments + ["--output", str(second)])
    assert repeat.exit_code == 0, repeat.output
    for name in (
        "weather_rows.parquet",
        "window_weather.parquet",
        "windows_weather_summary.parquet",
    ):
        assert pq.read_table(first / name).equals(pq.read_table(second / name))
    assert (first / "manifest.json").read_bytes() == (second / "manifest.json").read_bytes()
    manifest = json.loads((first / "manifest.json").read_text())
    parity = manifest["parity"]
    assert parity["identical_window_id_set"] is True
    assert parity["summary_windows_total"] == parity["windows_total"]
    assert parity["summary_eligible_windows"] == parity["windows_eligible"]
    splits_table = pq.read_table(splits / "splits.parquet")
    assert {row["window_id"] for row in summary_rows(first)} == set(
        splits_table.column("window_id").to_pylist()
    )
    assert manifest["outputs"]["window_weather_sha256"] == sha256_file(
        first / "window_weather.parquet"
    )
    assert manifest["inputs"]["splits_sha256"] == sha256_file(splits / "splits.parquet")


def test_join_validates_weather_manifest_and_frozen_chain(tmp_path):
    timeline, windows, splits = frozen_chain(tmp_path, [STATION_A])
    rows = synthetic_rows([{"valid_at": hour(20), "issued_at": hour(20), "value": 21.5}])
    output = tmp_path / "joined"

    wrong_version = write_weather_bundle(tmp_path / "wrong-version", rows)
    (wrong_version / "manifest.json").write_text(
        json.dumps({"version": "otra", "output_sha256": "x"})
    )
    with pytest.raises(ValueError):
        join_weather(single_station_config(), wrong_version, windows, timeline, splits, output)

    wrong_hash = write_weather_bundle(tmp_path / "wrong-hash", rows)
    (wrong_hash / "manifest.json").write_text(
        json.dumps({"version": WEATHER_ALIGNMENT_VERSION, "output_sha256": "0" * 64})
    )
    with pytest.raises(ValueError):
        join_weather(single_station_config(), wrong_hash, windows, timeline, splits, output)

    tampered = tmp_path / "splits-tampered"
    tampered.mkdir()
    for name in ("splits.parquet", "manifest.json"):
        (tampered / name).write_bytes((splits / name).read_bytes())
    table = pq.read_table(tampered / "splits.parquet")
    index = table.schema.get_field_index("target_mean")
    values = table.column("target_mean").to_pylist()
    values[0] = (values[0] or 0.0) + 1.0
    replaced = table.set_column(index, "target_mean", pa.array(values, pa.float64()))
    pq.write_table(replaced, tampered / "splits.parquet")
    good = write_weather_bundle(tmp_path / "good", rows)
    with pytest.raises(ValueError):
        join_weather(single_station_config(), good, windows, timeline, tampered, output)


def test_cli_requires_join_arguments_together(tmp_path):
    config_path = write_config(tmp_path, single_station_config())
    data = tmp_path / "data"
    data.mkdir()
    run = RUNNER.invoke(
        app,
        [
            "align",
            "weather",
            "--config",
            str(config_path),
            "--data-dir",
            str(data),
            "--windows",
            str(tmp_path / "windows"),
            "--output",
            str(tmp_path / "out"),
        ],
    )
    assert run.exit_code != 0


def test_repository_config_matches_pinned_acquisition_plan():
    root = Path(__file__).resolve().parents[1]
    config = AlignmentConfig.model_validate(
        yaml.safe_load((root / "configs/weather-alignment.yaml").read_text(encoding="utf-8"))
    )
    assert len(config.stations) == 7
    assert len({station.station_key for station in config.stations}) == 7
    assert config.weather_variant.variable == VARIABLE
    assert config.weather_variant.available_at_policy == "undocumented_null"
    assert config.weather_variant.experiment_class == "retrospective_issue_time"
    assert config.weather_variant.nominal_lead_hours == 24
    plan = json.loads((root / config.weather_variant.acquisition_plan).read_text(encoding="utf-8"))
    requested = set()
    for job in plan["jobs"]:
        if job["spec"]["source_id"] != "open-meteo-previous-model-runs":
            continue
        query = parse_qs(urlsplit(job["spec"]["resource_url"]).query)
        requested.add((float(query["latitude"][0]), float(query["longitude"][0])))
    configured = {(station.latitude, station.longitude) for station in config.stations}
    assert requested == configured
    assert (root / config.comparison_policy).exists()
