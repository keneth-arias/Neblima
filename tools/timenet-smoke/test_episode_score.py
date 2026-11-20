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
            with self.assertRaisesRegex(ValueError, "1 cruce.*a.*2"):
                read_quantiles(path, sha256_file(path), np.array(["a", "b"]), "a" * 64)

    def test_training_frequency_persistence_reliability_and_paired_brier(self):
        y = np.array([[1] * 6, [6] * 6], dtype=float)
        table = scores(
            y,
            y,
            y,
            y,
            np.array([5.0, 5.0]),
            np.array([0.0, 0.0]),
            np.array([0.1, 0.9]),
            np.array([0, 1]),
            np.array([0.5, 0.5]),
            np.array([0, 168]),
        )["event"]["all"]
        self.assertAlmostEqual(table["brier"], 0.01)
        self.assertEqual(table["training_frequency_brier"], 0.25)
        self.assertEqual(table["persistence_brier"], 0.5)
        self.assertEqual(sum(r["windows"] for r in table["reliability"]), 2)
        self.assertAlmostEqual(table["brier_difference"]["difference"], -0.24)

    def test_coincident_ids_do_not_admit_foreign_histories(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from episode_calibration import verify_candidate_bundle
        from export_senamhi import sha256_file

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "selection"
            folder.mkdir()
            ids = np.array(["a", "b"])
            np.savez(folder / "history.npz", window_id=ids, history=np.ones((2, 24)))
            frozen = sha256_file(folder / "history.npz")
            m = {"blocks": {"selection": {"files": {"history.npz": frozen}}}}
            np.savez(root / "data.npz", window_id=ids, history=np.zeros((2, 24)))
            spec = {
                "head": "quantile",
                "phase": "infer",
                "schema": "forecast-input-v1",
                "unit": "ug/m3",
                "block": "selection",
                "split_sha256": "a" * 64,
                "files": {"data.npz": sha256_file(root / "data.npz")},
            }
            release = root / "manifest.json"
            release.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, "historias"):
                verify_candidate_bundle(
                    root, "selection", "a" * 64, m, release, sha256_file(release), "quantile", ids
                )

    def test_same_calendar_draws_for_concentration_and_onsets(self):
        from pathlib import Path
        from runpy import run_path

        from episode_score import block_difference

        warnings = run_path(
            str(Path(__file__).resolve().parents[2] / "src/airaware/episode_warnings.py")
        )
        hours = np.array([503, 504, 0, 169, 168, 335, 502, 3, 4, 5])
        delta = np.array([3, 12, 5, 1, 8, 1, 9, -2, 1, 6], dtype=float)
        a = warnings["paired_interval"](hours.tolist(), delta.tolist(), [0.0] * len(hours))
        b = block_difference(hours, delta, 168)
        np.testing.assert_allclose(
            [a["difference"], a["lower"], a["upper"]], [b["difference"], *b["ci95"]]
        )
