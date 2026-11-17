"""Diagnóstico reproducible de los cuatro XLSX conocidos; no es el importador de producción."""

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from datetime import UTC, date, datetime, time
from pathlib import Path

import duckdb
import openpyxl
from review import clock_value, date_value, fold, iter_records, numeric_value, parameter_family

from airaware.comparison.metrics import count_windows, records

VERSION = "oefa-workbook-review-v1"
LIMA_TERMS = (
    "lima",
    "villa el salvador",
    "lurigancho",
    "carabayllo",
    "puente piedra",
    "san juan de miraflores",
    "san juan de lurigancho",
    "santa anita",
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encoded(value):
    if isinstance(value, (datetime, date, time)):
        return {"type": type(value).__name__, "value": value.isoformat()}
    return {"type": type(value).__name__, "value": str(value) if value is not None else None}


def text(value):
    return "" if value is None else str(value)


def converted(record, source):
    v = record["values"]
    formulas = record["formula_fields"]
    errors = record["error_fields"]
    raw = json.dumps({k: encoded(x) for k, x in v.items()}, ensure_ascii=False, sort_keys=True)
    d, ds = date_value(v.get("Fecha inicio"), record["epoch"])
    h, hs = clock_value(v.get("Hora inicio"))
    end_date, eds = date_value(v.get("Fecha fin"), record["epoch"])
    end_hour, ehs = clock_value(v.get("Hora fin"))
    start = datetime.combine(d, h) if d is not None and h is not None else None
    end = (
        datetime.combine(end_date, end_hour)
        if end_date is not None and end_hour is not None
        else None
    )
    dv = v.get("Fecha inicio")
    if isinstance(dv, datetime) and dv.time() != time(0) and dv.time() != h:
        start = None
        hs = "date_hour_conflict"
    if formulas or errors:
        start = None
        hs = "formula_or_excel_error_row"
    value_class, value = numeric_value(v.get("Valor"))
    if "Valor" in formulas:
        value_class, value = "formula", None
    if "Valor" in errors:
        value_class, value = "excel_error", None
    parameter = text(v.get("Parámetro"))
    unit = text(v.get("Unidad de medida"))
    period = text(v.get("Periodo"))
    identity = {
        k: encoded(v.get(k))
        for k in ("Nombre del punto", "Este", "Norte", "Altitud", "Zona", "Datum")
    }
    station_key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    context = {
        k: encoded(v.get(k))
        for k in (
            "Número de informe",
            "Nombre de la Evaluación",
            "Etapa",
            "Procedencia de la Muestra",
            "Procedencia Especifica de la Muestra",
            "Tipo de muestra",
            "Tipo de análisis",
            "Caracterización de la muestra",
            "Periodo",
            "Parámetro",
            "Unidad de medida",
        )
    }
    context_json = json.dumps(context, ensure_ascii=False, sort_keys=True)
    series_id = hashlib.sha256(
        (source["source_id"] + station_key + context_json).encode()
    ).hexdigest()
    location = fold(
        text(v.get("Descripción de ubicación")) + " " + text(v.get("Nombre de la Evaluación"))
    )
    mentions = [term for term in LIMA_TERMS if re.search(r"\b" + re.escape(term) + r"\b", location)]
    duration = (end - start).total_seconds() if start is not None and end is not None else None
    return dict(
        source_id=source["source_id"],
        input_sha256=source["sha256"],
        sheet=record["sheet"],
        row_number=record["row"],
        row_hash=hashlib.sha256(raw.encode()).hexdigest(),
        raw_values_json=raw,
        station_key=station_key,
        point=text(v.get("Nombre del punto")),
        report=text(v.get("Número de informe")),
        series_id=series_id,
        series_context=context_json,
        parameter=parameter,
        unit=unit,
        period=period,
        family=parameter_family(parameter),
        value_token=text(v.get("Valor")),
        value_class=value_class,
        value=value,
        start_date=str(d) if d is not None else None,
        date_status=ds,
        clock_status=hs,
        end_date_status=eds,
        end_clock_status=ehs,
        start=str(start) if start is not None else None,
        end=str(end) if end is not None else None,
        end_key=json.dumps(
            [encoded(v.get("Fecha fin")), encoded(v.get("Hora fin"))], sort_keys=True
        ),
        interval_seconds=duration,
        formula_cells=len(formulas),
        error_cells=len(errors),
        candidate_lima=bool(mentions),
        lima_text_evidence=json.dumps(mentions),
        candidate_callao=("callao" in location or "ventanilla" in location),
        hourly_label=fold(period).strip() == "1 hora",
    )


def export(c, query, path):
    c.execute(f"COPY ({query}) TO ? (FORMAT PARQUET,COMPRESSION ZSTD)", [str(path)])


def analyze(receipt, output):
    if output.exists():
        raise ValueError("Elegir una carpeta nueva; no sobrescribir informes")
    sources = json.loads(receipt.read_text())["files"]
    for s in sources:
        p = Path(s["local_path"])
        if any(
            parent.name == "raw" and output.resolve().is_relative_to(parent)
            for parent in p.resolve().parents
        ):
            raise ValueError("Salida dentro de raw")
        if digest(p) != s["sha256"]:
            raise ValueError("SHA de entrada distinto del recibo")
        with zipfile.ZipFile(p) as z:
            entries = z.infolist()
            if (
                len(entries) > 128
                or sum(e.file_size for e in entries) > 256 * 1024 * 1024
                or any(e.flag_bits & 1 or "vbaproject" in e.filename.lower() for e in entries)
            ):
                raise ValueError("El archivo excede el alcance de esta revisión")
            if z.testzip() is not None:
                raise ValueError("CRC inválido")
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = Path(tempfile.mkdtemp(prefix=".pending-review-", dir=output.parent))
    try:
        epochs = {}
        counts = {}
        with (pending / "rows.jsonl").open("w") as f:
            for s in sources:
                count = 0
                for row in iter_records(Path(s["local_path"])):
                    epochs[s["source_id"]] = str(row["epoch"])
                    f.write(json.dumps(converted(row, s), ensure_ascii=False) + "\n")
                    count += 1
                counts[s["source_id"]] = count
                print(s["source_id"], count, "filas leídas", flush=True)
        with duckdb.connect(
            str(pending / "work.duckdb"),
            config={
                "memory_limit": "768MB",
                "threads": 2,
                "autoinstall_known_extensions": False,
                "autoload_known_extensions": False,
                "temp_directory": str(pending / "spill"),
                "max_temp_directory_size": "2GB",
            },
        ) as c:
            c.execute(
                """CREATE TABLE obs AS SELECT * REPLACE(try_cast(start AS TIMESTAMP) AS start,
              try_cast("end" AS TIMESTAMP) AS "end",try_cast(start_date AS DATE) AS start_date)
              FROM read_json_auto(?,format='newline_delimited',sample_size=-1)""",
                [str(pending / "rows.jsonl")],
            )
            # JSON inference must not turn all-null numeric columns into text in published metrics.
            c.execute(
                "ALTER TABLE obs ALTER COLUMN value TYPE DOUBLE USING try_cast(value AS DOUBLE)"
            )
            c.execute("""CREATE TABLE identities AS SELECT DISTINCT series_id,source_id,station_key,
              point,report,parameter,unit,period,family,series_context,candidate_lima,candidate_callao
              FROM obs""")
            c.execute("""CREATE TABLE slots AS SELECT series_id,start,end_key,count(*) AS n,
              count(DISTINCT value) AS distinct_values,min(value) AS value,
              bool_and(value_class='finite') AS all_finite,
              bool_and(interval_seconds IS NULL OR interval_seconds=3600) AS interval_consistent
              FROM obs WHERE hourly_label AND start IS NOT NULL
              AND date_trunc('hour',start)=start GROUP BY series_id,start,end_key""")
            c.execute("""CREATE TABLE points AS SELECT series_id,start AS ts,min(value) AS value
              FROM slots GROUP BY series_id,start HAVING count(*)=1
              AND bool_and(distinct_values=1 AND all_finite AND interval_consistent)""")
            dataset = records(
                c,
                """SELECT source_id,
              count(*)
              AS rows,
              count(DISTINCT row_hash)
              AS distinct_decoded_rows,
              count(*)-count(DISTINCT row_hash) AS decoded_duplicate_extra_rows,
              count(DISTINCT station_key)
              AS provisional_point_groups,
              count(DISTINCT point)
              AS point_names,
              count(DISTINCT report) AS reports,count(DISTINCT parameter) AS parameter_labels,
              min(start_date) AS first_date,max(start_date) AS last_date,
              count(*) FILTER(WHERE start_date IS NULL) AS unresolved_date_rows,
              count(start)
              AS parsed_start_rows,
              count(*) FILTER(WHERE start IS NULL)
              AS unresolved_start_rows,
              count(*) FILTER(WHERE value_class='finite') AS finite_values,
              count(*) FILTER(WHERE value_class='censored') AS censored_values,
              count(*) FILTER(WHERE value_class='missing') AS missing_values,
              count(*) FILTER(WHERE value_class NOT IN ('finite','censored','missing'))
              AS other_value_rows,
              count(*) FILTER(WHERE value<0)
              AS negative_values,
              count(*) FILTER(WHERE value=0)
              AS zero_values,
              count(*) FILTER(WHERE hourly_label) AS hourly_label_rows,
              count(*) FILTER(WHERE candidate_lima) AS text_lima_candidate_rows,
              count(*) FILTER(WHERE candidate_callao) AS text_callao_candidate_rows,
              count(*) FILTER(WHERE interval_seconds<0) AS negative_intervals,
              count(*) FILTER(WHERE hourly_label AND interval_seconds!=3600)
              AS hourly_duration_mismatch,
              sum(formula_cells) AS formula_cells,sum(error_cells) AS excel_error_cells
              FROM obs GROUP BY source_id ORDER BY source_id""",
            )
            params = records(
                c,
                """SELECT source_id,parameter,unit,period,family,count(*) AS rows,
              count(value)
              AS finite_values,
              count(*) FILTER(WHERE value_class='censored')
              AS censored_values,
              min(value)
              AS minimum,max(value)
              AS maximum,
              min(start_date)
              AS first_date,max(start_date)
              AS last_date
              FROM obs GROUP BY ALL ORDER BY source_id,rows DESC""",
            )
            tokens = records(
                c,
                """SELECT source_id,value_class,value_token,count(*) AS n FROM obs
              WHERE value_class!='finite' GROUP BY ALL ORDER BY source_id,n DESC""",
            )
            times = records(
                c,
                """SELECT source_id,date_status,clock_status,count(*) AS n
              FROM obs GROUP BY ALL ORDER BY source_id,n DESC""",
            )
            coverage = records(
                c,
                """WITH ordered AS (SELECT *,ts-row_number() OVER(PARTITION BY series_id
              ORDER BY ts)*INTERVAL '1 hour' AS run FROM points),runs AS (SELECT series_id,run,
              count(*)
              AS n
              FROM ordered GROUP BY series_id,run), totals AS (SELECT series_id,
              count(*)
              AS distinct_hour_slots,
              min(ts) AS first_clock,max(ts) AS last_clock FROM points GROUP BY series_id)
              SELECT i.*,coalesce(t.distinct_hour_slots,0)
              AS distinct_hour_slots,
              t.first_clock,
              t.last_clock,
              (SELECT max(n) FROM runs r WHERE r.series_id=i.series_id) AS longest_run_hours,
              (SELECT sum(n-1) FROM slots s WHERE s.series_id=i.series_id)
              AS duplicate_extra_clock_rows,
              (SELECT count(*) FROM slots s WHERE s.series_id=i.series_id AND distinct_values>1)
              AS conflict_slots
              FROM identities i LEFT JOIN totals t USING(series_id) ORDER BY source_id,series_id""",
            )
            windows = []
            lookup = {r["series_id"]: r for r in coverage}
            for h in (24, 48, 72, 168):
                for f in (6, 12, 24, 48):
                    for r in count_windows(c, h, f):
                        meta = lookup[r["series_id"]]
                        if meta["family"] not in ("pm10", "pm25"):
                            continue
                        assert (
                            r["candidates"]
                            == r["history_missing"] + r["future_missing"] + r["complete"]
                        )
                        windows.append(
                            {
                                **{
                                    k: meta[k]
                                    for k in (
                                        "source_id",
                                        "point",
                                        "family",
                                        "parameter",
                                        "unit",
                                        "period",
                                        "candidate_lima",
                                        "candidate_callao",
                                        "series_id",
                                    )
                                },
                                **r,
                                "history_hours": h,
                                "horizon_hours": f,
                                "scientific_valid_windows": None,
                            }
                        )
            for d in dataset:
                assert d["rows"] == counts[d["source_id"]]
                assert d["rows"] == sum(
                    d[k]
                    for k in (
                        "finite_values",
                        "censored_values",
                        "missing_values",
                        "other_value_rows",
                    )
                )
            export(c, "SELECT * FROM obs", pending / "observations.parquet")
            export(
                c,
                "SELECT source_id,value_class,value_token,count(*) AS n FROM obs GROUP BY ALL",
                pending / "tokens.parquet",
            )
        summary = dict(
            algorithm=VERSION,
            created_at_utc=datetime.now(UTC).isoformat(),
            openpyxl_version=openpyxl.__version__,
            duckdb_version=duckdb.__version__,
            workbook_epochs=epochs,
            sources=dataset,
            parameters=params,
            value_tokens=tokens,
            time_statuses=times,
            coverage=coverage,
            windows=windows,
            scientific_selection="not_established",
        )
        (pending / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        for name in ("rows.jsonl", "work.duckdb", "work.duckdb.wal"):
            (pending / name).unlink(missing_ok=True)
        if (pending / "spill").exists():
            shutil.rmtree(pending / "spill")
        if any(digest(Path(s["local_path"])) != s["sha256"] for s in sources):
            raise ValueError("Un original cambió durante el análisis")
        manifest = dict(
            algorithm=VERSION,
            inputs_unchanged=True,
            sources=sources,
            files={
                p.name: {"sha256": digest(p), "size_bytes": p.stat().st_size}
                for p in pending.iterdir()
                if p.is_file()
            },
        )
        (pending / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        )
        pending.rename(output)
        print(output, flush=True)
    finally:
        if pending.exists():
            shutil.rmtree(pending)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--receipt", type=Path, default=Path("metadata/oefa-air-workbooks-download.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.receipt, args.output)
