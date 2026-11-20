"""Vincular los índices históricos H24/F6 con la serie y el instrumento de origen."""

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
from episode_blocks import BLOCKS, VERSION
from episode_calibration import check_file


def trace(blocks, splits, hours, block_hash, split_hash, timeline_hash):
    check_file(blocks / "manifest.json", block_hash)
    check_file(splits, split_hash)
    check_file(hours, timeline_hash)
    manifest = json.loads((blocks / "manifest.json").read_text())
    if manifest["version"] != VERSION or manifest["purpose"] != "retrospective_replay":
        raise ValueError("Se requiere la repetición histórica de cuatro bloques")

    with duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone='UTC'")
        db.execute("""
            CREATE TABLE replay(window_id VARCHAR PRIMARY KEY, station_key VARCHAR NOT NULL,
                origin_hour BIGINT NOT NULL, source_index INTEGER NOT NULL,
                block VARCHAR NOT NULL)
        """)
        for name in (*BLOCKS, "purged"):
            if name == "purged":
                path, digest = blocks / "purged.npz", manifest["purged_sha256"]
                count = manifest["purged"]
            else:
                spec = manifest["blocks"][name]
                path, digest = blocks / name / "index.npz", spec["files"]["index.npz"]
                count = spec["windows"]
            check_file(path, digest)
            with np.load(path, allow_pickle=False) as index:
                rows = pa.table(
                    {
                        k: index[k]
                        for k in ("window_id", "station_key", "origin_hour", "source_index")
                    }
                )
            if len(rows) != count:
                raise ValueError(f"El conteo del índice difiere en {name}")
            db.register("phase_rows", rows)
            db.execute("INSERT INTO replay SELECT *, ? FROM phase_rows", [name])
            db.unregister("phase_rows")

        db.execute(
            """CREATE TEMP TABLE original AS
               SELECT window_id, station_key, series_id, origin_at,
                      CASE split WHEN 'train' THEN 0 WHEN 'validation' THEN 1
                                 WHEN 'test' THEN 2 END AS source_index
               FROM read_parquet(?) WHERE split != 'purged'""",
            [str(splits)],
        )
        db.execute(
            """CREATE TEMP TABLE signals AS
               SELECT DISTINCT series_id, station_key, sensor_id FROM read_parquet(?)
               WHERE parameter_raw='PM2_5' AND parameter='PM2.5' AND unit='ug/m3'""",
            [str(hours)],
        )
        db.execute("""
            CREATE TEMP TABLE links AS
            SELECT r.block, o.station_key, o.series_id, s.sensor_id, r.window_id AS replay_id,
                   o.window_id AS original_id, s.series_id AS signal_id
            FROM replay r FULL JOIN original o
              ON r.window_id=o.window_id AND r.station_key=o.station_key
             AND r.source_index=o.source_index
             AND to_timestamp(r.origin_hour * 3600)=o.origin_at
            LEFT JOIN signals s ON o.series_id=s.series_id AND o.station_key=s.station_key
        """)
        total, distinct_ids, missing = db.execute("""
            SELECT count(*), count(DISTINCT replay_id),
                   count(*) FILTER (WHERE replay_id IS NULL OR original_id IS NULL
                                    OR signal_id IS NULL)
            FROM links
        """).fetchone()
        if missing or total != distinct_ids or total == 0:
            raise ValueError("Los bloques y las series de origen no corresponden uno a uno")
        signals = {}
        for station, series, sensor, block, windows in db.execute("""
            SELECT station_key, series_id, sensor_id, block, count(*) FROM links
            GROUP BY ALL ORDER BY station_key, series_id, block
        """).fetchall():
            entry = signals.setdefault(
                (station, series),
                dict(station_key=station, series_id=series, sensor_id=sensor, blocks={}),
            )
            entry["blocks"][block] = windows
    return {
        "version": "lima-h24-f6-procedencia-v1",
        "blocks_sha256": block_hash,
        "splits_sha256": split_hash,
        "timeline_sha256": timeline_hash,
        "matched_windows_including_purged": total,
        "series": list(signals.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("blocks", "splits", "hours"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    metadata = Path(__file__).resolve().parents[2] / "metadata"
    origin = json.loads((metadata / "qwen-smoke.json").read_text())["provenance"]
    replay = json.loads((metadata / "intervalos-pm25-replay-v1.json").read_text())
    receipt = trace(
        args.blocks,
        args.splits,
        args.hours,
        replay["manifest_sha256"],
        origin["splits_sha256"],
        origin["timeline_sha256"],
    )
    print(json.dumps(receipt, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
