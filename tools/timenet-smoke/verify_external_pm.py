"""Cotejar cada historia y objetivo guardados en TimeF con las observaciones locales."""

import argparse
import json
from datetime import datetime
from pathlib import Path

import duckdb
from export_senamhi import sha256_file
from external_pm import GRID, HOUR, PARAMS
from timenet.reader import TimeFReader

# TimeF 0.12.0 identifica cada bloque por archivo, grupo de filas y posición en el grupo.
BLOCKS = """
SELECT file_name, row_group_id,
       coalesce(sum(row_group_num_rows) OVER (
           PARTITION BY file_name ORDER BY row_group_id
           ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)::BIGINT AS base
FROM parquet_metadata(?) WHERE column_id = 0
"""

COMPARE = """
WITH framed AS (
    SELECT id_estacion, sensor25, sensor10, h,
           lead(h, 29) OVER series AS last_hour, list({channel}) OVER frame AS vals
    FROM cells
    WINDOW series AS (PARTITION BY id_estacion,sensor25,sensor10 ORDER BY h),
           frame AS (series ROWS BETWEEN CURRENT ROW AND 29 FOLLOWING)
), expected AS (
    SELECT *, CASE WHEN $cut IS NULL THEN 'test' WHEN last_hour < $cut THEN 'train'
              WHEN h >= $cut THEN 'validation' END AS assignment
    FROM framed WHERE last_hour=h+29
), saved AS (
    SELECT t.metadata->>'window_id' AS id, t.split,
           epoch((t.metadata->>'origin_at')::TIMESTAMP)::BIGINT//3600-23 AS h,
           r.metadata->>'station_key' AS station, r.metadata->'sensor_ids'->>0 AS sensor25,
           r.metadata->'sensor_ids'->>1 AS sensor10, v.values AS vals,
           (r.metadata->>'first_label')::TIMESTAMP AS first_label,
           t.metadata->>'clock' AS clock, k.start_time_us, a.period_numerator_us,
           a.period_denominator, a.offset_us, a.axis_type, s.unit, s.name, v.signal
    FROM tasks t JOIN {refs} ref USING(task_id)
    JOIN records r USING(record_id) JOIN clocks k USING(clock_id)
    JOIN sources src USING(record_id) JOIN signals s USING(source_id)
    JOIN axes a USING(axis_id) JOIN signal_chunks c USING(signal_id)
    JOIN blocks b ON b.file_name = $release || '/' || c.value_path
                  AND b.row_group_id=c.chunk_major_index
    JOIN read_parquet($shards,filename=true,file_row_number=true) v
         ON v.filename=b.file_name AND v.file_row_number=b.base+c.chunk_minor_index
    WHERE s.name='{channel}'
), comparison AS (
    SELECT e.h AS expected_hour,s.*,e.assignment,
           e.vals[{first}:{last}] AS expected_vals
    FROM (SELECT * FROM expected WHERE assignment IS NOT NULL) e FULL JOIN saved s
      ON e.h=s.h AND e.id_estacion=s.station
      AND e.sensor25 IS NOT DISTINCT FROM s.sensor25 AND e.sensor10 IS NOT DISTINCT FROM s.sensor10
)
SELECT count(*),count(DISTINCT id), count(*) FILTER (WHERE expected_hour IS NULL OR id IS NULL
       OR assignment IS DISTINCT FROM split OR expected_vals IS DISTINCT FROM vals
       OR first_label IS DISTINCT FROM make_timestamp((h+{offset})*$hour)
       OR start_time_us IS DISTINCT FROM (CASE WHEN $utc THEN (h+{offset})*$hour END)
       OR clock IS DISTINCT FROM (CASE WHEN $utc THEN 'UTC' ELSE 'provider_wall_clock' END)
       OR period_numerator_us <> $hour OR period_denominator <> 1 OR axis_type <> 'regular'
       OR offset_us <> CASE WHEN $utc THEN 0 ELSE {offset}*$hour END
       OR unit <> 'microgram / meter ** 3' OR signal <> name)
FROM comparison
"""


def verify(registry, paths=None):
    summary = json.loads((registry / "resumen.json").read_text())
    release = (registry / summary["dataset_id"] / summary["dataset_version"]).resolve()
    paths = [Path(p) for p in summary["inputs"]] if paths is None else paths
    if sorted(sha256_file(p) for p in paths) != sorted(summary["inputs"].values()):
        raise ValueError("Los insumos cambiaron desde la exportación")
    if sha256_file(release / "manifest.json") != summary["manifest_sha256"]:
        raise ValueError("Cambió el manifiesto TimeF")
    with TimeFReader.open(release) as reader:
        reader.verify()
    source = summary["source"]
    cut = summary["cut_utc"]
    shards = str(release / "time_series" / "*.parquet")
    with duckdb.connect(str(release / "control.duckdb"), read_only=True) as db:
        db.execute("SET threads=2")
        db.execute("SET TimeZone='UTC'")
        db.execute(
            "CREATE TEMP TABLE cells AS " + GRID,
            [[str(p) for p in paths], source, summary["begin"], summary["end_exclusive"]],
        )
        db.execute("CREATE TEMP TABLE blocks AS " + BLOCKS, [shards])
        n_tasks = db.sql("SELECT count(*) FROM tasks").fetchone()[0]
        split_ids = dict(
            db.sql(
                """SELECT split, sha256(to_json(list(id ORDER BY id)))
               FROM (SELECT split, metadata->>'window_id' AS id FROM tasks)
               GROUP BY split ORDER BY split"""
            ).fetchall()
        )
        for offset, end, refs in [
            (0, 24, "(SELECT * FROM task_record_refs WHERE field='inputs')"),
            (24, 30, "(SELECT task_id, record_id FROM task_targets WHERE target_kind='record')"),
        ]:
            for channel in PARAMS:
                query = COMPARE.format(
                    channel=channel, first=offset + 1, last=end, offset=offset, refs=refs
                )
                total, unique, errors = db.execute(
                    query,
                    dict(
                        cut=int(datetime.fromisoformat(cut).timestamp()) // 3600 if cut else None,
                        release=str(release),
                        shards=shards,
                        utc=source != "senamhi_horario",
                        hour=HOUR,
                    ),
                ).fetchone()
                if (total, unique, errors) != (n_tasks, n_tasks, 0):
                    raise ValueError(f"{source} {channel} +{offset}: {total}, {unique}, {errors}")
    return {
        "tasks": n_tasks,
        "history_values": n_tasks * 48,
        "target_values": n_tasks * 12,
        "split_ids_sha256": split_ids,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("observations", type=Path, nargs="*")
    args = parser.parse_args()
    print(json.dumps(verify(args.registry, args.observations or None)))
