import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from airaware.cli import app
from airaware.derived_artifacts import sha256_file
from airaware.senamhi_event_labels import (
    LabelingEvidence,
    evaluate_windows,
    inspect_structure,
    load_evidence,
)
from airaware.senamhi_timeline import HOURS_FILE, TIMELINE_VERSION
from airaware.senamhi_windows import WINDOWS_FILE, WINDOWS_VERSION

BASE = datetime(2024, 1, 1, tzinfo=UTC)
POLICY = Path("configs/thresholds.yaml")

TIMELINE_SCHEMA = pa.schema(
    [
        ("series_id", pa.string()),
        ("station_key", pa.string()),
        ("sensor_id", pa.string()),
        ("parameter_raw", pa.string()),
        ("parameter", pa.string()),
        ("unit", pa.string()),
        ("observed_at", pa.timestamp("us", tz="UTC")),
        ("value", pa.float64()),
        ("observation_id", pa.string()),
        ("available_at", pa.timestamp("us", tz="UTC")),
        ("quality", pa.string()),
        ("source_observation_ids", pa.list_(pa.string())),
        ("status", pa.string()),
        ("is_missing", pa.bool_()),
        ("is_imputed", pa.bool_()),
    ]
)

WINDOWS_SCHEMA = pa.schema(
    [
        ("window_id", pa.string()),
        ("series_id", pa.string()),
        ("station_key", pa.string()),
        ("history_start", pa.timestamp("us", tz="UTC")),
        ("origin_at", pa.timestamp("us", tz="UTC")),
        ("target_start", pa.timestamp("us", tz="UTC")),
        ("target_end", pa.timestamp("us", tz="UTC")),
        ("target_values", pa.list_(pa.float64())),
        ("target_mean", pa.float64()),
    ]
)

EVIDENCE = {
    "source_id": "senamhi-lima-csv",
    "timezone": "UTC",
    "method": "automatic_hourly",
    "interval_position": "hour_ending",
    "unit_evidence": "fixture:evidencia-unidades",
    "quality_evidence": "fixture:evidencia-calidad-v1",
    "quality_valid_values": ["valid"],
}


def make_rows(
    *,
    hours=range(48),
    value=10.0,
    quality="valid",
    series="serie-a",
    station="estacion-a",
    prefix="obs",
):
    rows = []
    for h in hours:
        measured = value(h) if callable(value) else value
        observation_id = None if measured is None else f"{prefix}-{h}"
        rows.append(
            {
                "series_id": series,
                "station_key": station,
                "sensor_id": "sensor-1",
                "parameter_raw": "PM2_5",
                "parameter": "PM2.5",
                "unit": "ug/m3",
                "observed_at": BASE + timedelta(hours=h),
                "value": measured,
                "observation_id": observation_id,
                "available_at": None,
                "quality": quality,
                "source_observation_ids": [] if measured is None else [observation_id],
                "status": "absent_hour" if measured is None else "observed",
                "is_missing": measured is None,
                "is_imputed": False,
            }
        )
    return rows


def write_timeline(tmp_path, rows, *, name="timeline", version=TIMELINE_VERSION):
    source = tmp_path / name
    source.mkdir()
    pq.write_table(pa.Table.from_pylist(rows, schema=TIMELINE_SCHEMA), source / HOURS_FILE)
    write_manifest(
        source,
        {
            "version": version,
            "timezone": "UTC",
            "frequency_hours": 1,
            "output_sha256": sha256_file(source / HOURS_FILE),
        },
    )
    return source


def write_manifest(directory, manifest):
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def read_manifest(directory):
    return json.loads((directory / "manifest.json").read_text(encoding="utf-8"))


def build_windows(source, output, *, history=24, horizon=24, step=1):
    result = CliRunner().invoke(
        app,
        [
            "benchmark",
            "windows",
            "--input",
            str(source),
            "--output",
            str(output),
            "--history",
            str(history),
            "--horizon",
            str(horizon),
            "--step",
            str(step),
        ],
    )
    assert result.exit_code == 0, result.output
    return output


