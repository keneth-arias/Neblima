"""Pruebas sintéticas de la confirmación pareada de los pronósticos directos."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from direct_cohorts import membership
from direct_confirmation import block_interval, evaluate, score
from export_senamhi import sha256_file
from joint_windows import write_json


class PairedConfirmationTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.origins = np.array([166, 167, 335, 503, 671, 839])
        self.stations = np.array(["S"] * 6)
        hours = self.origins[:, None] + np.arange(1, 7)
        self.targets = np.where(np.isin(hours, [168, 336, 504, 672]), 10.0, 0.0)
        self.high = self.targets >= 10
        self.history = np.zeros((6, 24))
        self.predictions = {
            seed: {"normalized-mse": self.targets + err, "physical-mae": self.targets.copy()}
            for seed, err in (("27", 2), ("28", 4))
        }

    def test_boundaries_and_decision(self):
        result = evaluate(
            self.origins, self.stations, self.history, self.targets, self.high, self.predictions
        )
        self.assertEqual(result["decision"], "advance_to_calibration")
        self.assertEqual(result["high_pairs"], 5)
        self.assertEqual(result["high_station_hours"], 4)
        self.assertEqual(result["station_hours"], 31)
        weekly = result["blocks"]["168"]
        self.assertEqual(weekly["blocks"], 6)
        self.assertEqual(weekly["high_blocks"], 4)
        self.assertEqual(weekly["ci95"], [3, 3])
        self.assertEqual(weekly["accepted"], 2000)
        self.assertGreater(weekly["discarded"], 0)
        self.assertIsNone(result["blocks"]["336"]["ci95"])
        self.assertEqual(result["persistence"]["high_mae"], 10)
        self.assertEqual(result["seeds"]["28"]["normalized-mse"]["mae_by_horizon"], [4] * 6)

    def test_weighted_shared_draws(self):
        hours = self.origins[:, None] + np.arange(1, 7)
        delta = np.stack((hours % 7 - 2, 3 - hours % 5))
        got = block_interval(hours, self.high, delta, 168)
        blocks = hours // 168
        observed = np.unique(blocks)
        rng = np.random.default_rng(27)
        draws = []
        discarded = 0
        while len(draws) < 2000:
            chosen = rng.choice(observed, len(observed))
            weights = sum((blocks == key).astype(int) for key in chosen) * self.high
            if weights.sum():
                draws.append(np.average(delta.mean(axis=0), weights=weights))
            else:
                discarded += 1
        np.testing.assert_allclose(got["ci95"], np.percentile(draws, [2.5, 97.5]))
        self.assertEqual(got["discarded"], discarded)

    def test_sparse_and_global_gates(self):
        def run(mask):
            return evaluate(
                self.origins, self.stations, self.history, self.targets, mask, self.predictions
            )

        sparse = run(np.zeros_like(self.high))
        self.assertEqual(sparse["decision"], "inconclusive")
        self.assertIsNone(sparse["high_improvement"])
        self.assertEqual(sparse["blocks"]["168"]["accepted"], 0)
        self.predictions["27"]["physical-mae"][~self.high] += 20
        self.assertEqual(run(self.high)["decision"], "retain_control")
        for seed in self.predictions.values():
            seed["physical-mae"] = self.targets.copy()
            seed["normalized-mse"] = self.targets + 1
            seed["physical-mae"][0:2] += 2
        self.assertEqual(run(self.high)["decision"], "inconclusive")

    def fixture(self):
        ids = np.array([f"ventana-{i}" for i in range(6)])

        def save(name, data):
            path = self.root / name
            write_json(path, data)
            return sha256_file(path)

        member = membership(ids)
        protocol = {
            "version": "lima-directo-cohortes-v1",
            "weights_manifest_sha256": "a" * 64,
            "source_manifest_sha256": "b" * 64,
            "cohorts": {"confirmation": member, "fit": {"ids_sha256": "c" * 64}},
        }
        protocol_hash = save("protocol.json", protocol)
        np.savez(
            self.root / "data.npz",
            targets=self.targets,
            history=self.history,
            station_key=self.stations,
            origin_hour=self.origins,
            window_id=ids,
        )
        thresholds = save(
            "thresholds.json",
            {
                "unit": "ug/m3",
                "method": "linear_p95_unique_fit_history_station_hours",
                "fit_ids_sha256": "c" * 64,
                "stations": {"S": 10},
            },
        )
        cohort = save(
            "manifest.json",
            {
                "phase": "confirmation",
                "schema": "forecast-direct-cohort-v1",
                "head": "direct",
                "unit": "ug/m3",
                "historical_use": "all_roles_previously_used_for_historical_training",
                "protocol_sha256": protocol_hash,
                "source_manifest_sha256": "b" * 64,
                "weights_manifest_sha256": "a" * 64,
                **member,
                "files": {
                    "data.npz": sha256_file(self.root / "data.npz"),
                    "thresholds.json": thresholds,
                },
            },
        )
        np.savez(self.root / "history.npz", window_id=ids[::-1], history=self.history[::-1])
        history_hash = sha256_file(self.root / "history.npz")
        freeze = {
            "schema": "direct-confirmation-selection-v1",
            "confirmation_manifest_sha256": cohort,
            "checkpoints": {},
        }
        receipts = {"schema": "direct-confirmation-predictions-v1", "arms": {}}
        for i, (seed, predictions) in enumerate(self.predictions.items()):
            freeze["checkpoints"][seed] = {}
            receipts["arms"][seed] = {}
            for j, (objective, values) in enumerate(predictions.items()):
                digest = str(i * 2 + j + 1) * 64
                path = self.root / f"{seed}-{objective}.npz"
                np.savez(
                    path,
                    window_id=ids[::-1],
                    predicted=values[::-1],
                    checkpoint_sha256=digest,
                    forecast_hour=np.arange(1, 7),
                )
                freeze["checkpoints"][seed][objective] = digest
                receipts["arms"][seed][objective] = {
                    "history_sha256": history_hash,
                    "output_sha256": sha256_file(path),
                }
        return save("selection.json", freeze), save("predictions.json", receipts)

    def run_score(self, freeze, inventory):
        return score(
            self.root / "selection.json",
            freeze,
            self.root / "predictions.json",
            inventory,
            self.root,
            self.root / "report.json",
            protocol_path=self.root / "protocol.json",
        )

    def test_complete_chain_and_no_overwrite(self):
        pins = self.fixture()
        self.run_score(*pins)
        report = self.root / "report.json"
        self.assertEqual(json.loads(report.read_bytes())["decision"], "advance_to_calibration")
        with self.assertRaises(FileExistsError):
            self.run_score(*pins)

    def test_swapped_checkpoints_rejected_even_when_outputs_rehashed(self):
        freeze, inventory = self.fixture()
        file = self.root / "selection.json"
        selected = json.loads(file.read_bytes())
        selected["checkpoints"]["27"], selected["checkpoints"]["28"] = (
            selected["checkpoints"]["28"],
            selected["checkpoints"]["27"],
        )
        write_json(file, selected)
        with self.assertRaisesRegex(ValueError, "checkpoint"):
            self.run_score(sha256_file(file), inventory)
        self.assertFalse((self.root / "report.json").exists())

    def test_changed_history_rejected_even_with_matching_inventory(self):
        freeze, _ = self.fixture()
        file = self.root / "history.npz"
        with np.load(file) as old:
            ids = old["window_id"]
        np.savez(file, window_id=ids, history=self.history + 1)
        receipt = self.root / "predictions.json"
        inventory = json.loads(receipt.read_bytes())
        for arms in inventory["arms"].values():
            for entry in arms.values():
                entry["history_sha256"] = sha256_file(file)
        write_json(receipt, inventory)
        with self.assertRaisesRegex(ValueError, "historias"):
            self.run_score(freeze, sha256_file(receipt))
        self.assertFalse((self.root / "report.json").exists())

    def test_rejects_damaged_files_wrong_prediction_axes_and_role(self):
        for fault in (
            "selection_hash",
            "file_hash",
            "forecast_hour",
            "duplicate_id",
            "quantile",
            "role",
            "missing_seed",
        ):
            with self.subTest(fault=fault):
                freeze, receipt_sha = self.fixture()
                selection_file = self.root / "selection.json"
                selection = json.loads(selection_file.read_bytes())
                if fault == "selection_hash":
                    freeze = "0" * 64
                elif fault == "role":
                    manifest = self.root / "manifest.json"
                    spec = json.loads(manifest.read_bytes())
                    spec["phase"] = "inner_validation"
                    write_json(manifest, spec)
                    selection["confirmation_manifest_sha256"] = sha256_file(manifest)
                    write_json(selection_file, selection)
                    freeze = sha256_file(selection_file)
                elif fault == "missing_seed":
                    del selection["checkpoints"]["28"]
                    write_json(selection_file, selection)
                    freeze = sha256_file(selection_file)
                else:
                    path = self.root / "27-physical-mae.npz"
                    with np.load(path) as archive:
                        fields = dict(archive)
                    if fault == "duplicate_id":
                        fields["window_id"][0] = fields["window_id"][1]
                    elif fault == "quantile":
                        fields["quantiles"] = fields["predicted"]
                    else:
                        fields["forecast_hour"] = np.arange(6)
                    np.savez(path, **fields)
                    if fault != "file_hash":
                        receipt = self.root / "predictions.json"
                        inventory = json.loads(receipt.read_bytes())
                        inventory["arms"]["27"]["physical-mae"]["output_sha256"] = sha256_file(path)
                        write_json(receipt, inventory)
                        receipt_sha = sha256_file(receipt)
                with self.assertRaises(ValueError):
                    self.run_score(freeze, receipt_sha)
                self.assertFalse((self.root / "report.json").exists())
