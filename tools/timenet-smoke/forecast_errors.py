"""Resumir el error frente a persistencia en un archivo de predicciones pareadas."""

import argparse
import json
from pathlib import Path

import duckdb
from export_senamhi import sha256_file

METRICS = """
WITH errors AS (
    SELECT station_key, target_at, forecast_hour, high_concentration,
           abs(predicted - actual) AS error, abs(persistence - actual) AS baseline
    FROM paired
)
SELECT station_key, forecast_hour, high_concentration, count(*) AS targets,
       count(DISTINCT (station_key, target_at)) AS station_hours,
       avg(error) AS mae, avg(baseline) AS persistence_mae,
       avg(error - baseline) AS delta_mae
FROM errors
GROUP BY GROUPING SETS ((), (station_key), (forecast_hour), (high_concentration))
ORDER BY station_key NULLS FIRST, forecast_hour NULLS FIRST, high_concentration NULLS FIRST
"""


def summarize(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    path = folder / "paired.parquet"
    if sha256_file(path) != manifest["paired_sha256"]:
        raise ValueError("El SHA-256 de las predicciones pareadas difiere del manifiesto")
    with duckdb.connect(config={"threads": 1}) as db:
        db.read_parquet(str(path)).create_view("paired")
        invalid = db.sql("""
            SELECT count(*) FROM paired
            WHERE station_key IS NULL OR target_at IS NULL OR forecast_hour IS NULL
               OR high_concentration IS NULL OR NOT coalesce(
                    isfinite(actual) AND isfinite(predicted) AND isfinite(persistence), false)
        """).fetchone()
        if invalid != (0,):
            raise ValueError("Faltan mediciones, pronósticos o claves en las predicciones pareadas")
        rows = db.sql(METRICS).to_arrow_table().to_pylist()
    report = {"by_horizon": {}, "by_station": {}, "high_concentration": None}
    for row in rows:
        station = row.pop("station_key")
        hour = row.pop("forecast_hour")
        high = row.pop("high_concentration")
        if station is not None:
            report["by_station"][station] = row
        elif hour is not None:
            report["by_horizon"][str(hour)] = row
        elif high:
            report["high_concentration"] = row
        elif high is None:
            report["overall"] = row
    if not report["overall"]["targets"] or report["overall"]["targets"] != manifest["targets"]:
        raise ValueError("El conteo de objetivos difiere del manifiesto")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Carpeta de salida de paired_forecasts.py")
    print(json.dumps(summarize(parser.parse_args().folder), indent=2, allow_nan=False))
