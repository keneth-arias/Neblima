import csv
from hashlib import sha256
from pathlib import Path

import duckdb
from typer.testing import CliRunner

from airaware.cli import app
from airaware.normalization import stream_observations, write_parquet_output
from airaware.senamhi_preparation import load_policy

POLICY = Path("configs/normalization/senamhi.yaml")


def normalized(tmp_path: Path) -> Path:
    source = tmp_path / "input.csv"
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "ESTACION",
                "LONGITUD",
                "LATITUD",
                "ALTITUD",
                "DEPARTAMENTO",
                "PROVINCIA",
                "DISTRITO",
                "FECHA",
                "HORA",
                "PM10",
                "PM2_5",
                "NO2",
            ]
        )
        for longitude, hour, pm10, pm25, province in [
            ("-77.1", "0", "9", "0", "LIMA"),
            ("-77.1", "0", "8", "0.0", "LIMA"),
            ("-77.1", "0", "", "", "LIMA"),
            ("-77.2", "0", "8", "2", "LIMA"),
            ("-77.1", "10000", "8", "nan", "LIMA"),
            ("-77.1", "13000", "8", "3", "LIMA"),
            ("-77.1", "20000", "8", "4", "CALLAO"),
            ("-77.1", "30000", "8", "5", "LIMA"),
            ("-77.1", "30000", "8", "6", "LIMA"),
        ]:
            writer.writerow(
                [
                    "Estación",
                    longitude,
                    "-12",
                    "30",
                    "LIMA",
                    province,
                    "Distrito",
                    "20240101",
                    hour,
                    pm10,
                    pm25,
                    "4",
                ]
            )
    policy = load_policy(POLICY).model_copy(
        update={"input_sha256": sha256(source.read_bytes()).hexdigest()}
    )
    target = tmp_path / "normalized"
    write_parquet_output(stream_observations(source, policy, batch_size=2), policy, target)
    return target


def curate(source: Path, target: Path):
    return CliRunner().invoke(
        app, ["curate", "senamhi", "--input", str(source), "--output", str(target)]
    )


def test_curation_keeps_lineage_and_resolves_each_signal(tmp_path):
    target = tmp_path / "audit.parquet"
    source = normalized(tmp_path)
    result = curate(source, target)
    assert result.exit_code == 0, result.output
    with duckdb.connect() as db:
        records = db.execute(
            """SELECT provenance.record, parameter_raw, decision, value, kept_observation_id,
                      observation_id, station_key
               FROM read_parquet(?) ORDER BY provenance.record, parameter_raw""",
            [str(target)],
        ).fetchall()
    assert len(records) == 27
    pm25 = [row for row in records if row[1] == "PM2_5"]
    assert [row[2] for row in pm25] == [
        "kept",
        "duplicate",
        "unusable_value",
        "kept",
        "unusable_value",
        "off_hour",
        "outside_lima",
        "conflict",
        "conflict",
    ]
    assert pm25[0][3] == 0
    assert pm25[0][4] == pm25[1][4] == pm25[2][4] == pm25[0][5]
    assert pm25[0][6] != pm25[3][6]
    assert pm25[7][4] is None
    assert [row[2] for row in records if row[1] == "PM10"][:3] == [
        "conflict",
        "conflict",
        "unusable_value",
    ]
    assert curate(source, target).exit_code == 1


def test_curation_rejects_changed_parquet_before_publication(tmp_path):
    source = normalized(tmp_path)
    next(source.rglob("*.parquet")).write_bytes(b"alterado")
    target = tmp_path / "audit.parquet"
    result = curate(source, target)
    assert result.exit_code == 1
    assert "Artefacto ausente o distinto del manifiesto" in result.output
    assert not target.exists()
