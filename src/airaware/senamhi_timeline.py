"""Grilla horaria con procedencia y máscaras a partir de la auditoría SENAMHI."""

import json
from pathlib import Path
from typing import Annotated

import duckdb
import typer

from airaware.derived_artifacts import new_bundle, sha256_file

alignment_app = typer.Typer(no_args_is_help=True, help="Alinear series horarias locales.")
HOURS_FILE = "hours.parquet"
TIMELINE_VERSION = "senamhi-hourly-v1"

GRID_QUERY = """
WITH compatible AS (
    SELECT *, sha256(to_json(list_value(
        station_key, sensor_id, parameter_raw, parameter, unit
    ))) AS series_id
    FROM audit
    WHERE provenance.source_id = 'senamhi-lima-csv'
      AND decision IN ('kept', 'duplicate', 'unusable_value', 'conflict')
      AND start IS NULL AND "end" IS NULL
      AND observed_at = date_trunc('hour', observed_at)
), slots AS (
    SELECT series_id, observed_at, count(*) FILTER (WHERE decision = 'kept') AS kept,
           max(value) FILTER (WHERE decision = 'kept') AS value,
           max(observation_id) FILTER (WHERE decision = 'kept') AS observation_id,
           max(available_at) FILTER (WHERE decision = 'kept') AS available_at,
           max(quality) FILTER (WHERE decision = 'kept') AS quality,
           bool_or(decision = 'conflict') AS conflicted,
           list(observation_id ORDER BY observation_id) AS source_observation_ids
    FROM compatible GROUP BY series_id, observed_at
), span AS (
    SELECT series_id, station_key, sensor_id, parameter_raw, parameter, unit,
           min(observed_at) AS first_hour, max(observed_at) AS last_hour
    FROM compatible GROUP BY series_id, station_key, sensor_id, parameter_raw, parameter, unit
)
SELECT span.series_id, station_key, sensor_id, parameter_raw, parameter, unit, hour AS observed_at,
       CASE WHEN kept = 1 AND NOT conflicted THEN value END AS value,
       CASE WHEN kept = 1 AND NOT conflicted THEN observation_id END AS observation_id,
       CASE WHEN kept = 1 AND NOT conflicted THEN available_at END AS available_at,
       CASE WHEN kept = 1 AND NOT conflicted THEN quality END AS quality,
       coalesce(source_observation_ids, []::VARCHAR[]) AS source_observation_ids,
       CASE
           WHEN kept IS NULL THEN 'absent_hour'
           WHEN kept > 1 OR conflicted THEN 'conflict'
           WHEN kept = 1 THEN 'observed'
           ELSE 'unusable_value'
       END AS status,
       NOT coalesce(kept = 1 AND NOT conflicted, false) AS is_missing,
       false AS is_imputed
FROM span
CROSS JOIN LATERAL generate_series(first_hour, last_hour, INTERVAL '1 hour') AS grid(hour)
LEFT JOIN slots ON slots.series_id = span.series_id AND slots.observed_at = grid.hour
ORDER BY span.series_id, grid.hour
"""


def align_senamhi(audit: Path, output: Path) -> None:
    """Materializar una hora por señal compatible dentro de sus extremos publicados."""
    audit_digest = sha256_file(audit)
    with new_bundle(output) as staging, duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone = 'UTC'")
        db.read_parquet(str(audit), hive_partitioning=False).create_view("audit")
        hours = staging / HOURS_FILE
        db.execute(f"COPY ({GRID_QUERY}) TO ? (FORMAT PARQUET)", [str(hours)])
        if sha256_file(audit) != audit_digest:
            data_error = "El archivo de auditoría cambió durante la alineación"
            raise ValueError(data_error)
        counts = db.execute(
            """SELECT station_key, parameter_raw, status, count(*) AS hours
               FROM read_parquet(?) GROUP BY ALL ORDER BY ALL""",
            [str(hours)],
        ).fetchall()
        manifest = {
            "version": TIMELINE_VERSION,
            "timezone": "UTC",
            "frequency_hours": 1,
            "input_sha256": audit_digest,
            "output_sha256": sha256_file(hours),
            "counts": [
                {"station_key": station, "parameter_raw": signal, "status": status, "hours": size}
                for station, signal, status, size in counts
            ],
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


@alignment_app.command("senamhi")
def senamhi(
    input: Annotated[Path, typer.Option(help="Auditoría Parquet generada por curate senamhi.")],
    output: Annotated[Path, typer.Option(help="Carpeta nueva para la grilla y el manifiesto.")],
) -> None:
    """Construir una grilla horaria SENAMHI a partir de las horas publicadas."""
    try:
        align_senamhi(input, output)
    except (OSError, ValueError, duckdb.Error) as error:
        typer.echo(f"No se pudo alinear SENAMHI: {error}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Grilla horaria SENAMHI: {output}")
