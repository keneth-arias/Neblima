"""Verificar cortes, separación de permisos y procedencia del ajuste directo."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from direct_cohorts import export
from episode_blocks import VERSION
from export_senamhi import sha256_file
from joint_windows import write_json


def digest_ids(names):
    return hashlib.sha256("".join(f"{name}\n" for name in sorted(names)).encode()).hexdigest()


class DirectCohortsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        source = self.root / "train"
        source.mkdir()
        # Fin de ajuste 99, inicio válido de validación 100 y de confirmación 200.
        hours = np.array([92, 93, 94, 122, 123, 193, 194, 222, 223, 293])
        ids = np.array([f"id-{i}" for i in range(len(hours))])
        self.groups = {
            "fit": [0, 1],
            "inner_validation": [4, 5],
            "confirmation": [8, 9],
            "purged": [2, 3, 6, 7],
        }
        np.savez(
            source / "index.npz", window_id=ids, origin_hour=hours, station_key=["S"] * len(ids)
        )
        self.fit = dict(
            window_id=ids[::-1],
            history=(hours[:, None] + np.arange(-23, 1))[::-1],
            targets=(hours[:, None] + np.arange(1, 7))[::-1],
        )
        self.write_fit()
        self.protocol = {
            "version": "lima-directo-cohortes-v1",
            "source_manifest_sha256": sha256_file(self.root / "manifest.json"),
            "weights_manifest_sha256": "f" * 64,
            "cuts_utc": ["1970-01-05T04:00:00Z", "1970-01-09T08:00:00Z", "1970-01-13T12:00:00Z"],
            "cohorts": {
                k: {"windows": len(ix), "ids_sha256": digest_ids(ids[ix])}
                for k, ix in self.groups.items()
            },
            "fit_graph_sample": {"windows": 2, "ids_sha256": digest_ids(ids[:2])},
        }
        self.dest = self.root / "output"
        self.protocol_path = self.root / "protocol.json"

    def write_fit(self):
        folder = self.root / "train"
        np.savez(folder / "fit.npz", **self.fit)
        write_json(
            self.root / "manifest.json",
            {
                "version": VERSION,
                "unit": "ug/m3",
                "blocks": {"train": {"files": {p.name: sha256_file(p) for p in folder.iterdir()}}},
            },
        )

    def run_export(self):
        write_json(self.protocol_path, self.protocol)
        return export(self.root, self.protocol_path, self.dest)

    def test_physical_roles_and_fit_only_threshold(self):
        record = self.run_export()
        purged = self.dest / "purged.json"
        self.assertEqual(json.loads(purged.read_bytes()), ["id-2", "id-3", "id-6", "id-7"])
        self.assertEqual(record["purged_file_sha256"], sha256_file(purged))
        seen = set()
        for role, owner in (
            ("fit", "trainer"),
            ("inner_validation", "trainer"),
            ("confirmation", "scorer"),
        ):
            folder = self.dest / owner / role
            spec = json.loads((folder / "manifest.json").read_text())
            self.assertEqual(spec["phase"], role)
            self.assertEqual(sha256_file(folder / "manifest.json"), record["manifests"][role])
            self.assertEqual(spec["files"]["data.npz"], sha256_file(folder / "data.npz"))
            with np.load(folder / "data.npz", allow_pickle=False) as data:
                used = {
                    (s, h)
                    for s, origin in zip(data["station_key"], data["origin_hour"], strict=True)
                    for h in range(origin - 23, origin + 7)
                }
                self.assertFalse(used & seen)
                seen.update(used)
                np.testing.assert_array_equal(data["targets"][:, 0], data["origin_hour"] + 1)
            thresholds = json.loads((folder / "thresholds.json").read_text())
            self.assertEqual(thresholds["stations"]["S"], np.quantile(np.arange(69, 94), 0.95))
            self.assertEqual(
                thresholds["fit_ids_sha256"], self.protocol["cohorts"]["fit"]["ids_sha256"]
            )
        self.assertEqual(
            {p.name for p in (self.dest / "trainer").iterdir()}, {"fit", "inner_validation"}
        )
        with self.assertRaises(FileExistsError):
            self.run_export()

    def test_index_includes_incomplete_windows_omitted_by_producer(self):
        index = self.root / "train/index.npz"
        with np.load(index, allow_pickle=False) as original:
            # Intercalar un ID sin objetivos completos y desordenar también el índice.
            rows = {k: original[k][::-1] for k in original.files}
        np.savez(
            index,
            window_id=np.append(rows["window_id"], "id-1a"),
            station_key=np.append(rows["station_key"], "T"),
            origin_hour=np.append(rows["origin_hour"], 95),
        )
        self.write_fit()
        self.protocol["source_manifest_sha256"] = sha256_file(self.root / "manifest.json")
        self.run_export()
        with np.load(self.dest / "trainer/fit/data.npz", allow_pickle=False) as fit:
            self.assertEqual(fit["window_id"].tolist(), ["id-0", "id-1"])
            self.assertEqual(fit["origin_hour"].tolist(), [92, 93])

    def test_unindexed_fit_id_is_rejected(self):
        self.fit["window_id"][0] = "zzzz"
        self.write_fit()
        self.protocol["source_manifest_sha256"] = sha256_file(self.root / "manifest.json")
        with self.assertRaisesRegex(ValueError, "índice"):
            self.run_export()
        self.assertFalse(self.dest.exists())

    def test_rejects_unsorted_cuts_and_window_ending_at_final_cut(self):
        cuts = self.protocol["cuts_utc"]
        for bad in ([cuts[1], cuts[0], cuts[2]], [*cuts[:2], "1970-01-13T11:00:00Z"]):
            with self.subTest(cuts=bad):
                self.protocol["cuts_utc"] = bad
                with self.assertRaisesRegex(ValueError, "Cortes"):
                    self.run_export()
                self.assertFalse(self.dest.exists())

    def test_nonfinite_complete_window_rejected(self):
        for field, value in (("history", np.nan), ("targets", np.inf)):
            with self.subTest(field=field):
                original = self.fit[field]
                self.fit[field] = original.astype(float)
                self.fit[field][0, 0] = value
                self.write_fit()
                self.protocol["source_manifest_sha256"] = sha256_file(self.root / "manifest.json")
                with self.assertRaisesRegex(ValueError, "finitos"):
                    self.run_export()
                self.assertFalse(self.dest.exists())
                self.fit[field] = original

    def test_duplicate_station_hour_rejected(self):
        index = self.root / "train/index.npz"
        with np.load(index, allow_pickle=False) as data:
            rows = dict(data)
        rows["origin_hour"][0] = rows["origin_hour"][1]
        np.savez(index, **rows)
        self.write_fit()
        self.protocol["source_manifest_sha256"] = sha256_file(self.root / "manifest.json")
        with self.assertRaisesRegex(ValueError, "duplicadas"):
            self.run_export()
        self.assertFalse(self.dest.exists())

    def test_missing_fit_row_even_with_new_file_digests(self):
        self.fit = {k: v[1:] for k, v in self.fit.items()}
        self.write_fit()
        self.protocol["source_manifest_sha256"] = sha256_file(self.root / "manifest.json")
        with self.assertRaisesRegex(ValueError, "confirmation"):
            self.run_export()
        self.assertFalse(self.dest.exists())

    def test_modified_source_or_role_rejected_without_output(self):
        self.protocol["cohorts"]["inner_validation"]["ids_sha256"] = self.protocol["cohorts"][
            "confirmation"
        ]["ids_sha256"]
        with self.assertRaisesRegex(ValueError, "inner_validation"):
            self.run_export()
        (self.root / "train/index.npz").write_bytes(b"otro")
        with self.assertRaisesRegex(ValueError, "huella"):
            self.run_export()
        self.assertFalse(self.dest.exists())

    def test_fit_sample_uses_hash_order(self):
        chosen = min(("id-0", "id-1"), key=lambda key: (hashlib.sha256(key.encode()).digest(), key))
        self.protocol["fit_graph_sample"] = {"windows": 1, "ids_sha256": digest_ids([chosen])}
        self.run_export()
        with np.load(self.dest / "trainer/fit/data.npz", allow_pickle=False) as data:
            self.assertEqual(data["window_id"][data["graph_sample"]].tolist(), [chosen])

    def test_graph_sample_mismatch(self):
        self.protocol["fit_graph_sample"]["ids_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "muestra"):
            self.run_export()
        self.assertFalse(self.dest.exists())
