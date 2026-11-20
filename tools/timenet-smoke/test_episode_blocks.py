"""Comprobar purga temporal, umbrales y separación física de los insumos."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import numpy as np
from episode_blocks import export_blocks
from export_senamhi import sha256_file


class EpisodeBlocksTest(TestCase):
    def test_purge_and_training_only_threshold(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            start = datetime(2020, 1, 1, tzinfo=UTC)
            hours = np.array([23, 24, 41, 42, 70, 71, 89, 90, 119, 137, 138, 167])
            stamps = [(start + timedelta(hours=int(h))).isoformat() for h in hours]
            cuts = [(start + timedelta(hours=h)).isoformat() for h in (48, 96, 144)]
            data = root / "source.npz"
            np.savez(
                data,
                window_id=np.array(stamps),
                station_key=["s"] * len(hours),
                origin_at=stamps,
                history=hours[:, None] + np.arange(-23, 1),
                targets=hours[:, None] + np.arange(1, 7),
            )
            dest = root / "run"
            export_blocks([(data, sha256_file(data))], cuts, dest)
            m = json.loads((dest / "manifest.json").read_text())
            self.assertEqual(m["purged"], 4)  # 42, 70, 90, 138
            self.assertEqual(m["blocks"]["train"]["windows"], 3)
            self.assertAlmostEqual(
                json.loads((dest / "thresholds.json").read_text())["stations"]["s"],
                np.quantile(np.arange(42), 0.95),
            )
            seen = set()
            for name in ("train", "calibration", "selection", "test"):
                with (
                    np.load(dest / name / "history.npz") as inputs,
                    np.load(dest / name / "index.npz") as idx,
                ):
                    self.assertEqual(set(inputs.files), {"window_id", "history"})
                    self.assertEqual(inputs["window_id"].tolist(), idx["window_id"].tolist())
                    used = {
                        h for origin in idx["origin_hour"] for h in range(origin - 23, origin + 7)
                    }
                    self.assertFalse(used & seen)
                    seen.update(used)
            with self.assertRaises(FileExistsError):
                export_blocks([(data, sha256_file(data))], cuts, dest)
            with self.assertRaisesRegex(ValueError, "huella"):
                export_blocks([(data, "0" * 64)], cuts, root / "bad")
            self.assertFalse((root / "bad").exists())
