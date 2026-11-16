import csv
import hashlib
import json

import duckdb
import pytest

from airaware.acquisition.models import AcquisitionSpec
from airaware.acquisition.store import ingest_file
from airaware.profiling import ProfileSpec, profile

HEADER = [
    "ESTACION",
    "LONGITUD",
    "LATITUD",
    "ALTITUD",
    "DEPARTAMENTO",
    "PROVINCIA",
    "DISTRITO",
    "FECHA",
    "HORA",
    "PM2_5",
]


def fixture(tmp_path, points):
    source = tmp_path / "input.csv"
    with source.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for hour, value in points:
            writer.writerow(
                ["demo", "-77", "-12", "10", "LIMA", "LIMA", "demo", "20240101", hour, value]
            )
    acquisition = AcquisitionSpec(
        source_id="fixture",
        resource_url="https://example.org/data",
        method="local",
        format="csv",
        max_bytes=100000,
    )
    result = ingest_file(acquisition, source, tmp_path / "data")
    return ProfileSpec(
        source_id="fixture",
        kind="senamhi",
        manifest=result.manifest,
        raw_root=tmp_path / "data/raw",
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        columns=HEADER,
        signals=["PM2_5"],
    )


def read(run, name):
    with duckdb.connect() as c:
        result = c.execute("SELECT * FROM read_parquet(?)", [str(run / f"{name}.parquet")])
        names = [item[0] for item in result.description]
        return [dict(zip(names, row, strict=True)) for row in result.fetchall()]


def test_profile_exports_real_counts_markers_and_conflicts_without_deleting_rows(tmp_path):
    spec = fixture(
        tmp_path,
        [
            ("10000", "10"),
            ("10000", "10"),
            ("20000", "20"),
            ("20000", "30"),
            ("30000", ""),
            ("40000", "-"),
            ("50000", "bad"),
            ("60000", "NaN"),
            ("70000", "inf"),
            ("80000", "-2"),
            ("90000", "0"),
        ],
    )
    result = profile(spec, tmp_path / "reports")
    dataset = read(result, "datasets")[0]
    signal = read(result, "signals")[0]
    assert dataset["rows"] == 11 and dataset["exact_duplicate_rows"] == 1
    assert signal["finite_count"] == 6 and signal["empty_count"] == 1
    assert signal["marker_count"] == 2 and signal["invalid_numeric_count"] == 1
    assert (
        signal["nonfinite_count"] == 1
        and signal["negative_count"] == 1
        and signal["zero_count"] == 1
    )
    assert signal["duplicate_extra_rows"] == 2 and signal["conflict_slots"] == 1
    assert signal["minimum"] == -2 and signal["maximum"] == 30
    assert {r["token"]: r["count"] for r in read(result, "tokens")} == {
        "-": 1,
        "bad": 1,
        "NaN": 1,
        "inf": 1,
    }
    assert json.loads((result / "manifest.json").read_text())["input_sha256"] == spec.sha256


def test_gap_and_constant_runs_ignore_order_and_break_at_missing_or_conflicting_slots(tmp_path):
    spec = fixture(
        tmp_path,
        [
            ("70000", "5"),
            ("10000", "5"),
            ("20000", "5"),
            ("30000", ""),
            ("50000", "5"),
            ("60000", "5"),
        ],
    )
    result = profile(spec, tmp_path / "out")
    row = read(result, "signals")[0]
    assert row["observed_hour_slots"] == 5 and row["expected_hour_slots"] == 7
    assert row["missing_hour_slots"] == 2 and row["longest_gap_hours"] == 2
    assert row["longest_constant_run_hours"] == 3 and row["is_constant"]
    assert row["clock_status"] == "unverified_source_clock"


def test_hourly_parser_rejects_invalid_calendar_dates_and_24_hour_rollover(tmp_path):
    spec = fixture(tmp_path, [("240000", "1"), ("126000", "2"), ("10000", "3")])
    run = profile(spec, tmp_path / "out")
    assert read(run, "datasets")[0]["unparsed_start_rows"] == 2


def test_repeated_runs_do_not_overwrite_inputs_or_reports(tmp_path):
    spec = fixture(tmp_path, [("10000", "1")])
    before = spec.manifest.read_bytes()
    first = profile(spec, tmp_path / "out")
    second = profile(spec, tmp_path / "out")
    assert first != second and spec.manifest.read_bytes() == before
    assert (first / "signals.parquet").read_bytes() == (second / "signals.parquet").read_bytes()


