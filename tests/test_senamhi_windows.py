import json
from pathlib import Path

import duckdb
import pyarrow.parquet as pq
from typer.testing import CliRunner

from airaware.cli import app
from airaware.derived_artifacts import sha256_file
from airaware.senamhi_timeline import TIMELINE_VERSION


def sample(tmp_path: Path) -> Path:
    source = tmp_path / "timeline"
    source.mkdir()
    with duckdb.connect() as db:
        table = db.sql("""
            SELECT series_id, series_id AS station_key, 'PM2_5' AS parameter_raw,
                   'ug/m3' AS unit,
                   TIMESTAMPTZ '2024-01-01 00:00:00+00' + h * INTERVAL '1 hour' AS observed_at,
                   CASE WHEN h <> 4 THEN h::DOUBLE END AS value, h = 4 AS is_missing,
                   false AS is_imputed, CASE WHEN h = 4 THEN 'conflict' ELSE 'observed' END
                   AS status
            FROM (SELECT 'a' AS series_id, h FROM range(11) AS r(h)
                  UNION ALL SELECT 'b' AS series_id, h FROM range(3) AS r(h))
        """).to_arrow_table()
    pq.write_table(table, source / "hours.parquet")
    (source / "manifest.json").write_text(
        json.dumps(
            {
                "version": TIMELINE_VERSION,
                "output_sha256": sha256_file(source / "hours.parquet"),
            }
        )
    )
    return source


def windows(source, output, *, step=1):
    return CliRunner().invoke(
        app,
        [
            "benchmark",
            "windows",
            "--input",
            str(source),
            "--output",
            str(output),
            "--history",
            "2",
            "--horizon",
            "2",
            "--step",
            str(step),
        ],
    )


def test_build_windows_with_measured_targets_and_disjoint_discard_counts(tmp_path):
    source = sample(tmp_path)
    output = tmp_path / "benchmark"
    result = windows(source, output)
    assert result.exit_code == 0, result.output
    rows = pq.read_table(output / "windows.parquet").to_pylist()
    assert [row["origin_at"].hour for row in rows] == [1, 6, 7, 8]
    assert all(row["series_id"] == "a" for row in rows)
    assert rows[0]["history_start"].hour == 0
    assert rows[0]["target_end"].hour == 3
    assert rows[0]["target_values"] == [2.0, 3.0]
    assert rows[0]["target_mean"] == 2.5
    counts = json.loads((output / "manifest.json").read_text())["counts"]
    assert counts == [
        {
            "series_id": "a",
            "candidates": 8,
            "complete": 4,
            "history_missing": 2,
            "future_missing": 2,
        }
    ]
    repeat = tmp_path / "repeat"
    assert windows(source, repeat).exit_code == 0
    assert pq.read_table(output / "windows.parquet").equals(
        pq.read_table(repeat / "windows.parquet")
    )
    stepped = tmp_path / "stepped"
    assert windows(source, stepped, step=2).exit_code == 0
    assert [
        row["origin_at"].hour for row in pq.read_table(stepped / "windows.parquet").to_pylist()
    ] == [1, 7]


def test_windows_refuse_tampered_timeline(tmp_path):
    source = sample(tmp_path)
    with (source / "hours.parquet").open("ab") as stream:
        stream.write(b"alterado")
    output = tmp_path / "benchmark"
    result = windows(source, output)
    assert result.exit_code == 1
    assert "SHA-256" in result.output
    assert not output.exists()