def evidence(**changes):
    return LabelingEvidence.model_validate({**EVIDENCE, **changes})


def evaluate(timeline, windows, output, *, ev=None):
    return evaluate_windows(timeline, windows, POLICY, output, evidence=ev)


def rewrite_timeline(timeline, mutate):
    table = pq.read_table(timeline / HOURS_FILE)
    rows = [mutated for row in table.to_pylist() if (mutated := mutate(dict(row))) is not None]
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), timeline / HOURS_FILE)
    manifest = read_manifest(timeline)
    manifest["output_sha256"] = sha256_file(timeline / HOURS_FILE)
    write_manifest(timeline, manifest)
    return manifest["output_sha256"]


def rewrite_windows(windows, mutate=None, *, manifest_changes=None):
    table = pq.read_table(windows / WINDOWS_FILE)
    rows = [mutate(dict(row)) for row in table.to_pylist()] if mutate else None
    if rows is not None:
        pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), windows / WINDOWS_FILE)
    manifest = read_manifest(windows)
    manifest["output_sha256"] = sha256_file(windows / WINDOWS_FILE)
    manifest.update(manifest_changes or {})
    write_manifest(windows, manifest)


def bundle(timeline, windows, output, *, ev=None):
    with pytest.raises(ValueError):
        evaluate(timeline, windows, output, ev=ev)
    assert not output.exists()
    assert list(output.parent.glob(".airaware-*")) == []


def full_bundle(tmp_path, *, ev=None):
    timeline = write_timeline(tmp_path, make_rows())
    windows = build_windows(timeline, tmp_path / "windows")
    return timeline, windows, tmp_path / "labels"


def test_horizon24_bundle_reconstructs_targets_and_labels(tmp_path):
    timeline, windows, output = full_bundle(tmp_path)
    summary = evaluate(timeline, windows, output, ev=evidence())
    assert summary["labeling"] == "evaluated"
    labels = pq.read_table(output / "labels.parquet").to_pylist()
    assert len(labels) == 1
    row = labels[0]
    assert row["origin_at"] == BASE + timedelta(hours=23)
    assert row["target_start"] == BASE + timedelta(hours=24)
    assert row["target_end"] == BASE + timedelta(hours=47)
    assert row["target_start"] == row["origin_at"] + timedelta(hours=1)
    assert row["target_end"] == row["origin_at"] + timedelta(hours=24)
    assert row["mean_ug_m3"] == 10.0
    assert row["label"] == "not_above_reference"
    assert row["valid_hours"] == 24 and row["required_hours"] == 24
    assert row["reason"] == "evaluated"
    assert row["kind"] == "forecast_24h"
    assert row["policy_id"] == "pe-pm25-reference-2017-v1"
    assert row["series_id"] == "serie-a" and row["station_key"] == "estacion-a"
    assert row["observation_ids"] == [f"obs-{h}" for h in range(24, 48)]
    assert row["valid_observation_ids"] == row["observation_ids"]
    assert row["source_observation_ids"] == [f"obs-{h}" for h in range(24, 48)]
    manifest = read_manifest(output)
    assert manifest["labeling"] == "evaluated"
    assert manifest["output_sha256"] == sha256_file(output / "labels.parquet")
    assert manifest["timeline_sha256"] == sha256_file(timeline / HOURS_FILE)
    assert manifest["windows_sha256"] == sha256_file(windows / WINDOWS_FILE)
    assert manifest["timeline_version"] == TIMELINE_VERSION
    assert manifest["windows_version"] == WINDOWS_VERSION
    assert manifest["horizon_hours"] == 24 and manifest["history_hours"] == 24
    assert manifest["counts"]["measured_complete_windows"] == 1
    assert manifest["counts"]["labels"]["not_above_reference"] == 1


