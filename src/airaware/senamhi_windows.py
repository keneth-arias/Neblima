"""Ventanas completas de pronóstico retrospectivo de PM2.5 en Lima."""

import json
from pathlib import Path
from typing import Annotated

import duckdb
import typer

from airaware.derived_artifacts import new_bundle, sha256_file
from airaware.senamhi_timeline import HOURS_FILE, TIMELINE_VERSION

benchmark_app = typer.Typer(no_args_is_help=True, help="Preparar evaluaciones locales.")
WINDOWS_FILE = "windows.parquet"
WINDOWS_VERSION = "senamhi-pm25-windows-v1"

CANDIDATES = """
WITH measured AS (
    SELECT series_id, station_key, observed_at,
           CASE WHEN status = 'observed' AND NOT is_missing AND NOT is_imputed
                     AND isfinite(value) THEN value END AS value
    FROM read_parquet(?) WHERE parameter_raw = 'PM2_5' AND unit = 'ug/m3'
), bounded AS (
    SELECT *,
           min(observed_at) FILTER (WHERE value IS NOT NULL) OVER series AS first_hour,
           max(observed_at) FILTER (WHERE value IS NOT NULL) OVER series AS last_hour
    FROM measured WINDOW series AS (PARTITION BY series_id)
), framed AS (
    SELECT series_id, station_key, observed_at AS origin_at,
           first(observed_at) OVER history AS history_start,
           first(observed_at) OVER future AS target_start,
           last(observed_at) OVER future AS target_end,
           count(value) OVER history = {history}
               AND date_diff('hour', history_start, observed_at) = {lookback} AS history_complete,
           count(value) OVER future = {horizon}
               AND date_diff('hour', observed_at, target_end) = {horizon} AS future_complete,
           list(value) OVER future AS target_values, avg(value) OVER future AS target_mean,
           date_diff('hour', first_hour, observed_at) - {lookback} AS offset_hour,
           date_diff('hour', observed_at, last_hour) AS remaining
    FROM bounded WHERE observed_at BETWEEN first_hour AND last_hour
    WINDOW
        history AS (PARTITION BY series_id ORDER BY observed_at
                    ROWS BETWEEN {lookback} PRECEDING AND CURRENT ROW),
        future AS (PARTITION BY series_id ORDER BY observed_at
                   ROWS BETWEEN 1 FOLLOWING AND {horizon} FOLLOWING)
)
SELECT * FROM framed
WHERE offset_hour >= 0 AND offset_hour % {step} = 0 AND remaining >= {horizon}
"""


def build_windows(timeline: Path, output: Path, *, history: int, horizon: int, step: int) -> None:
    """Fijar referencias a la grilla y escribir objetivos completos por ventana."""
    if not (1 <= history <= 168 and 1 <= horizon <= 48 and step >= 1):
        raise ValueError("Historia, horizonte o paso fuera del contrato")
    hours = timeline / HOURS_FILE
    source = json.loads((timeline / "manifest.json").read_text(encoding="utf-8"))
    source_hash = sha256_file(hours)
    if source["version"] != TIMELINE_VERSION or source["output_sha256"] != source_hash:
        raise ValueError("Versión o SHA-256 de la grilla distinto del manifiesto")
    with new_bundle(output) as staging, duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone = 'UTC'")
        query = CANDIDATES.format(history=history, lookback=history - 1, horizon=horizon, step=step)
        db.execute(f"CREATE TEMP TABLE candidates AS {query}", [str(hours)])
        if sha256_file(hours) != source_hash:
            raise ValueError("La grilla cambió durante la lectura")
        counts = db.execute("""
            SELECT series_id, count(*) AS candidates,
                   count(*) FILTER (WHERE history_complete AND future_complete) AS complete,
                   count(*) FILTER (WHERE NOT history_complete) AS history_missing,
                   count(*) FILTER (WHERE history_complete AND NOT future_complete)
                       AS future_missing
            FROM candidates GROUP BY series_id ORDER BY series_id
        """).fetchall()
        output_file = staging / WINDOWS_FILE
        db.execute(
            """
            COPY (
                SELECT sha256(to_json(list_value(series_id, origin_at::VARCHAR,
                       history_start::VARCHAR, target_end::VARCHAR))) AS window_id,
                       series_id, station_key, history_start, origin_at, target_start, target_end,
                       target_values, target_mean
                FROM candidates WHERE history_complete AND future_complete
                ORDER BY series_id, origin_at
            ) TO ? (FORMAT PARQUET)
            """,
            [str(output_file)],
        )
        manifest = {
            "version": WINDOWS_VERSION,
            "input_sha256": source_hash,
            "output_sha256": sha256_file(output_file),
            "history_hours": history,
            "horizon_hours": horizon,
            "step_hours": step,
            "counts": [
                {
                    "series_id": series,
                    "candidates": total,
                    "complete": complete,
                    "history_missing": missing,
                    "future_missing": future,
                }
                for series, total, complete, missing, future in counts
            ],
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


@benchmark_app.command("windows")
def windows(
    input: Annotated[Path, typer.Option(help="Carpeta de grilla SENAMHI y manifiesto.")],
    output: Annotated[Path, typer.Option(help="Carpeta nueva de ventanas.")],
    history: Annotated[int, typer.Option(help="Horas completas de historia.", min=1, max=168)] = 24,
    horizon: Annotated[int, typer.Option(help="Horas completas de objetivo.", min=1, max=48)] = 6,
    step: Annotated[int, typer.Option(help="Paso entre orígenes candidatos.", min=1)] = 1,
) -> None:
    """Generar tareas retrospectivas con historia y objetivo medidos."""
    try:
        build_windows(input, output, history=history, horizon=horizon, step=step)
    except (OSError, ValueError, KeyError, duckdb.Error) as error:
        typer.echo(f"No se pudieron generar ventanas: {error}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Ventanas SENAMHI: {output}")
