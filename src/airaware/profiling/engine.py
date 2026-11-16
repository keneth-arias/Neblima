"""Informes Parquet por fuente y serie comparable, sobre archivos de adquisición verificados."""

import csv
import hashlib
import json
import os
import shutil
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

import duckdb
from pydantic import BaseModel, ConfigDict, Field

from airaware.acquisition.models import Manifest
from airaware.acquisition.store import _chunks, verify_bundle

VERSION = "raw-profile-v2"


class ProfileSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    kind: Literal["senamhi", "oefa"]
    manifest: Path
    raw_root: Path = Path("data/raw")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    columns: tuple[str, ...] = Field(min_length=1, max_length=128)
    signals: tuple[str, ...] = Field(min_length=1, max_length=32)
    expected_rows: int | None = Field(default=None, strict=True, gt=0)


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _json_fields(names: list[str]) -> str:
    return "to_json(list_value(" + ",".join(_q(name) for name in names) + "))"


def _layout(kind: str) -> tuple[list[str], list[str], str, str, str]:
    if kind == "senamhi":
        station = [
            "ESTACION",
            "LONGITUD",
            "LATITUD",
            "ALTITUD",
            "DEPARTAMENTO",
            "PROVINCIA",
            "DISTRITO",
        ]
        clock = "lpad(HORA,6,'0')"
        start = f"""CASE WHEN regexp_full_match(FECHA,'[0-9]{{8}}')
            AND regexp_full_match(HORA,'[0-9]{{1,6}}')
            AND regexp_full_match({clock},'([01][0-9]|2[0-3])[0-5][0-9][0-5][0-9]')
            THEN try_strptime(FECHA||{clock},'%Y%m%d%H%M%S') END"""
        return station, [], start, "NULL::TIMESTAMP", "true"
    station = [
        "NOMBRE_PUNTO",
        "ESTE",
        "NORTE",
        "ALTITUD",
        "ZONA",
        "DATUM",
        "DEPARTAMENTO",
        "PROVINCIA",
        "DISTRITO",
    ]
    context = [
        "NOMBRE_EVALUACION",
        "PERIODO",
        "UNIDAD_MEDIDA",
        "TIPO_ANALISIS",
        "TIPO_MUESTRA",
        "PROCEDENCIA_MUESTRA",
    ]

    def clock(date: str, hour: str) -> str:
        return f"""CASE
            WHEN regexp_full_match({_q(date)},'[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}')
            AND regexp_full_match({_q(hour)},
                '(1899-12-(30|31) )?([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]')
            THEN try_strptime({_q(date)}||' '||right({_q(hour)},8),
                '%Y-%m-%d %H:%M:%S') END"""

    return (
        station,
        context,
        clock("FECHA_INICIO", "HORA_INICIO"),
        clock("FECHA_FIN", "HORA_FIN"),
        "PERIODO='1 hora'",
    )


