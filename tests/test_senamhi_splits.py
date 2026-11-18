import json

import duckdb
import pyarrow.parquet as pq
from typer.testing import CliRunner

from airaware.cli import app
from airaware.derived_artifacts import sha256_file
from airaware.senamhi_timeline import TIMELINE_VERSION
from airaware.senamhi_windows import build_windows


def test_split_purges_overlaps_and_late_publication(tmp_path):
    timeline = tmp_path / "timeline"
    timeline.mkdir()
    hours = timeline / "hours.parquet"
    with duckdb.connect() as db:
        table = db.sql("""
            SELECT 'a' AS series_id, 'estacion' AS station_key,
                   'PM2_5' AS parameter_raw, 'ug/m3' AS unit,
                   TIMESTAMPTZ '2024-01-01 00:00:00+00' + h * INTERVAL '1 hour' AS observed_at,
                   CASE WHEN h = 2 THEN observed_at + INTERVAL '2 hours' END AS available_at,
                   h::DOUBLE AS value, false AS is_missing, false AS is_imputed,
                   'observed' AS status
            FROM range(45) AS samples(h)
        """).to_arrow_table()
    pq.write_table(table, hours)
    (timeline / "manifest.json").write_text(
        json.dumps({"version": TIMELINE_VERSION, "output_sha256": sha256_file(hours)})
    )
    windows = tmp_path / "windows"
    build_windows(timeline, windows, history=2, horizon=2, step=1)
    output = tmp_path / "splits"
    result = CliRunner().invoke(
        app,
        [
            "benchmark",
            "split",
            "--input",
            str(windows),
            "--timeline",
            str(timeline),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    rows = pq.read_table(output / "splits.parquet").to_pylist()
    partitions = {
        name: [row for row in rows if row["split"] == name]
        for name in ("train", "validation", "test")
    }
    assert [len(rows) for rows in partitions.values()] == [25, 3, 6]
    train, validation, test = partitions.values()
    assert train[-1]["target_end"] < validation[0]["history_start"]
    assert validation[-1]["target_end"] < test[0]["history_start"]
    purges = [row["purge_reason"] for row in rows if row["split"] == "purged"]
    assert purges.count("late_publication") == 2
    assert purges.count("crosses_cutoff") == 6
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["validation_start"].startswith("2024-01-02 06:00")
    assert manifest["test_start"].startswith("2024-01-02 12:00")
    assert manifest["output_sha256"] == sha256_file(output / "splits.parquet")
