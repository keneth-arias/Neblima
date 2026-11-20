"""Comprobar cuantiles de residuos y probabilidad calibrada con datos sintéticos."""

from contextlib import contextmanager
from unittest import TestCase

import numpy as np
from episode_calibration import fit_logistic, fit_residuals, probability


class EpisodeCalibrationTest(TestCase):
    def test_known_residual_quantiles_per_hour(self):
        obs = np.arange(11)[:, None] + np.arange(6)
        q = fit_residuals(np.zeros((11, 6)), obs)
        np.testing.assert_array_equal(q, [1 + np.arange(6), 9 + np.arange(6)])

    def test_logistic_is_monotone_and_degenerate_cases_are_explicit(self):
        x = np.arange(-8, 9, dtype=float)
        y = (x >= 0).astype(float)
        model = fit_logistic(x, y)
        p = probability(x, model)
        self.assertTrue(np.all(np.diff(p) > 0))
        self.assertLess(np.mean((y - p) ** 2), np.mean((y - y.mean()) ** 2))
        inverse = fit_logistic(x, 1 - y)
        np.testing.assert_allclose(probability(x, inverse), (1 - y).mean(), atol=1e-6)
        constant = fit_logistic(x, np.zeros_like(x))
        self.assertEqual(constant["status"], "single_class")
        np.testing.assert_array_equal(probability(x, constant), 0)

    @staticmethod
    @contextmanager
    def calibration_fixture():
        import json
        from argparse import Namespace
        from datetime import UTC, datetime, timedelta
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from episode_blocks import export_blocks
        from export_senamhi import sha256_file

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            start = datetime(2020, 1, 1, tzinfo=UTC)
            hours = np.arange(23, 300)
            dates = [(start + timedelta(hours=int(h))).isoformat() for h in hours]
            cuts = [dates[n - 23] for n in (75, 150, 225)]
            raw = root / "raw.npz"
            np.savez(
                raw,
                window_id=dates,
                station_key=["s"] * len(hours),
                origin_at=dates,
                history=(hours[:, None] + np.arange(-23, 1)) % 23,
                targets=(hours[:, None] + np.arange(1, 7)) % 23,
            )
            blocks = root / "blocks"
            export_blocks([(raw, sha256_file(raw))], cuts, blocks)
            manifest_hash = sha256_file(blocks / "manifest.json")
            threshold_hash = sha256_file(blocks / "thresholds.json")
            t = json.loads((blocks / "thresholds.json").read_text())["stations"]["s"]
            checkpoint = "b" * 64
            for role in ("calibration", "selection"):
                with np.load(blocks / role / "history.npz") as z:
                    ids, history = z["window_id"], z["history"]
                np.savez(
                    root / f"{role}.npz",
                    window_id=ids[::-1],
                    forecast_hour=np.arange(1, 7),
                    checkpoint_sha256=checkpoint,
                    predicted=np.tile(history[::-1, -1:], (1, 6)),
                )
                if role == "calibration":
                    with np.load(blocks / role / "observed.npz") as z:
                        event = (z["targets"].max(axis=1) >= t).astype(int)
                    np.savez(
                        root / "eligible.npz",
                        window_id=ids,
                        event=event,
                        manifest_sha256=manifest_hash,
                        thresholds_sha256=threshold_hash,
                    )
            args = Namespace(
                command="fit",
                blocks=blocks,
                forecasts=root / "calibration.npz",
                output=root / "cal.json",
                manifest_sha256=manifest_hash,
                eligible_labels=root / "eligible.npz",
            )
            yield root, args

    def test_fit_and_apply_require_disjoint_roles_and_matching_release(self):
        from episode_calibration import run
        from export_senamhi import sha256_file

        with self.calibration_fixture() as (root, args):
            blocks = args.blocks
            args.forecasts_sha256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "Huella"):
                run(args)
            self.assertFalse(args.output.exists())
            args.forecasts_sha256 = sha256_file(args.forecasts)
            run(args)
            args.command = "apply"
            args.calibrator = args.output
            args.calibrator_sha256 = sha256_file(args.output)
            args.block = "selection"
            args.forecasts = root / "selection.npz"
            args.forecasts_sha256 = sha256_file(args.forecasts)
            args.output = root / "scored.npz"
            (
                blocks / "selection" / "observed.npz"
            ).unlink()  # el pod de inferencia carece de objetivos
            run(args)
            with np.load(args.output) as z:
                self.assertEqual(z["forecasts_sha256"].item(), args.forecasts_sha256)
                self.assertTrue(np.all(z["lower"] <= z["upper"]))
                self.assertTrue(
                    np.all((z["episode_probability"] >= 0) & (z["episode_probability"] <= 1))
                )
            args.output = root / "bad.npz"
            args.calibrator_sha256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "huella"):
                run(args)
            self.assertFalse(args.output.exists())

    def test_episode_fit_binds_export_to_requested_checkpoint(self):
        import json

        from episode_calibration import run
        from export_senamhi import sha256_file

        with self.calibration_fixture() as (root, args):
            phase = args.blocks / "calibration"
            table = args.blocks / "thresholds.json"
            threshold_sha = sha256_file(table)
            threshold = json.loads(table.read_bytes())["stations"]["s"]
            data = root / "data.npz"
            with np.load(phase / "history.npz") as z:
                ids = z["window_id"]
                np.savez(
                    data,
                    window_id=ids,
                    history=z["history"],
                    station_key=["s"] * len(ids),
                    threshold_ug_m3=np.full(len(ids), threshold),
                    thresholds_sha256=threshold_sha,
                )
            data_sha = sha256_file(data)
            spec = dict(
                block="calibration",
                split_sha256=args.manifest_sha256,
                head="episode",
                phase="infer",
                schema="forecast-input-v1",
                unit="ug/m3",
                files={"data.npz": data_sha},
                thresholds_sha256=threshold_sha,
            )
            manifest = root / "bundle.json"
            export = root / "logits.npz"
            checkpoint = "e" * 64
            for requested in ("f" * 64, None, checkpoint):
                with self.subTest(requested=requested):
                    args.output = root / f"cal-{requested}.json"
                    bundle = dict(spec)
                    if requested is not None:
                        bundle["checkpoint_sha256"] = requested
                    manifest.write_text(json.dumps(bundle))
                    manifest_sha = sha256_file(manifest)
                    np.savez(
                        export,
                        window_id=ids,
                        episode_logit=np.arange(len(ids), dtype=float),
                        task="episode",
                        unit="logit",
                        schema_version=2,
                        thresholds_sha256=threshold_sha,
                        input_manifest_sha256=manifest_sha,
                        input_sha256=data_sha,
                        checkpoint_sha256=checkpoint,
                    )
                    args.episode_logits = [export, sha256_file(export), manifest, manifest_sha]
                    if requested == checkpoint:
                        run(args)
                        self.assertEqual(
                            json.loads(args.output.read_bytes())["episode_checkpoint_sha256"],
                            checkpoint,
                        )
                    else:
                        with self.assertRaisesRegex(ValueError, "punto de control"):
                            run(args)
                        self.assertFalse(args.output.exists())

    def test_reject_invalid_probability_artifacts(self):
        for model in (
            {"status": "single_class", "frequency": 2},
            {"status": "unknown"},
            {"status": "fitted", "scale": 0.0, "center": 0, "intercept": 0, "slope": 1, "l2": 1},
            {"status": "fitted", "scale": 1.0, "center": 0, "intercept": 0, "slope": -1, "l2": 1},
        ):
            with self.subTest(model=model), self.assertRaises(ValueError):
                probability(np.array([1.0, 2.0]), model)

    def test_replay_test_block_cannot_be_opened_with_self_asserted_selection(self):
        from argparse import Namespace

        from episode_calibration import run

        with self.assertRaisesRegex(ValueError, "repetición"):
            run(Namespace(command="apply", block="test"))

    def test_candidate_logits_require_frozen_context_and_align_ids(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from episode_calibration import candidate_logits
        from export_senamhi import sha256_file

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "pred.npz"
            np.savez(
                path,
                window_id=["b", "a"],
                episode_logit=[3.0, -1.0],
                task="episode",
                unit="logit",
                schema_version=2,
                thresholds_sha256="a" * 64,
                checkpoint_sha256="b" * 64,
                input_manifest_sha256="d" * 64,
                input_sha256="e" * 64,
                model_revision="rev",
            )
            values, checkpoint = candidate_logits(
                path, sha256_file(path), np.array(["a", "b"]), "a" * 64, "d" * 64
            )
            np.testing.assert_array_equal(values, [-1.0, 3.0])
            self.assertEqual(checkpoint, "b" * 64)
            with self.assertRaises(ValueError):
                candidate_logits(path, sha256_file(path), np.array(["a", "b"]), "c" * 64, "d" * 64)
