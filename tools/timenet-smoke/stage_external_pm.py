"""Preparar los insumos locales fijados de noviembre de 2026 sin consultar la red."""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

HISTORICAL = "896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4"
ARCHIVE = "0623be0b25cd0bd108065ae35257ef0c3d38cb6e8cfa072c29cd6b9b74071f1d"
RECEIPTS = "a0121b7077025b561d8b80c671e6c382e5da953c3840d39c15a9b442005eaa83"
REFRESH = "cf29254a857f5afa081f9030210476c2ecca77c910dcae1378c37a8ed6f42287"
HIST_SQL = """
WITH csv AS (
    SELECT * FROM read_csv(?,header=true,all_varchar=true,parallel=false) WITH ORDINALITY
), renamed AS (
    SELECT ESTACION AS sitio, sha256('senamhi-lima-csv'||to_json(
        [ESTACION,LONGITUD,LATITUD,ALTITUD,DEPARTAMENTO,PROVINCIA,DISTRITO])) AS id_estacion,
        strptime(FECHA||lpad(HORA,6,'0'),'%Y%m%d%H%M%S') AS hora, ordinality+1 AS fila,
        PM2_5 AS pm25, PM10 FROM csv
    WHERE DEPARTAMENTO='LIMA' AND PROVINCIA='LIMA' AND trim(ESTACION)<>''
)
SELECT 'historico' AS fuente,sitio,'benchmark' AS grupo,id_estacion,NULL::VARCHAR AS id_sensor,
       parametro,'µg/m³' AS unidad,hora AS hora_nativa,hora AT TIME ZONE 'UTC' AS observado_utc,
       try_cast(raw AS DOUBLE) AS valor,fila,? AS archivo
FROM renamed UNPIVOT INCLUDE NULLS (raw FOR parametro IN (pm25 AS pm25,PM10 AS pm10))
"""


def readings(html, *, expected_series=None):
    script = re.sub(r"/\*.*?\*/", "", html, flags=re.S)
    labels = re.search(r"categories:\s*\[([^\]]*)\]", script)
    if not labels or "Highcharts.chart" not in script:
        raise ValueError("No se encontró el gráfico horario")
    series = re.findall(
        r"name:\s*'([^']+)'[\s\S]*?\bdata:\s*\[([^\]]*)\]", script.split("series:", 1)[1]
    )
    ((name, values),) = [(name, data) for name, data in series if not name.startswith("ECA")]
    if expected_series is not None and name != expected_series:
        raise ValueError("La serie medida corresponde a otro contaminante")

    def items(text):
        return (
            [x.strip() for x in text.strip().removesuffix(",").split(",")] if text.strip() else []
        )

    for t, v in zip(items(labels[1]), items(values), strict=True):
        yield (
            datetime.strptime(t.strip("'"), "%d/%m/%Y%H:%M:"),
            None if v in ("null", "") else float(v),
        )


def verify(path, digest):
    from export_senamhi import sha256_file

    if sha256_file(path) != digest:
        raise ValueError(f"SHA-256 incorrecto: {path}")


def stage(csv_path, baseline, old_raw, refresh, dest):
    if dest.exists():
        raise FileExistsError(dest)
    obs = baseline / "observaciones.parquet"
    verify(csv_path, HISTORICAL)
    verify(obs, ARCHIVE)
    verify(baseline / "manifest-fuentes.jsonl", RECEIPTS)
    old = [json.loads(s) for s in (baseline / "manifest-fuentes.jsonl").read_text().splitlines()]
    for r in old:
        verify(old_raw / r["archivo"], r["sha256"])
    recent = [json.loads(p.read_text()) for p in sorted((refresh / "recibos").glob("*.json"))]
    with TemporaryDirectory(dir=dest.parent) as tmp, duckdb.connect() as db:
        out = Path(tmp) / "insumos"
        out.mkdir()
        receipt_file = out / "recibos-actualizacion.json"
        receipt_file.write_text(json.dumps(recent, ensure_ascii=False, indent=2) + "\n")
        verify(receipt_file, REFRESH)
        db.execute("SET TimeZone='UTC'")
        stations = dict(
            db.sql(
                "select distinct id_estacion,sitio from read_parquet(?) "
                "where fuente='senamhi_horario' and grupo='benchmark'",
                params=[str(obs)],
            ).fetchall()
        )
        stations.update(
            {
                "111286": "CARABAYLLO",
                "112193": "SAN_BORJA",
                "112208": "SANTA_ANITA",
                "112265": "SAN_MARTIN_DE_PORRES",
                "112267": "SAN_JUAN_DE_LURIGANCHO",
            }
        )
        rows = []
        charts = set()
        inventories = set()
        for receipt in recent:
            path = refresh / receipt["archivo"]
            verify(path, receipt["sha256"])
            args = parse_qs(urlparse(receipt["url"]).query)
            if path.suffix == ".xml":
                inventories.add(path.stem)
                continue
            code = args["estacion"][0]
            param = {"N_PM25": "pm25", "N_PM10": "pm10"}[args["cont"][0]]
            if code not in stations or (code, param) in charts:
                raise ValueError("Consulta horaria inesperada")
            charts.add((code, param))
            for row, (t, v) in enumerate(readings(path.read_text(encoding="latin1")), 1):
                if not datetime(2026, 11, 18) <= t < datetime(2026, 11, 21):
                    raise ValueError("Fecha fuera de la consulta")
                rows.append(
                    dict(
                        fuente="senamhi_horario",
                        grupo="benchmark",
                        sitio=stations[code],
                        id_estacion=code,
                        id_sensor=None,
                        parametro=param,
                        unidad="µg/m³",
                        hora_nativa=t,
                        observado_utc=None,
                        valor=v,
                        archivo=receipt["archivo"],
                        fila=row,
                        etiqueta_publicada=t.strftime("%d/%m/%Y%H:%M:"),
                    )
                )
        # Algunas fichas históricas no publican mediciones en todo el periodo.
        if len(charts) != 24 or len(inventories) != 27:
            raise ValueError("Actualización incompleta")
        delta = pa.Table.from_pylist(rows, schema=pq.read_schema(obs))
        pq.write_table(delta, out / "actualizacion.parquet")
        db.sql(HIST_SQL, params=[str(csv_path), csv_path.name]).write_parquet(
            str(out / "historico.parquet"), compression="zstd"
        )
        out.rename(dest)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("csv_path", "baseline", "old_raw", "refresh", "dest"):
        p.add_argument(arg, type=Path)
    stage(**vars(p.parse_args()))