def test_origin_at_is_excluded_and_bounds_included(tmp_path):
    timeline = write_timeline(tmp_path, make_rows(value=lambda h: 10000.0 if h == 23 else 0.0))
    windows = build_windows(timeline, tmp_path / "windows")
    summary = evaluate(timeline, windows, tmp_path / "labels", ev=evidence())
    assert summary["labeling"] == "evaluated"
    row = pq.read_table(tmp_path / "labels" / "labels.parquet").to_pylist()[0]
    assert row["mean_ug_m3"] == 0.0
    assert row["label"] == "not_above_reference"


def test_window_crossing_utc_midnight_keeps_published_timestamps(tmp_path):
    rows = make_rows()
    for row in rows:
        row["observed_at"] = datetime(2024, 1, 1, 10, tzinfo=UTC) + (row["observed_at"] - BASE)
    timeline = write_timeline(tmp_path, rows)
    windows = build_windows(timeline, tmp_path / "windows")
    evaluate(timeline, windows, tmp_path / "labels", ev=evidence())
    row = pq.read_table(tmp_path / "labels" / "labels.parquet").to_pylist()[0]
    assert row["target_start"] == datetime(2024, 1, 2, 10, tzinfo=UTC)
    assert row["target_end"] == datetime(2024, 1, 3, 9, tzinfo=UTC)
    assert row["observation_ids"][0] == "obs-24" and row["observation_ids"][-1] == "obs-47"


def test_horizon6_bundle_is_rejected_not_padded(tmp_path):
    timeline = write_timeline(tmp_path, make_rows())
    windows = build_windows(timeline, tmp_path / "windows6", horizon=6)
    summary = evaluate(timeline, windows, tmp_path / "labels", ev=evidence())
    assert summary["labeling"] == "blocked"
    assert "horizon_not_24" in summary["blocked_reasons"]
    assert not (tmp_path / "labels" / "labels.parquet").exists()
    assert (tmp_path / "labels" / "compatibility.json").exists()


@pytest.mark.parametrize(
    ("tamper", "match"),
    [
        ("windows_hash", "SHA-256"),
        ("timeline_hash", "SHA-256"),
        ("linkage", "vínculo"),
        ("timeline_version", "Versión"),
        ("windows_version", "Versión"),
        ("frequency", "frecuencia"),
        ("station", "estación"),
        ("grid_station", "estación"),
        ("bounds", "límites"),
        ("target_values", "valores"),
        ("target_mean", "promedio"),
        ("missing_hour", "conteo"),
        ("duplicate_hour", "conteo"),
        ("no_horizon", "contrato"),
    ],
)
def test_structural_inconsistencies_are_rejected(tmp_path, tamper, match):
    timeline = write_timeline(tmp_path, make_rows())
    windows = build_windows(timeline, tmp_path / "windows")
    output = tmp_path / "labels"
    if tamper == "windows_hash":
        with (windows / WINDOWS_FILE).open("ab") as stream:
            stream.write(b"alterado")
    elif tamper == "timeline_hash":
        with (timeline / HOURS_FILE).open("ab") as stream:
            stream.write(b"alterado")
    elif tamper == "linkage":
        rewrite_windows(windows, manifest_changes={"input_sha256": "0" * 64})
    elif tamper == "timeline_version":
        write_manifest(timeline, {**read_manifest(timeline), "version": "otra-version"})
    elif tamper == "windows_version":
        rewrite_windows(windows, manifest_changes={"version": "otra-version"})
    elif tamper == "frequency":
        write_manifest(timeline, {**read_manifest(timeline), "frequency_hours": 2})
    elif tamper == "station":
        rewrite_windows(windows, mutate=lambda row: {**row, "station_key": "otra-estacion"})
    elif tamper == "grid_station":
        hash_value = rewrite_timeline(
            timeline,
            lambda row: (
                {**row, "station_key": "otra-estacion"}
                if row["observed_at"] == BASE + timedelta(hours=30)
                else row
            ),
        )
        rewrite_windows(windows, manifest_changes={"input_sha256": hash_value})
    elif tamper == "bounds":
        rewrite_windows(
            windows,
            mutate=lambda row: {
                **row,
                "target_start": row["target_start"] + timedelta(hours=1),
            },
        )
    elif tamper == "target_values":
        rewrite_windows(
            windows,
            mutate=lambda row: {
                **row,
                "target_values": [row["target_values"][0] + 1.0, *row["target_values"][1:]],
            },
        )
    elif tamper == "target_mean":
        rewrite_windows(
            windows, mutate=lambda row: {**row, "target_mean": row["target_mean"] + 1.0}
        )
    elif tamper == "missing_hour":
        hash_value = rewrite_timeline(
            timeline,
            lambda row: None if row["observed_at"] == BASE + timedelta(hours=30) else row,
        )
        rewrite_windows(windows, manifest_changes={"input_sha256": hash_value})
    elif tamper == "duplicate_hour":
        table = pq.read_table(timeline / HOURS_FILE)
        rows = table.to_pylist()
        duplicate = next(row for row in rows if row["observed_at"] == BASE + timedelta(hours=30))
        rows.append(duplicate)
        pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), timeline / HOURS_FILE)
        manifest = read_manifest(timeline)
        manifest["output_sha256"] = sha256_file(timeline / HOURS_FILE)
        write_manifest(timeline, manifest)
        rewrite_windows(windows, manifest_changes={"input_sha256": manifest["output_sha256"]})
    elif tamper == "no_horizon":
        manifest = read_manifest(windows)
        del manifest["horizon_hours"]
        write_manifest(windows, manifest)
    with pytest.raises(ValueError, match=match):
        evaluate(timeline, windows, output, ev=evidence())
    assert not output.exists()


