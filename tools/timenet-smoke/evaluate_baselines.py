"""Evaluar referencias horarias sobre las tareas TimeF congeladas de Lima."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
from export_benchmark import sha256_file, verified_parquet
from timenet.reader import TimeFReader

FIT = """
CREATE TEMP TABLE fit AS
WITH training AS (
    SELECT series_id, observed_at, value FROM grid
    WHERE observed_at < ?::TIMESTAMPTZ AND isfinite(value)
), hourly AS (
    SELECT series_id, hour(observed_at) AS hour_utc, avg(value) AS seasonal
    FROM training GROUP BY ALL
), scales AS (
    SELECT recent.series_id, avg(abs(recent.value - daily.value)) AS scale,
           quantile_cont(recent.value, 0.95) AS high_threshold
    FROM training AS recent
    LEFT JOIN training AS daily ON recent.series_id = daily.series_id
        AND daily.observed_at = recent.observed_at - INTERVAL '24 hours'
    GROUP BY recent.series_id
)
SELECT * FROM hourly JOIN scales USING (series_id)
"""

PREDICT = """
WITH forecast AS (
    SELECT tasks.*, forecast_hour, actual,
           target_start + (forecast_hour - 1) * INTERVAL '1 hour' AS target_at
    FROM tasks JOIN targets USING (window_id)
)
SELECT forecast.window_id, forecast.series_id, station_key, split, origin_at, target_at,
       forecast_hour, actual, last.value AS persistence, previous_day.value AS daily,
       fit.seasonal, fit.scale, actual >= fit.high_threshold AS high_concentration,
       CASE
           WHEN month(target_at) IN (12, 1, 2) THEN 'DJF'
           WHEN month(target_at) IN (3, 4, 5) THEN 'MAM'
           WHEN month(target_at) IN (6, 7, 8) THEN 'JJA'
           ELSE 'SON'
       END AS season
FROM forecast
LEFT JOIN grid AS last ON last.series_id = forecast.series_id AND last.observed_at = origin_at
LEFT JOIN grid AS previous_day ON previous_day.series_id = forecast.series_id
    AND previous_day.observed_at = target_at - INTERVAL '24 hours'
LEFT JOIN fit ON fit.series_id = forecast.series_id AND fit.hour_utc = hour(target_at)
"""

METRICS = """
WITH errors AS (
    SELECT model, split, station_key, forecast_hour, season, high_concentration, scale,
           abs(predicted - actual) AS absolute_error
    FROM predictions UNPIVOT (predicted FOR model IN (persistence, daily, seasonal))
)
SELECT model, split, station_key, forecast_hour, season, high_concentration,
       count(*) AS n, avg(absolute_error) AS mae,
       sqrt(avg(absolute_error * absolute_error)) AS rmse,
       avg(absolute_error / nullif(scale, 0)) AS mase,
       count(*) FILTER (WHERE scale > 0) AS n_mase
