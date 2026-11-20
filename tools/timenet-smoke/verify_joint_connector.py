"""Contrastar cada ventana del conector público con la versión histórica de AirAware."""

import argparse
import json
from pathlib import Path

import duckdb
from export_senamhi import sha256_file
from joint_windows import FREEZE
from timenet.reader import TimeFReader
from timenet.registry import LocalRegistry
from timenet.types.references import DatasetRef
from verify_external_pm import BLOCKS


def fingerprints(release):
    # Se incluyen las etiquetas y los valores de cada señal, en orden de window_id.
    # Los identificadores internos de TimeF pueden cambiar entre dos construcciones.
    with duckdb.connect(str(release / "control.duckdb"), read_only=True) as db:
        db.execute("SET threads=2")
        shards = str(release / "time_series/*.parquet")
        db.execute("CREATE TEMP TABLE blocks AS " + BLOCKS, [shards])
        rows = db.execute(
            """
            WITH refs AS (
                SELECT task_id,record_id,'history' AS side FROM task_record_refs
                WHERE field='inputs'
                UNION ALL SELECT task_id,record_id,'future' FROM task_targets
                WHERE target_kind='record'
            ), content AS (
                SELECT t.split,side,s.name,t.metadata->>'window_id' AS id,
                       sha256(to_json(struct_pack(
                         id:=id,origin_at:=t.metadata->>'origin_at',clock:=t.metadata->>'clock',
                         station:=r.metadata->>'station_key',series:=r.metadata->'series_ids',
                         unit_status:=r.metadata->>'unit_status',start_us:=k.start_time_us,
                         unit:=s.unit,period:=a.period_numerator_us,den:=a.period_denominator,
                         offset_us:=a.offset_us,axis:=a.axis_type,signal:=v.signal,vals:=v.values
                       ))) AS fingerprint
                FROM tasks t JOIN refs USING(task_id) JOIN records r USING(record_id)
                JOIN clocks k USING(clock_id) JOIN sources src USING(record_id)
                JOIN signals s USING(source_id) JOIN axes a USING(axis_id)
                JOIN signal_chunks c USING(signal_id)
                JOIN blocks b ON b.file_name=?||'/'||c.value_path
                           AND b.row_group_id=c.chunk_major_index
                JOIN read_parquet(?,filename=true,file_row_number=true) v
                ON v.filename=b.file_name AND v.file_row_number=b.base+c.chunk_minor_index
            )
            SELECT split,side,name,count(*),count(DISTINCT id),
                   sha256(string_agg(fingerprint,'' ORDER BY id))
            FROM content GROUP BY ALL ORDER BY 1,2,3
        """,
            [str(release), shards],
        ).fetchall()
    return [
        dict(split=s, side=side, channel=c, rows=n, unique_ids=keys, sha256=d)
        for s, side, c, n, keys, d in rows
    ]


def checked_release(registry, dataset, expected_counts):
    ref = DatasetRef.parse(f"airaware/{dataset}@0.1.0")
    release = Path(LocalRegistry(registry).open_release(ref).root)
    with TimeFReader.open(release) as reader:
        reader.verify()
        counts = {split: reader.read_task_table(split=split).num_rows for split in expected_counts}
        if counts != expected_counts or sum(counts.values()) != reader.read_task_table().num_rows:
            raise ValueError("Conteos de tareas diferentes")
    return release


def compare(registry, internal):
    ds = next(d for d in json.loads(FREEZE.read_text())["datasets"] if d["source"] == "historico")
    if sha256_file(internal / "manifest.json") != ds["manifest_sha256"]:
        raise ValueError("Histórico interno distinto del conjunto congelado")
    with TimeFReader.open(internal) as reader:
        reader.verify()
    counts = {"train": 251915, "validation": 44458}
    joint = checked_release(registry, "lima-pm25-pm10-forecast", counts)
    hashes = fingerprints(joint)
    if (
        hashes != fingerprints(internal)
        or len(hashes) != 8
        or any(
            row["rows"] != counts[row["split"]] or row["rows"] != row["unique_ids"]
            for row in hashes
        )
    ):
        raise ValueError("Las ventanas o los valores del conector difieren del registro local")
    legacy_counts = {"train": 237397, "validation": 50706, "test": 50789}
    legacy = checked_release(registry, "lima-pm25-forecast", legacy_counts)
    return dict(
        joint_counts=counts,
        pm25_counts=legacy_counts,
        windows_sha256=hashes,
        internal_manifest_sha256=ds["manifest_sha256"],
        connector_manifest_sha256=sha256_file(joint / "manifest.json"),
        pm25_manifest_sha256=sha256_file(legacy / "manifest.json"),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("internal", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.registry.resolve(), args.internal.resolve()), indent=2))
