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
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.split = self.root / "splits.parquet"
        self.hours = self.root / "hours.parquet"
        self.roles = ("train", "validation", "test")
        self.hashes = dict(zip(self.roles, ("a" * 64, "b" * 64, "c" * 64), strict=True))
        self.signal = dict(
            station_key="a",
            series_id="series-a",
            sensor_id=None,
            parameter_raw="PM2_5",
            parameter="PM2.5",
            unit="ug/m3",
        )
        pq.write_table(pa.Table.from_pylist([self.signal]), self.hours)
        self.manifest = {
            "version": VERSION,
            "purpose": "retrospective_replay",
            "blocks": {},
            "source_sha256": [self.hashes[r] for r in self.roles],
        }
        self.original = []
        for hour, (name, role) in enumerate(zip((*BLOCKS, "purged"), (0, 1, 1, 2, 1), strict=True)):
            self.write_index(name, [name], [hour], [role])
            self.original.append(
                dict(
                    window_id=name,
                    station_key="a",
                    series_id="series-a",
                    origin_at=datetime.fromtimestamp(hour * 3600, UTC),
                    split=self.roles[role],
                )
            )

    def write_index(self, name, ids, hours, roles):
        path = self.root / "purged.npz" if name == "purged" else self.root / name / "index.npz"
        path.parent.mkdir(exist_ok=True)
        np.savez(
            path,
            window_id=np.array(ids, dtype=str),
            station_key=np.array(["a"] * len(ids), dtype=str),
            origin_hour=np.array(hours, dtype=int),
            source_index=np.array(roles, dtype=int),
        )
        if name == "purged":
            self.manifest.update(purged=len(ids), purged_sha256=sha256_file(path))
        else:
            self.manifest["blocks"][name] = {
                "windows": len(ids),
                "files": {"index.npz": sha256_file(path)},
            }

    def run_trace(self, rows=None):
        path = self.root / "manifest.json"
        path.write_text(json.dumps(self.manifest))
        table = pa.Table.from_pylist(self.original)
        if rows is not None:
            table = pa.Table.from_pylist(rows, schema=table.schema)
        pq.write_table(table, self.split)
        return trace(
            self.root,
            self.split,
            self.hours,
            sha256_file(path),
            sha256_file(self.split),
            sha256_file(self.hours),
            self.hashes,
        )

    def test_exact_origin_station_split_and_nullable_sensor(self):
        result = self.run_trace(list(reversed(self.original)))
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
            dict(origin_at=self.original[2]["origin_at"]),
            dict(station_key="b"),
            dict(split="test"),
            dict(series_id="other"),
        ):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "uno a uno"):
                self.run_trace([{**self.original[0], **change}, *self.original[1:]])
        for rows in (self.original[:-1], self.original + [self.original[0]]):
            with self.assertRaisesRegex(ValueError, "uno a uno"):
                self.run_trace(rows)
        known = {**self.signal, "sensor_id": "instrumento-1"}
        pq.write_table(pa.Table.from_pylist([known]), self.hours)
        self.assertEqual(self.run_trace()["series"][0]["sensor_id"], "instrumento-1")
        pq.write_table(pa.Table.from_pylist([self.signal, known]), self.hours)
        with self.assertRaisesRegex(ValueError, "uno a uno"):
            self.run_trace()
        (self.root / "train/index.npz").write_bytes(b"otro insumo")
        with self.assertRaisesRegex(ValueError, "huella"):
            self.run_trace()

    def test_manifest_scope_order_and_row_counts(self):
        for key, wrong in (("version", "otro"), ("purpose", "operativo")):
            with self.subTest(key=key):
                previous = self.manifest[key]
                self.manifest[key] = wrong
                with self.assertRaisesRegex(ValueError, "repetición histórica"):
                    self.run_trace()
                self.manifest[key] = previous
        self.manifest["source_sha256"].reverse()
        with self.assertRaisesRegex(ValueError, "orden de las fuentes"):
            self.run_trace()
        self.manifest["source_sha256"].reverse()
        self.manifest["blocks"]["train"]["windows"] = 2
        with self.assertRaisesRegex(ValueError, "conteo del índice"):
            self.run_trace()

    def test_empty_cohort_is_not_a_successful_match(self):
        for name in (*BLOCKS, "purged"):
            self.write_index(name, [], [], [])
        with self.assertRaisesRegex(ValueError, "uno a uno"):
            self.run_trace([])
