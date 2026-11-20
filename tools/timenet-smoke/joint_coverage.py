"""Medir ventanas perdidas al exigir PM10 además de PM2.5 en cada cohorte de #88."""

import argparse
import json
from pathlib import Path

import duckdb
from export_senamhi import sha256_file
from joint_windows import FREEZE, write_json


def count_pm25(dataset, paths):
    # Se resuelven conflictos antes de exigir 30 horas con el mismo sensor de PM2.5.
    sql = """
    WITH raw AS (
        SELECT sitio,id_estacion,id_sensor,valor,CASE WHEN fuente='senamhi_horario'
          THEN hora_nativa ELSE observado_utc::TIMESTAMP END AS hora FROM read_parquet(?)
        WHERE fuente=? AND grupo='benchmark' AND parametro='pm25' AND unidad='µg/m³'
    ), valid AS (
        SELECT sitio,id_estacion,hora,min(id_sensor) AS sensor FROM raw
        WHERE date_trunc('hour',hora)=hora AND hora>=? AND hora<?
        GROUP BY sitio,id_estacion,hora HAVING count(DISTINCT id_sensor)<=1
          AND count(DISTINCT valor) FILTER (WHERE isfinite(valor))=1
          AND count(*) FILTER (WHERE valor IS NOT NULL AND NOT isfinite(valor))=0
    ), framed AS (
        SELECT *,lead(hora,29) OVER (PARTITION BY sitio,id_estacion,sensor ORDER BY hora) AS fin
        FROM valid
    ), assigned AS (
        SELECT *,CASE WHEN ? IS NULL THEN 'test' WHEN fin<? THEN 'train'
                 WHEN hora>=? THEN 'validation' ELSE 'purged' END AS split FROM framed
        WHERE fin=hora+interval '29 hours'
    )
    SELECT sitio,id_estacion,split,count(*) FROM assigned GROUP BY ALL ORDER BY 1,2,3
    """
    cut = dataset["cut_utc"]
    with duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone='UTC'")
        rows = db.execute(
            sql,
            [
                [str(p) for p in paths],
                dataset["source"],
                dataset["begin"],
                dataset["end_exclusive"],
                cut,
                cut,
                cut,
            ],
        ).fetchall()
    return {(site, code, split): n for site, code, split, n in rows}


def coverage(registries):
    results = []
    for dataset in json.loads(FREEZE.read_text())["datasets"]:
        source = dataset["source"]
        local = json.loads((registries / source / "resumen.json").read_text())
        paths = [Path(p) for p in local["inputs"]]
        if {p.name: sha256_file(p) for p in paths} != dataset["inputs"]:
            raise ValueError("Insumos diferentes de la cohorte")
        retained = {}
        for station in dataset["stations"]:
            for split in ("train", "validation", "purged", "test"):
                key = (station["site"], station["code"], split)
                retained[key] = retained.get(key, 0) + station[split]
        single = count_pm25(dataset, paths)
        for key in sorted(set(single) | set(retained)):
            n, joint = single.get(key, 0), retained.get(key, 0)
            if joint > n:
                raise ValueError("Hay más ventanas conjuntas que candidatas de PM2.5")
            if n:
                site, code, split = key
                results.append(
                    dict(
                        source=source,
                        site=site,
                        station_key=code,
                        split=split,
                        pm25=n,
                        joint=joint,
                        lost=n - joint,
                    )
                )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registries", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_json(args.output, coverage(args.registries))
