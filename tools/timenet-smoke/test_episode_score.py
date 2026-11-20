"""Comprobar el denominador y el estrato de cada medida horaria."""

from unittest import TestCase

import numpy as np
from episode_score import scores


class EpisodeScoreTest(TestCase):
    def test_incomplete_follow_up_and_active_history(self):
        y = np.array([[1.0, 2, 3, 4, 5, 6], [1.0, 2, 3, 4, 5, np.nan]])
        table = scores(
            y,
            np.ones_like(y),
            np.zeros_like(y),
            np.full_like(y, 4),
            np.array([5.0, 5.0]),
            np.array([0.0, 6.0]),
            np.array([0.75, 0.5]),
            np.array([1, -1]),
        )
        self.assertEqual(table["all"]["targets"], 11)
        self.assertEqual(table["high"]["targets"], 3)
        self.assertAlmostEqual(table["all"]["coverage"], 8 / 11)
        self.assertEqual(table["by_horizon"][-1]["targets"], 1)
        self.assertEqual(table["event"]["below"]["brier"], 0.25**2)
        self.assertIsNone(table["event"]["active"]["brier"])
        self.assertEqual(table["event"]["ineligible"], 1)

    def test_quantile_export_contract_and_paired_block_metrics(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from episode_quantiles import read_quantiles
        from export_senamhi import sha256_file

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "q.npz"
            values = np.broadcast_to([2.0, 3.0, 4.0], (2, 6, 3)).copy()
            fields = {
                "window_id": ["b", "a"],
                "quantiles": values,
                "predicted": values[:, :, 1],
                "unit": "ug/m3",
                "schema_version": 2,
                "task": "quantile",
                "levels": [0.1, 0.5, 0.9],
                "forecast_hour": np.arange(1, 7),
                "input_manifest_sha256": "a" * 64,
                "checkpoint_sha256": "c" * 64,
            }
            np.savez(path, **fields)
            q, checkpoint = read_quantiles(path, sha256_file(path), np.array(["a", "b"]), "a" * 64)
            self.assertEqual(q.shape, (2, 6, 3))
            self.assertEqual(checkpoint, "c" * 64)
            values[1, 1] = [3, 1, 2]
            np.savez(path, **fields)
            with self.assertRaisesRegex(ValueError, "cruce"):
                read_quantiles(path, sha256_file(path), np.array(["a", "b"]), "a" * 64)