def test_non_measured_targets_never_become_valid_observations(tmp_path):
    def value(h):
        return None if h in (24, 25, 26) else 10.0

    rows = make_rows(value=value)
    statuses = {24: "conflict", 25: "unusable_value", 26: "absent_hour"}
    for row in rows:
        hour = (row["observed_at"] - BASE).total_seconds() / 3600
        if hour in statuses:
            row.update(
                value=None,
                observation_id=None,
                source_observation_ids=[],
                status=statuses[hour],
                is_missing=True,
            )
        if hour == 27:
            row.update(value=10.0, status="observed", is_imputed=True)
    timeline = write_timeline(tmp_path, rows)
    windows = build_windows(timeline, tmp_path / "windows")
    table = pq.read_table(windows / WINDOWS_FILE)
    assert table.num_rows == 0
    summary = evaluate(timeline, windows, tmp_path / "labels", ev=evidence())
    assert summary["labeling"] == "evaluated"
    assert summary["counts"]["labels"]["above_reference"] == 0
    assert summary["counts"]["measured_complete_windows"] == 0


def test_zero_is_measured_and_negative_value_is_not_a_negative_label(tmp_path):
    timeline = write_timeline(tmp_path, make_rows(value=0.0))
    windows = build_windows(timeline, tmp_path / "windows")
    evaluate(timeline, windows, tmp_path / "labels", ev=evidence())
    row = pq.read_table(tmp_path / "labels" / "labels.parquet").to_pylist()[0]
    assert row["mean_ug_m3"] == 0.0 and row["label"] == "not_above_reference"

    negative = write_timeline(
        tmp_path, make_rows(value=lambda h: -3.0 if h == 30 else 10.0), name="timeline2"
    )
    windows2 = build_windows(negative, tmp_path / "windows2")
    summary = evaluate(negative, windows2, tmp_path / "labels2", ev=evidence())
    row = pq.read_table(tmp_path / "labels2" / "labels.parquet").to_pylist()[0]
    assert summary["counts"]["measured_complete_windows"] == 1
    assert row["label"] == "not_evaluable" and row["valid_hours"] == 23
    assert row["mean_ug_m3"] is None and row["reason"] == "insufficient_valid_hours"
    assert read_manifest(tmp_path / "labels2")["counts"]["label_reasons"] == {
        "evaluated": 0,
        "insufficient_valid_hours": 1,
    }