FROM errors
GROUP BY GROUPING SETS (
    (model, split), (model, split, station_key), (model, split, forecast_hour),
    (model, split, season), (model, split, high_concentration),
    (model, split, station_key, forecast_hour)
)
"""

FROZEN_TARGETS = """
SELECT window_id, position AS forecast_hour, actual
FROM frozen, UNNEST(target_values) WITH ORDINALITY AS target(actual, position)
"""


def prepare_tasks(db: duckdb.DuckDBPyConnection, release: Path, partitions: Path) -> None:
    with TimeFReader.open(release) as reader:
        reader.verify()
        db.register(
            "timef_tasks", reader.read_task_table().select(["task_id", "split", "metadata"])
        )
        db.register(
            "timef_targets",
            reader.read_target_table().select(["task_id", "position", "float_value"]),
        )
    db.execute(
        "CREATE TEMP TABLE frozen AS SELECT * FROM read_parquet(?) WHERE split <> 'purged'",
        [str(partitions)],
    )
    db.execute("""
        CREATE TEMP TABLE task_keys AS
        SELECT task_id, split, CAST(metadata AS JSON)->>'window_id' AS window_id,
               (CAST(metadata AS JSON)->>'origin_at')::TIMESTAMPTZ AS origin_at,
               (CAST(metadata AS JSON)->>'target_start')::TIMESTAMPTZ AS target_start,
               CAST(metadata AS JSON)->>'series_id' AS series_id
        FROM timef_tasks
    """)
    invalid = db.execute("""
        SELECT count(*) FROM task_keys t FULL JOIN frozen f USING (window_id)
        WHERE t.split IS DISTINCT FROM f.split OR t.series_id IS DISTINCT FROM f.series_id
           OR t.origin_at IS DISTINCT FROM f.origin_at
           OR t.target_start IS DISTINCT FROM f.target_start
    """).fetchone()
    distinct_counts = db.execute(
        "SELECT count(*), count(DISTINCT window_id) FROM task_keys"
    ).fetchone()
    if invalid != (0,) or distinct_counts is None or distinct_counts[0] != distinct_counts[1]:
        raise ValueError("Las tareas TimeF no coinciden con las ventanas congeladas")
    db.execute("""
        CREATE TEMP TABLE tasks AS
        SELECT window_id, station_key, series_id, split, origin_at, target_start
        FROM frozen
    """)
    db.execute("""
        CREATE TEMP TABLE targets AS
        SELECT window_id, position + 1 AS forecast_hour, float_value AS actual
        FROM timef_targets JOIN task_keys USING (task_id)
    """)
    invalid = db.execute(f"""
        SELECT count(*) FROM targets t FULL JOIN ({FROZEN_TARGETS}) f
        USING (window_id, forecast_hour) WHERE t.actual IS DISTINCT FROM f.actual
    """).fetchone()
    target_count = db.execute(
        "SELECT count(*), count(DISTINCT (window_id, forecast_hour)) FROM targets"
    ).fetchone()
    if invalid != (0,) or target_count is None or target_count[0] != target_count[1]:
        raise ValueError("Los objetivos TimeF difieren del manifiesto de ventanas")


def evaluate(release: Path, timeline: Path, partitions: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"La salida ya existe: {output}")
    hours, grid_meta = verified_parquet(timeline, "hours.parquet", "senamhi-hourly-v1")
    splits, split_meta = verified_parquet(partitions, "splits.parquet", "senamhi-pm25-splits-v1")
    if (
        split_meta["timeline_sha256"] != grid_meta["output_sha256"]
        or split_meta["history_hours"] != 24
        or split_meta["horizon_hours"] != 6
    ):
        raise ValueError("Se requiere la grilla vinculada a las particiones 24/6")
    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        TemporaryDirectory(dir=output.parent, prefix=".baseline-") as temp,
        duckdb.connect(config={"threads": 1}) as db,
    ):
        staging = Path(temp) / "result"
        staging.mkdir()
        db.execute("SET TimeZone='UTC'")
        data = db.read_parquet(str(hours)).filter("parameter_raw = 'PM2_5' AND unit = 'ug/m3'")
        data.project("series_id, observed_at, value").create_view("grid")
        prepare_tasks(db, release, splits)
        db.execute(FIT, [split_meta["validation_start"]])
        db.execute("CREATE TEMP TABLE predictions AS " + PREDICT)
        incomplete = db.execute("""
            SELECT count(*) FROM predictions
            WHERE NOT coalesce(isfinite(persistence) AND isfinite(daily)
                               AND isfinite(seasonal) AND isfinite(actual), false)
        """).fetchone()
        if incomplete != (0,):
            raise ValueError("Las tres referencias requieren cobertura sobre los mismos objetivos")
        selection = db.execute("""
            SELECT model, avg(abs(predicted - actual)) AS mae
            FROM predictions UNPIVOT (predicted FOR model IN (persistence, daily, seasonal))
            WHERE split='validation' GROUP BY model ORDER BY mae, model
        """).fetchall()
        if len(selection) != 3:
            raise ValueError("Faltan referencias comparables en validación")
        db.execute("CREATE TEMP TABLE metrics AS " + METRICS)
        for name, query in (
            (
                "predictions.parquet",
                """SELECT * EXCLUDE (scale) FROM predictions ORDER BY window_id, forecast_hour""",
            ),
            ("metrics.parquet", "SELECT * FROM metrics ORDER BY ALL"),
            ("fit.parquet", "SELECT * FROM fit ORDER BY series_id, hour_utc"),
        ):
            db.execute(f"COPY ({query}) TO ? (FORMAT PARQUET)", [str(staging / name)])
        manifest = {
            "version": "lima-pm25-baselines-v1",
            "timef_manifest_sha256": sha256_file(release / "manifest.json"),
            "timeline_sha256": grid_meta["output_sha256"],
            "splits_sha256": split_meta["output_sha256"],
            "validation_start": split_meta["validation_start"],
            "primary_baseline": selection[0][0],
            "validation_mae": dict(selection),
            "unit": "ug/m3",
            "files": {str(p.name): sha256_file(p) for p in sorted(staging.iterdir())},
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if output.exists():
            raise FileExistsError(f"La salida ya existe: {output}")
        os.rename(staging, output)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--splits", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.release, args.timeline, args.splits, args.output), indent=2))


if __name__ == "__main__":
    main()
