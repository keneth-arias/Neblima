"""Diagnóstico local EAS largo; los seriales Excel son una hipótesis, no instantes acreditados."""

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import duckdb

from airaware.comparison.metrics import count_windows, records

CONTEXT = (
    "Número.de.informe",
    "Nombre.de.la.Evaluación",
    "Etapa",
    "Procedencia.de.la.Muestra",
    "Procedencia.Especifica.de.la.Muestra",
    "Nombre.del.punto",
    "Este",
    "Norte",
    "Altitud",
    "Zona",
    "Datum",
    "Tipo.de.muestra",
    "Tipo.de.análisis",
    "Periodo",
    "Parámetro",
    "Unidad.de.medida",
)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def review(path: Path, output: Path) -> None:
    if output.exists() or output.resolve().is_relative_to(path.resolve().parent):
        raise ValueError("Elegir una carpeta nueva fuera de la carpeta del original")
    before = digest(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = Path(tempfile.mkdtemp(prefix=".pending-eas-", dir=output.parent))
    try:
        with duckdb.connect(
            str(pending / "work.duckdb"),
            config={
                "threads": 1,
                "memory_limit": "1GB",
                "max_temp_directory_size": "16GB",
                "temp_directory": str(pending / "spill"),
                "autoinstall_known_extensions": False,
                "autoload_known_extensions": False,
            },
        ) as c:
            c.execute(
                """CREATE TABLE raw AS SELECT row_number() OVER()+1 AS source_record,*
                FROM read_csv(?,header=true,all_varchar=true,delim=',',strict_mode=true,
                nullstr='',max_line_size=1048576)""",
                [str(path)],
            )
            context = ",".join('"' + col + '"' for col in CONTEXT)
            c.execute(f"""CREATE TABLE parsed AS SELECT *,
                sha256(to_json(list_value({context}))) AS series_id,
                try_cast("Fecha.inicio" AS INTEGER) AS serial,
                try_strptime("Hora.inicio",'%H:%M:%S') AS clock,
                try_cast("Valor" AS DOUBLE) AS number,
                CASE WHEN "Valor" IS NULL OR upper(trim("Valor")) IN ('','-','NA','N/A','NULL')
                  THEN 'missing' WHEN regexp_matches(trim("Valor"),'^[<>≤≥]') THEN 'censored'
                  WHEN try_cast("Valor" AS DOUBLE) IS NULL THEN 'unresolved'
                  WHEN NOT isfinite(try_cast("Valor" AS DOUBLE)) THEN 'nonfinite'
                  ELSE 'finite' END AS value_status,
                CASE WHEN contains(lower("Parámetro"),'25 micras') THEN 'ambiguous_pm'
                  WHEN lower("Parámetro") IN ('material particulado pm2,5',
                    'material particulado con diámetro menor a 2,5 micras (pm2,5)') THEN 'pm25'
                  WHEN lower("Parámetro") IN ('pm10',
                    'material particulado con diámetro menor a 10 micras (pm10)') THEN 'pm10'
                  ELSE 'other' END AS family,
                regexp_matches(lower(coalesce("Descripción.de.ubicación",'') || ' ' ||
                  coalesce("Nombre.de.la.Evaluación",'')), '\\blima\\b') AS candidate_lima
                FROM raw""")
            c.execute("""CREATE TABLE base AS SELECT *,CASE WHEN serial BETWEEN 25000 AND 60000
                AND regexp_full_match("Fecha.inicio",'[0-9]{5}') AND clock IS NOT NULL
                THEN TIMESTAMP '1899-12-30' + serial*INTERVAL '1 day'
                  + date_part('hour',clock)*INTERVAL '1 hour'
                  + date_part('minute',clock)*INTERVAL '1 minute'
                  + date_part('second',clock)*INTERVAL '1 second' END AS ts FROM parsed""")
            c.execute("""CREATE TABLE slots AS SELECT series_id,ts,count(*) AS n,
                count(DISTINCT number) AS distinct_values,min(number) AS value,
                bool_and(value_status='finite') AS all_finite,
                bool_and(coalesce("Fecha.fin",'-') IN ('-','') AND
                  coalesce("Hora.fin",'-') IN ('-','')) AS end_unspecified
                FROM base WHERE family IN ('pm25','pm10') AND "Periodo"='1 hora'
                AND "Unidad.de.medida" IN ('µg/m³','ug/m3','µg/m3')
                AND ts IS NOT NULL AND date_trunc('hour',ts)=ts GROUP BY series_id,ts""")
            # Solo intervalos sin fin declarado; los demás requieren verificación explícita.
            c.execute("""CREATE TABLE points AS SELECT series_id,ts,value FROM slots
                WHERE all_finite AND distinct_values=1 AND end_unspecified""")
            c.execute("""CREATE TABLE identities AS SELECT DISTINCT series_id,
                "Nombre.del.punto" AS point,"Número.de.informe" AS report,
                "Parámetro" AS parameter,"Unidad.de.medida" AS unit,family,candidate_lima
                FROM base""")
            identities = {r["series_id"]: r for r in records(c, "SELECT * FROM identities")}
            windows = []
            for h in (24, 48, 72, 168):
                for f in (6, 12, 24, 48):
                    for row in count_windows(c, h, f):
                        assert row["candidates"] == sum(
                            row[k] for k in ("history_missing", "future_missing", "complete")
                        )
                        windows.append(
                            identities[row["series_id"]]
                            | row
                            | {"history_hours": h, "horizon_hours": f}
                        )
            counts = {
                r["value_status"]: r["n"]
                for r in records(
                    c, "SELECT value_status,count(*) n FROM base GROUP BY value_status"
                )
            }
            total = c.execute("SELECT count(*) FROM base").fetchone()
            assert total is not None and total[0] == sum(counts.values())
            coverage = records(
                c,
                """WITH ordered AS (SELECT *,ts-row_number() OVER(
                PARTITION BY series_id ORDER BY ts)*INTERVAL '1 hour' run FROM points),
                runs AS (SELECT series_id,run,count(*) n FROM ordered GROUP BY ALL)
                SELECT i.*,max(n) longest_run_hours,sum(n) distinct_hour_slots
                FROM runs JOIN identities i USING(series_id) GROUP BY ALL""",
            )
            for table in ("points", "identities"):
                c.execute(
                    f"COPY {table} TO ? (FORMAT PARQUET)", [str(pending / f"{table}.parquet")]
                )
            c.execute(
                """COPY (SELECT source_record,series_id,ts,value_status,family
                FROM base WHERE family!='other') TO ? (FORMAT PARQUET)""",
                [str(pending / "row-diagnostics.parquet")],
            )
            summary = dict(
                algorithm="eas-long-diagnostic-v1",
                rows=total[0],
                sha256=before,
                date_hypothesis="excel-1900-unconfirmed",
                timezone=None,
                scientific_valid_windows=None,
                value_counts=counts,
                conflict_slots=records(
                    c, "SELECT count(*) AS n FROM slots WHERE distinct_values>1"
                )[0]["n"],
                windows=windows,
                coverage=coverage,
                vocabulary=records(
                    c,
                    """SELECT "Parámetro" parameter,"Unidad.de.medida" unit,
                    "Periodo" period,family,count(*) n FROM base GROUP BY ALL""",
                ),
                temporal_counts=records(
                    c,
                    """SELECT (ts IS NOT NULL) parsed_hypothesis,
                    count(*) n FROM base GROUP BY ALL""",
                ),
                excluded_end_policy="only_missing_end_in_diagnostic_points",
            )
        if before != digest(path):
            raise ValueError("El original cambió durante la revisión")
        summary["inputs_unchanged"] = True
        (pending / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        (pending / "work.duckdb").unlink()
        shutil.rmtree(pending / "spill", ignore_errors=True)
        manifest = {
            "input": str(path),
            "sha256": before,
            "files": {p.name: digest(p) for p in pending.iterdir() if p.is_file()},
        }
        (pending / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        pending.rename(output)
    finally:
        if pending.exists():
            shutil.rmtree(pending)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review(args.input, args.output)