def test_unknown_quality_and_interval_position_cannot_be_coerced(tmp_path):
    timeline, windows, output = full_bundle(tmp_path)
    summary = evaluate(timeline, windows, output, ev=evidence(quality_valid_values=["valid"]))
    timeline2 = write_timeline(tmp_path, make_rows(quality="unknown"), name="timeline2")
    windows2 = build_windows(timeline2, tmp_path / "windows2")
    blocked = evaluate(timeline2, windows2, tmp_path / "labels2", ev=evidence())
    assert blocked["labeling"] == "blocked"
    assert "quality_values_not_admissible" in blocked["blocked_reasons"]
    compatibility = json.loads((tmp_path / "labels2" / "compatibility.json").read_text())
    assert "unknown" in compatibility["data"]["target_quality_values"]
    assert not (tmp_path / "labels2" / "labels.parquet").exists()
    with pytest.raises(ValidationError):
        evidence(interval_position="hour_starting")
    assert summary["labeling"] == "evaluated"


def test_missing_quality_never_becomes_valid_quality(tmp_path):
    timeline = write_timeline(tmp_path, make_rows(quality=None))
    windows = build_windows(timeline, tmp_path / "windows")
    summary = evaluate(timeline, windows, tmp_path / "labels", ev=evidence())
    assert summary["labeling"] == "blocked"
    assert "quality_missing" in summary["blocked_reasons"]
    compatibility = json.loads((tmp_path / "labels" / "compatibility.json").read_text())
    assert compatibility["data"]["target_quality_missing"] is True
    assert not (tmp_path / "labels" / "labels.parquet").exists()


def test_evidence_cannot_admit_unknown_quality(tmp_path):
    timeline = write_timeline(tmp_path, make_rows(quality="unknown"))
    windows = build_windows(timeline, tmp_path / "windows")
    summary = evaluate(
        timeline,
        windows,
        tmp_path / "labels",
        ev=evidence(quality_valid_values=["unknown"]),
    )
    assert summary["labeling"] == "blocked"
    assert "quality_evidence_unknown_not_admissible" in summary["blocked_reasons"]
    assert not (tmp_path / "labels" / "labels.parquet").exists()


def test_series_and_stations_are_isolated(tmp_path):
    rows = make_rows(series="serie-a", station="estacion-a", value=60.0, prefix="a") + make_rows(
        series="serie-b", station="estacion-b", value=10.0, prefix="b"
    )
    timeline = write_timeline(tmp_path, rows)
    windows = build_windows(timeline, tmp_path / "windows")
    summary = evaluate(timeline, windows, tmp_path / "labels", ev=evidence())
    assert summary["labeling"] == "evaluated"
    assert summary["counts"]["series_total"] == 2
    assert summary["counts"]["windows_total"] == 2
    labels = pq.read_table(tmp_path / "labels" / "labels.parquet").to_pylist()
    assert [row["series_id"] for row in labels] == ["serie-a", "serie-b"]
    first, second = labels
    assert (first["station_key"], first["mean_ug_m3"], first["label"]) == (
        "estacion-a",
        60.0,
        "above_reference",
    )
    assert (second["station_key"], second["mean_ug_m3"], second["label"]) == (
        "estacion-b",
        10.0,
        "not_above_reference",
    )
    assert first["observation_ids"] == [f"a-{h}" for h in range(24, 48)]
    assert second["observation_ids"] == [f"b-{h}" for h in range(24, 48)]
    assert not set(first["observation_ids"]) & set(second["observation_ids"])


