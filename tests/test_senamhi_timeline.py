import json
from hashlib import file_digest

import duckdb
import pyarrow.parquet as pq
from typer.testing import CliRunner

from airaware.cli import app


def test_hourly_grid_keeps_masks_lineage_and_compatible_series(tmp_path):
    audit = tmp_path / "audit.parquet"
    with duckdb.connect() as db:
        rows = db.sql("""
            SELECT 'estacion' AS station_key, sensor_id, 'PM2_5' AS parameter_raw,
                   'PM2.5' AS parameter, 'ug/m3' AS unit,
                   TIMESTAMPTZ '2024-01-01 00:00:00+00'
                      + hours * INTERVAL '1 hour' AS observed_at,
                   NULL::TIMESTAMPTZ AS start,
                   CASE WHEN observation_id = 'diario'
                       THEN TIMESTAMPTZ '2024-01-02 00:00:00+00' END AS "end",
                   NULL::TIMESTAMPTZ AS available_at, 'unknown' AS quality,
                   struct_pack(source_id := 'senamhi-lima-csv') AS provenance,
                   observation_id, value, decision
            FROM (VALUES
                (0, 'cero', 0., 'kept', NULL),
                (0, 'vacio', NULL, 'unusable_value', NULL),
                (1, 'nulo', NULL, 'unusable_value', NULL),
                (2, 'conflicto1', 10., 'conflict', NULL),
                (2, 'conflicto2', 11., 'conflict', NULL),
                (4, 'valor', 4., 'kept', NULL),
                (6, 'fuera', 6., 'off_hour', NULL),
                (7, 'diario', 7., 'kept', NULL),
                (0, 'independiente', 8., 'kept', 'sensor-2')
            ) AS samples(hours, observation_id, value, decision, sensor_id)
        """).to_arrow_table()
    pq.write_table(rows, audit)
    runner = CliRunner()
    outputs = [tmp_path / "timeline", tmp_path / "repeat"]
    for output in outputs:
        run = runner.invoke(
            app, ["align", "senamhi", "--input", str(audit), "--output", str(output)]
        )
        assert run.exit_code == 0, run.output
    result = pq.read_table(outputs[0] / "hours.parquet")
    assert result.equals(pq.read_table(outputs[1] / "hours.parquet"))
    rows = [row for row in result.to_pylist() if row["sensor_id"] is None]
    assert [row["observed_at"].hour for row in rows] == [0, 1, 2, 3, 4]
    assert [row["value"] for row in rows] == [0.0, None, None, None, 4.0]
    assert [row["status"] for row in rows] == [
        "observed",
        "unusable_value",
        "conflict",
        "absent_hour",
        "observed",
    ]
    assert [row["is_missing"] for row in rows] == [False, True, True, True, False]
    assert not any(row["is_imputed"] for row in rows)
    assert rows[0]["observation_id"] == "cero"
    assert rows[2]["source_observation_ids"] == ["conflicto1", "conflicto2"]
    assert rows[3]["source_observation_ids"] == []
    assert len(set(result["series_id"].to_pylist())) == 2
    with audit.open("rb") as stream:
        assert json.loads((outputs[0] / "manifest.json").read_text())["input_sha256"] == (
            file_digest(stream, "sha256").hexdigest()
        )
    rerun = runner.invoke(
        app, ["align", "senamhi", "--input", str(audit), "--output", str(outputs[0])]
    )
    assert rerun.exit_code != 0
