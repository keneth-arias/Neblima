"""Vista horaria de SENAMHI con decisiones por observación y señal."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

import duckdb
import pyarrow as pa
import typer

from airaware.normalization.parquet import OBSERVATION_SCHEMA, verify_output
from airaware.senamhi_preparation import SENAMHI_STATION_FIELDS

curation_app = typer.Typer(
    no_args_is_help=True, help="Construir vistas derivadas con procedencia local."
)

# Mismo orden y codificación de identidad que comparison-v3.
STATION_CONTEXT = (
    "to_json(list_value("
    + ", ".join(f"raw_fields['{field}']" for field in SENAMHI_STATION_FIELDS)
    + "))"
)

AUDIT_QUERY = f"""
WITH identified AS (
    SELECT observation_id, provenance, sensor_id, parameter_raw, parameter, unit,
           value_raw, value, value_status, quality, observed_at, start, "end", available_at,
           {STATION_CONTEXT} AS station_context,
           CASE
               WHEN raw_fields['DEPARTAMENTO'] IS DISTINCT FROM 'LIMA'
                    OR raw_fields['PROVINCIA'] IS DISTINCT FROM 'LIMA' THEN 'outside_lima'
               WHEN nullif(trim(raw_fields['ESTACION']), '') IS NULL THEN 'unknown_station'
               WHEN observed_at IS NULL OR date_trunc('hour', observed_at) != observed_at
                    THEN 'off_hour'
               WHEN kind != 'measured' OR quality = 'invalid' THEN 'ineligible'
           END AS exclusion
    FROM normalized
), candidates AS (
    SELECT *, sha256(provenance.source_id || station_context) AS station_key,
           coalesce(exclusion IS NULL AND value_status = 'finite' AND isfinite(value), false)
               AS eligible
    FROM identified
), slots AS (
    SELECT *,
           min(value) FILTER (WHERE eligible) OVER same_hour AS minimum,
           max(value) FILTER (WHERE eligible) OVER same_hour AS maximum,
           first_value(CASE WHEN eligible THEN observation_id END IGNORE NULLS)
               OVER same_hour AS first_eligible
    FROM candidates
    WINDOW same_hour AS (
        PARTITION BY station_key, sensor_id, parameter_raw, unit, observed_at, start, "end"
        ORDER BY provenance.record, observation_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    )
)
SELECT observation_id, provenance, station_key, station_context, sensor_id, parameter_raw,
       parameter, unit, value_raw, value, value_status, quality, observed_at, start, "end",
       available_at,
       CASE
           WHEN exclusion IS NOT NULL THEN exclusion
           WHEN NOT eligible THEN 'unusable_value'
           WHEN minimum <> maximum THEN 'conflict'
           WHEN observation_id = first_eligible THEN 'kept'
           ELSE 'duplicate'
       END AS decision,
       CASE WHEN exclusion IS NULL AND minimum = maximum THEN first_eligible END
           AS kept_observation_id
FROM slots
ORDER BY provenance.record, parameter_raw, observation_id
"""


def curate_senamhi(input_dir: Path, output: Path) -> None:
    """Publicar la auditoría Parquet sin sobrescribir archivos existentes."""
    if output.exists():
        raise FileExistsError(f"El archivo de salida ya existe: {output}")
    root = input_dir.resolve()
    manifest = verify_output(root)
    if manifest.source_id != "senamhi-lima-csv":
        raise ValueError("Se requiere una normalización de senamhi-lima-csv")
    files = [str(root / entry.path) for entry in manifest.files]
    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        TemporaryDirectory(dir=output.parent, prefix=".curate-") as tmp,
        duckdb.connect(config={"threads": 2}) as db,
    ):
        temporary = Path(tmp) / "audit.parquet"
        db.execute("SET TimeZone = 'UTC'")
        if files:
            db.read_parquet(files, hive_partitioning=False).create_view("normalized")
        else:
            db.register("normalized", pa.Table.from_batches([], schema=OBSERVATION_SCHEMA))
        db.execute(f"COPY ({AUDIT_QUERY}) TO ? (FORMAT PARQUET)", [str(temporary)])
        os.link(temporary, output)


@curation_app.command("senamhi")
def senamhi(
    input: Annotated[Path, typer.Option(help="Carpeta de normalización con manifiesto.")],
    output: Annotated[Path, typer.Option(help="Archivo Parquet nuevo para la auditoría.")],
) -> None:
    """Resolver repeticiones y conflictos a partir del Parquet SENAMHI verificado."""
    try:
        curate_senamhi(input, output)
    except (OSError, ValueError, duckdb.Error) as error:
        typer.echo(f"No se pudo depurar SENAMHI: {error}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Auditoría SENAMHI: {output}")