def test_manifest_records_policy_evidence_and_reason_counts(tmp_path):
    timeline, windows, output = full_bundle(tmp_path)
    evaluate(timeline, windows, output, ev=evidence())
    manifest = read_manifest(output)
    assert manifest["policy_id"] == "pe-pm25-reference-2017-v1"
    assert manifest["policy_sha256"] == sha256_file(POLICY)
    assert manifest["evidence"]["source_id"] == "senamhi-lima-csv"
    assert manifest["evidence"]["interval_position"] == "hour_ending"
    assert manifest["counts"]["label_reasons"] == {
        "evaluated": 1,
        "insufficient_valid_hours": 0,
    }
    assert sum(manifest["counts"]["labels"].values()) == manifest["counts"]["windows_total"] == 1
    assert manifest["output_sha256"] == sha256_file(output / "labels.parquet")


def test_empty_window_bundle_publishes_empty_labels(tmp_path):
    timeline = write_timeline(tmp_path, make_rows(value=lambda h: None if h >= 24 else 10.0))
    windows = build_windows(timeline, tmp_path / "windows")
    assert pq.read_table(windows / WINDOWS_FILE).num_rows == 0
    summary = evaluate(timeline, windows, tmp_path / "labels", ev=evidence())
    assert summary["labeling"] == "evaluated"
    assert summary["counts"]["windows_total"] == 0
    assert summary["counts"]["labels"] == {
        "above_reference": 0,
        "not_above_reference": 0,
        "not_evaluable": 0,
    }
    assert pq.read_table(tmp_path / "labels" / "labels.parquet").num_rows == 0
    manifest = read_manifest(tmp_path / "labels")
    assert manifest["counts"]["label_reasons"] == {
        "evaluated": 0,
        "insufficient_valid_hours": 0,
    }
    assert manifest["output_sha256"] == sha256_file(tmp_path / "labels" / "labels.parquet")


def test_structurally_complete_window_stays_scientifically_inadmissible(tmp_path):
    timeline, windows, output = full_bundle(tmp_path)
    summary = evaluate(timeline, windows, output)
    assert summary["labeling"] == "blocked"
    assert "labeling_evidence_missing" in summary["blocked_reasons"]
    manifest = read_manifest(output)
    assert manifest["counts"]["measured_complete_windows"] == 1
    assert manifest["counts"]["labels"] == {
        "above_reference": 0,
        "not_above_reference": 0,
        "not_evaluable": 0,
    }
    assert not (output / "labels.parquet").exists()
    compatibility = json.loads((output / "compatibility.json").read_text())
    assert compatibility["counts"]["windows_total"] == 1
    assert compatibility["windows_sha256"] == sha256_file(windows / WINDOWS_FILE)


@pytest.mark.parametrize(("value", "expected"), [(50.0, "not_above_reference"), (51.0, "above")])
def test_threshold_remains_strict_through_the_adapter(tmp_path, value, expected):
    timeline = write_timeline(tmp_path, make_rows(value=value))
    windows = build_windows(timeline, tmp_path / "windows")
    evaluate(timeline, windows, tmp_path / "labels", ev=evidence())
    row = pq.read_table(tmp_path / "labels" / "labels.parquet").to_pylist()[0]
    if expected == "above":
        assert row["label"] == "above_reference" and row["mean_ug_m3"] == 51.0
    else:
        assert row["label"] == "not_above_reference" and row["mean_ug_m3"] == 50.0


def test_history_values_cannot_change_a_target_only_label(tmp_path):
    timeline, windows, output = full_bundle(tmp_path)
    evaluate(timeline, windows, output, ev=evidence())
    before = pq.read_table(output / "labels.parquet").to_pylist()

    def change_history(row):
        if row["observed_at"] == BASE + timedelta(hours=5):
            row["value"] = 99999.0
        return row

    hash_value = rewrite_timeline(timeline, change_history)
    rewrite_windows(windows, manifest_changes={"input_sha256": hash_value})
    summary = evaluate(timeline, windows, tmp_path / "labels2", ev=evidence())
    after = pq.read_table(tmp_path / "labels2" / "labels.parquet").to_pylist()
    assert summary["labeling"] == "evaluated"
    assert after == before


