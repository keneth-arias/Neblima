"""Verificar la procedencia con instrumentos ausentes y filas originales permutadas."""

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from episode_blocks import BLOCKS, VERSION
from episode_source_audit import trace
from export_senamhi import sha256_file


class SourceTest(TestCase):
    def test_exact_origin_station_split_and_nullable_sensor(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {"version": VERSION, "purpose": "retrospective_replay", "blocks": {}}
            original = []
            for hour, (name, role) in enumerate(
                zip((*BLOCKS, "purged"), (0, 1, 1, 2, 1), strict=True)
            ):
                path = root / "purged.npz" if name == "purged" else root / name / "index.npz"
                path.parent.mkdir(exist_ok=True)
                np.savez(
                    path,
                    window_id=[name],
                    station_key=["a"],
                    origin_hour=[hour],
                    source_index=[role],
                )
                if name == "purged":
                    manifest.update(purged=1, purged_sha256=sha256_file(path))
                else:
                    manifest["blocks"][name] = {
                        "windows": 1,
                        "files": {"index.npz": sha256_file(path)},
                    }
                original.append(
                    dict(
                        window_id=name,
                        station_key="a",
                        series_id="series-a",
                        origin_at=datetime.fromtimestamp(hour * 3600, UTC),
                        split=("train", "validation", "test")[role],
                    )
                )
            (root / "manifest.json").write_text(json.dumps(manifest))
            split, hours = root / "splits.parquet", root / "hours.parquet"
            signal = dict(
                station_key="a",
                series_id="series-a",
                sensor_id=None,
                parameter_raw="PM2_5",
                parameter="PM2.5",
                unit="ug/m3",
            )
            pq.write_table(pa.Table.from_pylist([signal]), hours)

            def run(rows):
                pq.write_table(pa.Table.from_pylist(rows), split)
                return trace(
                    root,
                    split,
                    hours,
                    sha256_file(root / "manifest.json"),
                    sha256_file(split),
                    sha256_file(hours),
                )

            result = run(list(reversed(original)))
            self.assertEqual(result["matched_windows_including_purged"], 5)
            self.assertEqual(
                result["series"],
                [
                    dict(
                        station_key="a",
                        series_id="series-a",
                        sensor_id=None,
                        blocks={b: 1 for b in (*BLOCKS, "purged")},
                    )
                ],
            )
            for change in (
                dict(window_id="bad"),
                dict(origin_at=original[2]["origin_at"]),
                dict(station_key="b"),
                dict(split="test"),
                dict(series_id="other"),
            ):
                with self.subTest(change=change), self.assertRaisesRegex(ValueError, "uno a uno"):
                    run([{**original[0], **change}, *original[1:]])
            for rows in (original[:-1], original + [original[0]]):
                with self.assertRaisesRegex(ValueError, "uno a uno"):
                    run(rows)
            known = {**signal, "sensor_id": "instrumento-1"}
            pq.write_table(pa.Table.from_pylist([known]), hours)
            self.assertEqual(run(original)["series"][0]["sensor_id"], "instrumento-1")
            pq.write_table(pa.Table.from_pylist([signal, known]), hours)
            with self.assertRaisesRegex(ValueError, "uno a uno"):
                run(original)
            (root / "train/index.npz").write_bytes(b"otro insumo")
            with self.assertRaisesRegex(ValueError, "huella"):
                run(original)