def test_corrupt_input_fails_before_publishing_reports(tmp_path):
    spec = fixture(tmp_path, [("10000", "1")])
    spec = spec.model_copy(update={"sha256": "0" * 64})
    with pytest.raises(ValueError):
        profile(spec, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_extreme_values_are_flagged_but_retained(tmp_path):
    spec = fixture(tmp_path, [(str(i * 10000), "1") for i in range(1, 10)] + [("100000", "1000")])
    row = read(profile(spec, tmp_path / "out"), "signals")[0]
    assert row["extreme_count"] == 1 and row["maximum"] == 1000 and row["finite_count"] == 10


def oefa_fixture(tmp_path):
    header = [
        "NOMBRE_PUNTO",
        "ESTE",
        "NORTE",
        "ALTITUD",
        "ZONA",
        "DATUM",
        "DEPARTAMENTO",
        "PROVINCIA",
        "DISTRITO",
        "NOMBRE_EVALUACION",
        "PERIODO",
        "UNIDAD_MEDIDA",
        "TIPO_ANALISIS",
        "TIPO_MUESTRA",
        "PROCEDENCIA_MUESTRA",
        "FECHA_INICIO",
        "HORA_INICIO",
        "FECHA_FIN",
        "HORA_FIN",
        "PM2.5",
    ]
    source = tmp_path / "oefa.csv"
    with source.open("w", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        for hour, period, unit in [
            (1, "1 hora", "ug/m3"),
            (3, "1 hora", "ug/m3"),
            (1, "24 horas", "ug/m3"),
            (2, "1 hora", "mg/m3"),
        ]:
            writer.writerow(
                [
                    "same-name",
                    "500000",
                    "9000000",
                    "10",
                    "18",
                    "WGS84",
                    "LIMA",
                    "LIMA",
                    "demo",
                    "evaluation-A",
                    period,
                    unit,
                    "PM2.5",
                    "simple",
                    "aire",
                    "2024-01-01",
                    f"1899-12-31 {hour:02d}:00:00",
                    "NA",
                    "NA",
                    "10",
                ]
            )
    acq = AcquisitionSpec(
        source_id="fixture-oefa",
        resource_url="https://example.org/oefa",
        method="local",
        format="csv",
        csv_delimiter=";",
        max_bytes=100000,
    )
    result = ingest_file(acq, source, tmp_path / "data")
    return ProfileSpec(
        source_id="fixture-oefa",
        kind="oefa",
        manifest=result.manifest,
        raw_root=tmp_path / "data/raw",
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        columns=header,
        signals=["PM2.5"],
    )


def test_oefa_keeps_periods_and_units_separate_and_does_not_claim_utc(tmp_path):
    spec = oefa_fixture(tmp_path)
    run = profile(spec, tmp_path / "out")
    signals = read(run, "signals")
    assert len(signals) == 3
    grouped = {
        (json.loads(r["series_context"])[1], json.loads(r["series_context"])[2]): r for r in signals
    }
    assert grouped["1 hora", "ug/m3"]["missing_hour_slots"] == 1
    assert grouped["24 horas", "ug/m3"]["expected_hour_slots"] is None
    assert grouped["1 hora", "mg/m3"]["finite_count"] == 1
    assert read(run, "stations")[0]["series_count"] == 3
    assert read(run, "datasets")[0]["first_parsed_clock"].tzinfo is None
    for table in ["datasets", "stations", "signals", "tokens"]:
        for row in read(run, table):
            assert row["input_sha256"] == spec.sha256 and row["source_id"] == spec.source_id


def test_empty_and_invalid_decimal_comma_do_not_become_zero(tmp_path):
    spec = fixture(tmp_path, [("10000", ""), ("20000", "1,25")])
    row = read(profile(spec, tmp_path / "out"), "signals")[0]
    assert (
        row["empty_count"] == 1 and row["invalid_numeric_count"] == 1 and row["finite_count"] == 0
    )
    assert row["minimum"] is None and row["expected_hour_slots"] is None


def test_hash_is_rechecked_even_if_modified_file_metadata_is_restored(tmp_path):
    import os

    spec = fixture(tmp_path, [("10000", "1")])
    manifest = json.loads(spec.manifest.read_text())
    original = spec.raw_root / manifest["artifact_path"]
    before = original.stat()

    def mutate(message):
        if "señal" in message:
            original.write_bytes(original.read_bytes().replace(b"10000,1", b"10000,2"))
            os.utime(original, ns=(before.st_atime_ns, before.st_mtime_ns))

    with pytest.raises(ValueError, match="SHA-256"):
        profile(spec, tmp_path / "out", progress=mutate)
    assert not list((tmp_path / "out").glob("*/manifest.json"))