def test_failed_write_publishes_no_partial_bundle(tmp_path):
    timeline, windows, output = full_bundle(tmp_path)
    rewrite_windows(windows, mutate=lambda row: {**row, "station_key": "otra-estacion"})
    bundle(timeline, windows, output, ev=evidence())


def test_failure_during_label_write_publishes_nothing(tmp_path, monkeypatch):
    timeline, windows, output = full_bundle(tmp_path)

    def explode(*args, **kwargs):
        args[3].write_bytes(b"parcial")
        raise ValueError("fallo simulado")

    monkeypatch.setattr("airaware.senamhi_event_labels._write_labels", explode)
    with pytest.raises(ValueError, match="fallo simulado"):
        evaluate(timeline, windows, output, ev=evidence())
    assert not output.exists()
    assert list(tmp_path.glob(".airaware-*")) == []


def test_input_change_during_blocked_inspection_publishes_nothing(tmp_path, monkeypatch):
    timeline, windows, output = full_bundle(tmp_path)

    def change_timeline_after_inspection(links):
        inspection = inspect_structure(links)
        with links.hours.open("ab") as stream:
            stream.write(b"alterado")
        return inspection

    monkeypatch.setattr(
        "airaware.senamhi_event_labels.inspect_structure", change_timeline_after_inspection
    )
    with pytest.raises(ValueError, match="cambiaron durante la evaluación"):
        evaluate(timeline, windows, output)
    assert not output.exists()
    assert list(tmp_path.glob(".airaware-*")) == []


def test_repeated_execution_is_logically_and_binarily_identical(tmp_path):
    timeline, windows, _ = full_bundle(tmp_path)
    evaluate(timeline, windows, tmp_path / "labels1", ev=evidence())
    evaluate(timeline, windows, tmp_path / "labels2", ev=evidence())
    assert (tmp_path / "labels1" / "manifest.json").read_bytes() == (
        tmp_path / "labels2" / "manifest.json"
    ).read_bytes()
    assert (tmp_path / "labels1" / "labels.parquet").read_bytes() == (
        tmp_path / "labels2" / "labels.parquet"
    ).read_bytes()


def test_cli_reports_blocked_labeling_and_failures(tmp_path):
    timeline, windows, output = full_bundle(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "labels",
            "senamhi",
            "--timeline",
            str(timeline),
            "--windows",
            str(windows),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "blocked" in result.output
    assert (output / "compatibility.json").exists()
    tampered = tmp_path / "tampered"
    with (windows / WINDOWS_FILE).open("ab") as stream:
        stream.write(b"alterado")
    failure = CliRunner().invoke(
        app,
        [
            "labels",
            "senamhi",
            "--timeline",
            str(timeline),
            "--windows",
            str(windows),
            "--output",
            str(tampered),
        ],
    )
    assert failure.exit_code == 1
    assert "SHA-256" in failure.output
    assert not tampered.exists()
    malformed = tmp_path / "evidence.json"
    malformed.write_text(json.dumps({**EVIDENCE, "method": "manual_24h"}))
    rejected = CliRunner().invoke(
        app,
        [
            "labels",
            "senamhi",
            "--timeline",
            str(timeline),
            "--windows",
            str(windows),
            "--output",
            str(tmp_path / "labels3"),
            "--policy",
            str(POLICY),
            "--evidence",
            str(malformed),
        ],
    )
    assert rejected.exit_code == 1


def test_load_evidence_reads_json_and_rejects_unsupported_semantics(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(EVIDENCE))
    loaded = load_evidence(path)
    assert loaded.interval_position == "hour_ending"
    assert loaded.quality_valid_values == ("valid",)
    path.write_text(json.dumps({**EVIDENCE, "interval_position": "hour_starting"}))
    with pytest.raises(ValidationError):
        load_evidence(path)
