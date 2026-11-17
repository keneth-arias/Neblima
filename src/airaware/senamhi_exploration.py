"""Exploración SENAMHI sin imputación; reloj local solo como escenario hipotético."""

import argparse
import json
import shutil
import tempfile
import unicodedata
from pathlib import Path

import duckdb

from airaware.comparison.inputs import digest, load_source, prepare_points
from airaware.comparison.metrics import records
from airaware.profiling.engine import ProfileSpec

VERSION = "senamhi-exploration-v1"


def normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(
        "".join(c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c))
        .upper()
        .replace("_", " ")
        .split()
    )


def build_view(c: duckdb.DuckDBPyConnection, signal: str, offset: int) -> dict:
    """Grilla diaria completa dentro del intervalo observado de cada identidad provisional."""
    if signal not in ("PM10", "PM2_5", "NO2") or offset not in (0, -5):
        raise ValueError("Señal o escenario de reloj no admitido")
    losses = prepare_points(c, signal, "lima")
    c.execute(f"""CREATE OR REPLACE TABLE bounds AS SELECT series_id,
        min(station_label) station_label,min(DISTRITO) district_raw,
        date_trunc('day',min(ts)+INTERVAL '{offset} hours') a,
        date_trunc('day',max(ts)+INTERVAL '{offset} hours')+INTERVAL '23 hours' b
        FROM base WHERE geography='lima' AND ts IS NOT NULL
        AND date_trunc('hour',ts)=ts GROUP BY series_id""")
    c.execute("""CREATE OR REPLACE TABLE grid AS SELECT b.*,t.clock_ts FROM bounds b,
        LATERAL generate_series(b.a,b.b,INTERVAL '1 hour') t(clock_ts)""")
    c.execute(f"""CREATE OR REPLACE TABLE hourly AS SELECT g.series_id,g.station_label,
        g.district_raw,g.clock_ts,p.value,p.value IS NOT NULL AS observed,
        p.ts source_clock_ts FROM grid g LEFT JOIN points p ON g.series_id=p.series_id
        AND g.clock_ts=p.ts+INTERVAL '{offset} hours' """)
    c.execute("""CREATE OR REPLACE TABLE daily AS SELECT series_id,station_label,district_raw,
        cast(clock_ts AS DATE) AS day,count(*) expected_hours,count(value) valid_hours,
        CASE WHEN count(value)>=18 THEN avg(value) END daily_mean,
        avg(value) mean_without_completeness_filter FROM hourly GROUP BY ALL""")
    c.execute("""CREATE OR REPLACE TABLE annual AS SELECT series_id,station_label,district_raw,
        year(clock_ts) AS year,count(*) expected_hours,count(value) valid_hours,
        count(value)*1.0/count(*) coverage,avg(value) mean,min(clock_ts) period_start,
        max(clock_ts) period_end FROM hourly GROUP BY ALL""")
    c.execute("""CREATE OR REPLACE TABLE monthly AS SELECT series_id,station_label,district_raw,
        date_trunc('month',clock_ts) AS month,count(*) expected_hours,count(value) valid_hours,
        avg(value) mean FROM hourly GROUP BY ALL""")
    c.execute("""CREATE OR REPLACE TABLE cycle AS SELECT series_id,station_label,
        hour(clock_ts) AS hour,count(*) expected_hours,count(value) valid_hours,
        avg(value) mean FROM hourly GROUP BY ALL""")
    totals = records(c, """SELECT count(*) expected_hours,count(value) valid_hours FROM hourly""")[
        0
    ]
    totals["daily_eligible"] = records(c, "SELECT count(daily_mean) n FROM daily")[0]["n"]
    assert totals["valid_hours"] == losses["unique_points"]
    return dict(
        signal=signal,
        clock_view="raw" if offset == 0 else "raw_minus5_hypothesis",
        offset_hours=offset,
        losses=losses,
        **totals,
    )


def explore(spec: ProfileSpec, output: Path) -> None:
    if spec.kind != "senamhi" or tuple(spec.signals) != ("PM10", "PM2_5", "NO2"):
        raise ValueError("Se requiere contrato SENAMHI con sus tres señales")
    if output.exists() or output.resolve().is_relative_to(spec.raw_root.resolve()):
        raise ValueError("Elegir salida nueva fuera de raw")
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = Path(tempfile.mkdtemp(prefix=".pending-senamhi-", dir=output.parent))
    try:
        with duckdb.connect(
            config={
                "threads": 1,
                "memory_limit": "768MB",
                "autoinstall_known_extensions": False,
                "autoload_known_extensions": False,
            }
        ) as c:
            original = load_source(c, spec)
            rows = records(c, "SELECT count(*) n FROM base")[0]["n"]
            c.execute(
                "COPY base TO ? (FORMAT PARQUET,COMPRESSION ZSTD)",
                [str(pending / "source-rows.parquet")],
            )
            # Esta tabla reproduce promedios crudos por distrito, no inferencia temporal o espacial.
            districts = records(
                c,
                """SELECT DISTRITO district_raw,count(*) source_rows,
                avg(try_cast(PM10 AS DOUBLE)) pm10,
                avg(try_cast(PM2_5 AS DOUBLE)) pm25,avg(try_cast(NO2 AS DOUBLE)) no2
                FROM base GROUP BY DISTRITO ORDER BY DISTRITO""",
            )
            for d in districts:
                d["district_normalized"] = normalize_name(d["district_raw"])
            results = []
            annual = []
            for offset in (0, -5):
                for signal in spec.signals:
                    result = build_view(c, signal, offset)
                    prefix = f"{signal}-{offset}"
                    for table in ("hourly", "daily", "annual", "monthly", "cycle"):
                        c.execute(
                            f"COPY {table} TO ? (FORMAT PARQUET,COMPRESSION ZSTD)",
                            [str(pending / f"{prefix}-{table}.parquet")],
                        )
                    annual.extend(
                        dict(signal=signal, offset_hours=offset, **r)
                        for r in records(c, "SELECT * FROM annual ORDER BY station_label,year")
                    )
                    results.append(result)
            summary = dict(
                algorithm=VERSION,
                source_id=spec.source_id,
                input_sha256=spec.sha256,
                rows=rows,
                scientific_eligible=False,
                timezone_confirmed=False,
                daily_min_hours=18,
                denominator="full_days_between_station_first_last_raw_timestamp",
                scenarios=results,
                annual=annual,
                raw_district_means=districts,
            )
        if digest(original) != spec.sha256:
            raise ValueError("El original cambió durante la ejecución")
        (pending / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        manifest = dict(
            algorithm=VERSION,
            input_sha256=spec.sha256,
            inputs_unchanged=True,
            files={p.name: digest(p) for p in pending.iterdir() if p.is_file()},
        )
        (pending / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        pending.rename(output)
    finally:
        if pending.exists():
            shutil.rmtree(pending)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/profiling.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    sources = [ProfileSpec.model_validate(s) for s in config["datasets"] if s["kind"] == "senamhi"]
    if len(sources) != 1:
        raise ValueError("El plan debe identificar exactamente un original SENAMHI")
    explore(sources[0], args.output)