def _export(c: duckdb.DuckDBPyConnection, query: str, path: Path, spec: ProfileSpec) -> None:
    provenance = (
        f"SELECT {_literal(spec.source_id)} source_id,{_literal(spec.sha256)} input_sha256,"
        f"{_literal(VERSION)} algorithm,* FROM ({query})"
    )
    c.execute(f"COPY ({provenance}) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(path)])


def _signal(c: duckdb.DuckDBPyConnection, name: str, ordinal: int) -> None:
    column = _q(name)
    c.execute(f"""CREATE OR REPLACE TEMP TABLE cells AS
        SELECT series_id, station_key, station_label, series_context, ts, end_ts, hourly,
        start_status,
        {column} AS raw_token, trim({column}) AS token,
        try_cast(trim({column}) AS DOUBLE) AS number,
        CASE WHEN token='' THEN 'empty'
             WHEN upper(token) IN ('-','NA','N/A','ND','NAN','NULL') THEN 'marker'
             WHEN number IS NULL THEN 'invalid_numeric'
             WHEN NOT isfinite(number) THEN 'nonfinite' ELSE 'finite' END AS class,
        CASE WHEN class='finite' THEN number END AS value FROM base""")
    c.execute("""CREATE OR REPLACE TEMP TABLE stats AS SELECT series_id,
        min(station_key) station_key, min(station_label) station_label,
          min(series_context) series_context,
        count(*) AS "rows", count(value) finite_count,
        count(*) FILTER(WHERE class='empty') empty_count,
        count(*) FILTER(WHERE class='marker') marker_count,
        count(*) FILTER(WHERE class='invalid_numeric') invalid_numeric_count,
        count(*) FILTER(WHERE class='nonfinite') nonfinite_count,
        count(*) FILTER(WHERE value<0) negative_count, count(*) FILTER(WHERE value=0) zero_count,
        min(value) minimum, max(value) maximum, quantile_cont(value,0.25) q25,
        quantile_cont(value,0.5) median, quantile_cont(value,0.75) q75,
        count(*) FILTER(WHERE ts IS NULL) unparsed_start_rows,
        count(value) FILTER(WHERE ts IS NOT NULL) parsed_finite_count,
        count(*) FILTER(WHERE start_status='clock_missing') clock_missing_rows,
        count(*) FILTER(WHERE start_status='clock_unsupported') clock_unsupported_rows,
        count(*) FILTER(WHERE ts IS NOT NULL AND date_trunc('hour',ts)!=ts) off_grid_start_rows,
        bool_or(hourly) hourly_candidate FROM cells GROUP BY series_id""")
    c.execute("""CREATE OR REPLACE TEMP TABLE slots AS SELECT series_id,ts,end_ts,count(*) n,
        count(DISTINCT value) distinct_values, min(value) AS value, bool_and(hourly) hourly
        FROM cells WHERE ts IS NOT NULL GROUP BY series_id,ts,end_ts""")
    c.execute("""CREATE OR REPLACE TEMP TABLE points AS SELECT series_id,ts,min(value) AS value
        FROM slots GROUP BY series_id,ts HAVING count(*)=1
        AND bool_and(hourly AND distinct_values=1 AND date_trunc('hour',ts)=ts)""")
    c.execute("""CREATE OR REPLACE TEMP TABLE ordered AS SELECT *,
        lag(ts) OVER w prev_ts, lag(value) OVER w prev_value
        FROM points WINDOW w AS (PARTITION BY series_id ORDER BY ts)""")
    c.execute(f"""CREATE OR REPLACE TABLE signal_{ordinal} AS WITH
        duplicates AS (SELECT series_id,sum(n-1)::BIGINT duplicate_extra_rows,
          count(*) FILTER(WHERE distinct_values>1) conflict_slots FROM slots GROUP BY series_id),
        spans AS (SELECT series_id,count(*) observed_hour_slots,min(ts) first_finite_clock,
          max(ts) last_finite_clock,date_diff('hour',min(ts),max(ts))+1 expected_hour_slots,
          coalesce(max(greatest(date_diff('hour',prev_ts,ts)-1,0)),0) longest_gap_hours
          FROM ordered GROUP BY series_id),
        breaks AS (SELECT *,sum(CASE WHEN prev_value=value AND date_diff('hour',prev_ts,ts)=1
          THEN 0 ELSE 1 END) OVER(PARTITION BY series_id ORDER BY ts) run FROM ordered),
        runs AS (SELECT series_id,max(n) longest_constant_run_hours FROM
          (SELECT series_id,run,count(*) n FROM breaks GROUP BY series_id,run) GROUP BY series_id),
        extremes AS (SELECT c.series_id,count(*) FILTER(WHERE c.value<s.q25-3*(s.q75-s.q25)
          OR c.value>s.q75+3*(s.q75-s.q25)) extreme_count FROM cells c JOIN stats s USING(series_id)
          GROUP BY c.series_id)
        SELECT s.*, {_literal(name)} signal, 'unverified_source_clock' clock_status,
        coalesce(d.duplicate_extra_rows,0) duplicate_extra_rows,coalesce(d.conflict_slots,
          0) conflict_slots,
        p.observed_hour_slots,p.first_finite_clock,p.last_finite_clock,p.expected_hour_slots,
        p.expected_hour_slots-p.observed_hour_slots missing_hour_slots,p.longest_gap_hours,
        r.longest_constant_run_hours,
        CASE WHEN s.finite_count>0 THEN s.minimum=s.maximum END is_constant,
        e.extreme_count FROM stats s LEFT JOIN duplicates d USING(series_id)
        LEFT JOIN spans p USING(series_id) LEFT JOIN runs r USING(series_id)
        LEFT JOIN extremes e USING(series_id)""")
    c.execute(f"""CREATE OR REPLACE TABLE tokens_{ordinal} AS SELECT 'signal' dimension,series_id,
        {_literal(name)} signal,class,raw_token token,count(*) count FROM cells
        WHERE class NOT IN ('finite','empty') GROUP BY series_id,class,raw_token""")


def profile(
    spec: ProfileSpec, output_root: Path, *, progress: Callable[[str], None] | None = None
) -> Path:
    """Verificar el original y publicar diagnósticos locales sin red de forma atómica."""
    started = time.monotonic()
    manifest_path = spec.manifest.resolve()
    raw_root = spec.raw_root.resolve()
    with manifest_path.open("rb") as stream:
        content = stream.read(65537)
    if len(content) > 65536:
        raise ValueError("El manifiesto supera 64 KiB")
    manifest = Manifest.model_validate_json(content)
    if manifest.spec.source_id != spec.source_id or manifest.sha256 != spec.sha256:
        raise ValueError("El contrato de perfilamiento no coincide con la adquisición")
    if manifest.spec.format != "csv":
        raise ValueError("El perfil requiere un original CSV")
    if progress:
        progress(f"{spec.source_id}: verificando adquisición")
    result = verify_bundle(manifest.spec, raw_root, manifest_path.parent)
    original = result.artifact
    before = original.stat()
    with original.open(encoding="utf-8-sig", newline="") as f:
        columns = next(csv.reader(f, delimiter=manifest.spec.csv_delimiter, strict=True))
    if columns != list(spec.columns) or len(set(columns)) != len(columns):
        raise ValueError("Las columnas no coinciden con el contrato")
    station, context, start, end, hourly = _layout(spec.kind)
    required = set(station + context + list(spec.signals))
    required.update(
        ["FECHA", "HORA"]
        if spec.kind == "senamhi"
        else ["FECHA_INICIO", "HORA_INICIO", "FECHA_FIN", "HORA_FIN"]
    )
    if not required <= set(columns) or len(set(spec.signals)) != len(spec.signals):
        raise ValueError("Faltan campos requeridos o hay señales repetidas")
    output_root = output_root.resolve()
    if output_root.is_relative_to(raw_root):
        raise ValueError("Los informes no pueden escribirse sobre raw")
    output_root.mkdir(parents=True, exist_ok=True)
    pending = Path(tempfile.mkdtemp(prefix=".pending-", dir=output_root))
    work = pending / ".work"
    work.mkdir()
    c = None
    try:
        c = duckdb.connect(
            str(work / "profile.duckdb"),
            config={
                "memory_limit": "768MB",
                "threads": 2,
                "temp_directory": str(work / "spill"),
                "max_temp_directory_size": "10GB",
                "autoinstall_known_extensions": False,
                "autoload_known_extensions": False,
            },
        )
        c.execute(
            """CREATE TABLE input AS SELECT * FROM read_csv(?,columns=?,header=true,delim=?,
          auto_detect=false,force_not_null=?,strict_mode=true,ignore_errors=false)""",
            [str(original), {n: "VARCHAR" for n in columns}, manifest.spec.csv_delimiter, columns],
        )
        station_json = _json_fields(station)
        context_json = _json_fields(context) if context else "'[]'"
        date_column = "FECHA" if spec.kind == "senamhi" else "FECHA_INICIO"
        clock_column = "HORA" if spec.kind == "senamhi" else "HORA_INICIO"
        date_format = "%Y%m%d" if spec.kind == "senamhi" else "%Y-%m-%d"
        date_pattern = "[0-9]{8}" if spec.kind == "senamhi" else "[0-9]{4}-[0-9]{2}-[0-9]{2}"
        parsed_date = (
            f"CASE WHEN regexp_full_match({_q(date_column)},'{date_pattern}') "
            f"THEN try_strptime({_q(date_column)},'{date_format}')::DATE END"
        )
        c.execute(f"""CREATE TABLE base AS SELECT *,sha256({_json_fields(columns)}) row_hash,
          {station_json} station_context,
          sha256({_literal(spec.source_id)}||station_context) station_key,
          {_q(station[0])} station_label,{context_json} series_context,
          sha256(station_key||series_context) series_id,{start} ts,{end} end_ts,
          {hourly} hourly,{parsed_date} parsed_date,{_q(date_column)} source_date_text,
          {_q(clock_column)} source_clock_text,
          CASE WHEN parsed_date IS NULL THEN 'date_unparsed'
            WHEN upper(trim(source_clock_text)) IN ('','NA','N/A','-','ND','NULL','NAN')
              THEN 'clock_missing'
            WHEN ts IS NULL THEN 'clock_unsupported' ELSE 'parsed' END start_status FROM input""")
        c.execute("DROP TABLE input")
        count = c.execute("SELECT count(*) FROM base").fetchone()
        if count is None or (spec.expected_rows is not None and count[0] != spec.expected_rows):
            raise ValueError("El conteo difiere de la adquisición")
        _export(
            c,
            f"""SELECT {len(columns)} column_count,count(*) AS "rows",
          count(*)-count(DISTINCT row_hash) exact_duplicate_rows,
          count(DISTINCT station_key) provisional_station_count,
          count(DISTINCT station_label) raw_station_name_count,
          count(*) FILTER(WHERE ts IS NULL) unparsed_start_rows,min(ts) first_parsed_clock,
          max(ts) last_parsed_clock,min(parsed_date) first_date,max(parsed_date) last_date,
          count(*) FILTER(WHERE start_status='date_unparsed') unparsed_date_rows,
          count(*) FILTER(WHERE start_status='clock_missing') clock_missing_rows,
          count(*) FILTER(WHERE start_status='clock_unsupported') clock_unsupported_rows,
          count(*) FILTER(WHERE ts IS NOT NULL AND date_trunc('hour',ts)!=ts) off_grid_start_rows,
          'unverified_source_clock' clock_status FROM base""",
            pending / "datasets.parquet",
            spec,
        )
        _export(
            c,
            """SELECT station_key,min(station_label) station_label,
          min(station_context) station_context,
          count(*) AS "rows",count(DISTINCT series_id) series_count,min(ts) first_parsed_clock,
          max(ts) last_parsed_clock,min(parsed_date) first_date,max(parsed_date) last_date,
          count(*) FILTER(WHERE ts IS NULL) unparsed_start_rows
          FROM base GROUP BY station_key ORDER BY station_key""",
            pending / "stations.parquet",
            spec,
        )
        for ordinal, signal in enumerate(spec.signals):
            if progress:
                progress(f"{spec.source_id}: señal {ordinal + 1}/{len(spec.signals)}")
            _signal(c, signal, ordinal)
        union = " UNION ALL ".join(f"SELECT * FROM signal_{i}" for i in range(len(spec.signals)))
        _export(c, union + " ORDER BY series_id,signal", pending / "signals.parquet", spec)
        tokens = " UNION ALL ".join(f"SELECT * FROM tokens_{i}" for i in range(len(spec.signals)))
        temporal = (
            f"SELECT 'start_clock' dimension,series_id,{_literal(clock_column)} signal,"
            "start_status AS class,source_clock_text token,count(*) count FROM base "
            "WHERE start_status!='parsed' GROUP BY series_id,start_status,source_clock_text "
            f"UNION ALL SELECT 'start_date',series_id,{_literal(date_column)},"
            "'date_unparsed',source_date_text,count(*) FROM base WHERE parsed_date IS NULL "
            "GROUP BY series_id,source_date_text"
        )
        _export(
            c,
            tokens + " UNION ALL " + temporal + " ORDER BY dimension,series_id,signal,class,token",
            pending / "tokens.parquet",
            spec,
        )
        after = original.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ino,
        ):
            raise ValueError("El original cambió durante el perfilamiento")
        digest = hashlib.sha256()
        for chunk in _chunks(original):
            digest.update(chunk)
        if digest.hexdigest() != spec.sha256:
            raise ValueError("El SHA-256 del original cambió durante el perfilamiento")
        c.close()
        c = None
        shutil.rmtree(work)
        files = {
            p.name: {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "size_bytes": p.stat().st_size,
            }
            for p in sorted(pending.glob("*.parquet"))
        }
        record = {
            "algorithm": VERSION,
            "source_id": spec.source_id,
            "kind": spec.kind,
            "profile_spec": spec.model_dump(mode="json"),
            "input_sha256": spec.sha256,
            "acquisition_manifest": str(spec.manifest),
            "verified_at_utc": datetime.now(UTC).isoformat(),
            "duckdb_version": duckdb.__version__,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "clock_status": "unverified_source_clock",
            "input_unchanged": True,
            "files": files,
        }
        (pending / "manifest.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        )
        destination = output_root / (spec.source_id + "-" + uuid4().hex)
        os.rename(pending, destination)
        return destination
    finally:
        if c is not None:
            c.close()
        if pending.exists():
            shutil.rmtree(pending)
