"""Vista diagnóstica trazable de originales, compartiendo el parser de #10."""

import csv
import hashlib
from pathlib import Path

import duckdb

from airaware.acquisition.models import Manifest
from airaware.acquisition.store import _chunks, verify_bundle
from airaware.comparison.metrics import records
from airaware.profiling.engine import ProfileSpec, _json_fields, _layout, _literal, _q


def digest(path: Path) -> str:
    h = hashlib.sha256()
    for chunk in _chunks(path):
        h.update(chunk)
    return h.hexdigest()


def load_source(c: duckdb.DuckDBPyConnection, spec: ProfileSpec) -> Path:
    """Crear base con identidad/tiempo crudos idénticos a raw-profile-v2; no escribe raw."""
    with spec.manifest.open("rb") as stream:
        body = stream.read(65537)
    if len(body) > 65536:
        raise ValueError("Manifiesto excesivo")
    m = Manifest.model_validate_json(body)
    if m.sha256 != spec.sha256 or m.spec.source_id != spec.source_id or m.spec.format != "csv":
        raise ValueError("Contrato de adquisición diferente")
    original = verify_bundle(
        m.spec, spec.raw_root.resolve(), spec.manifest.resolve().parent
    ).artifact
    with original.open(encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream, delimiter=m.spec.csv_delimiter, strict=True))
    if header != list(spec.columns) or len(set(header)) != len(header):
        raise ValueError("Columnas distintas del contrato")
    c.execute(
        """CREATE OR REPLACE TABLE input AS SELECT * FROM read_csv(?,columns=?,header=true,
      delim=?,auto_detect=false,force_not_null=?,strict_mode=true,ignore_errors=false)""",
        [str(original), {x: "VARCHAR" for x in header}, m.spec.csv_delimiter, header],
    )
    n = c.execute("SELECT count(*) FROM input").fetchone()
    if spec.expected_rows is not None and (n is None or n[0] != spec.expected_rows):
        raise ValueError("Conteo distinto del contrato")
    station, context, start, end, hourly = _layout(spec.kind)
    geo = "PROVINCIA='LIMA' AND DEPARTAMENTO='LIMA'"
    c.execute(f"""CREATE OR REPLACE TABLE base AS SELECT *,
      {_json_fields(station)} station_context,
      sha256({_literal(spec.source_id)}||station_context) station_key,
      {_q(station[0])} station_label,
      {_json_fields(context) if context else "'[]'"} series_context,
      sha256(station_key||series_context) series_id,
      {start} ts,{end} end_ts,{hourly} hourly,
      CASE WHEN {geo} THEN 'lima' WHEN PROVINCIA='CALLAO' AND DEPARTAMENTO='CALLAO'
        THEN 'callao' ELSE 'outside' END geography FROM input""")
    c.execute("DROP TABLE input")
    return original


def prepare_points(c: duckdb.DuckDBPyConnection, signal: str, geography: str) -> dict:
    """Filtros disjuntos de filas; points contiene instantes únicos admisibles."""
    c.execute(f"""CREATE OR REPLACE TABLE cells AS SELECT *,
      try_cast(trim({_q(signal)}) AS DOUBLE) number,
      CASE WHEN geography!={_literal(geography)} THEN 'outside'
        WHEN NOT hourly THEN 'period'
        WHEN ts IS NULL OR date_trunc('hour',ts)!=ts THEN 'clock'
        WHEN number IS NULL OR NOT isfinite(number) THEN 'value'
        ELSE 'candidate' END row_status FROM base""")
    # La ambigüedad se mide antes de descartar celdas vacías: conserva la política de #10.
    c.execute(f"""CREATE OR REPLACE TABLE slots AS SELECT series_id,ts,end_ts,
      count(DISTINCT number) FILTER(WHERE isfinite(number)) distinct_values,
      min(number) FILTER(WHERE isfinite(number)) AS value
      FROM cells WHERE geography={_literal(geography)} AND hourly AND ts IS NOT NULL
      AND date_trunc('hour',ts)=ts GROUP BY series_id,ts,end_ts""")
    c.execute("""CREATE OR REPLACE TABLE points AS SELECT series_id,ts,min(value) AS value
      FROM slots GROUP BY series_id,ts HAVING count(*)=1 AND bool_and(distinct_values=1)""")
    result = {
        r["row_status"]: r["n"]
        for r in records(c, "SELECT row_status,count(*)::BIGINT n FROM cells GROUP BY row_status")
    }
    accepted = c.execute("""SELECT count(*) FROM cells JOIN points USING(series_id,ts)
      WHERE row_status='candidate' """).fetchone()
    assert accepted is not None
    result["ambiguous"] = result.pop("candidate", 0) - accepted[0]
    result["accepted_rows"] = accepted[0]
    unique = c.execute("SELECT count(*) FROM points").fetchone()
    assert unique is not None
    result["unique_points"] = unique[0]
    result["collapsed_repetitions"] = result["accepted_rows"] - result["unique_points"]
    return result
