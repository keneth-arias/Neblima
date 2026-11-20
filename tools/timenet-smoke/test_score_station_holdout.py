"""Probar el puntaje reservado desde un paquete y una salida del worker en disco."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import numpy as np
from export_senamhi import sha256_file
from holdout_station_windows import write_json
from score_station_holdout import score as score_run

CLOSED = datetime(2026, 12, 2, 19, tzinfo=UTC)


def score(*args, now):
    output = args[-1]
    path = output.parent / "tracking.json" if output is not None else None
    return score_run(*args, now=now, tracking=(path, sha256_file(path)) if path else None)


def track(output):
    intent = json.loads((output / ".infer-step-00014838.intent.json").read_bytes())
    predicted = sha256_file(output / "predictions-step-00014838.npz")
    write_json(
        output.parent / "tracking.json",
        {
            "run": {
                "info": {"run_id": "fixture-run", "status": "FINISHED"},
                "data": {
                    "params": [{"key": k, "value": str(v)} for k, v in intent.items()],
                    "tags": [
                        {"key": "artifact_sha256", "value": predicted},
                        {"key": "checkpoint_sha256", "value": "a" * 64},
                    ],
                },
            }
        },
    )


class ScoreTest(TestCase):
    def stage(self, root, head, count):
        cohort = root / "cohort"
        infer, scoring, out = cohort / "infer", cohort / "scoring", root / "output"
        infer.mkdir(parents=True)
        scoring.mkdir()
        out.mkdir()
        spec = json.loads(
            (
                Path(__file__).resolve().parents[2]
                / "configs/training/lima-prueba-futura-campo-marte-v1.json"
            ).read_bytes()
        )
        threshold = root / "thresholds.json"
        write_json(threshold, {"stations": {spec["historical_station_key"]: 100}, "unit": "ug/m3"})
        spec["thresholds_sha256"] = sha256_file(threshold)
        protocol, seal, cal = root / "protocol.json", root / "seal.json", root / "cal.json"
        write_json(protocol, spec)
        ck = "a" * 64
        write_json(cal, {"residual_q10_q90": [[-1] * 6, [1] * 6], "checkpoint_sha256": ck})
        release = {
            "version": "lima-concentracion-prueba-congelada-v1",
            "scope": spec["scope"],
            "protocol_sha256": sha256_file(protocol),
            "thresholds_sha256": sha256_file(threshold),
            "checkpoint_sha256": ck,
            "image": spec["image"],
            "model_revision": "fixture",
            "base_weights_sha256": "b" * 64,
            "seed": 27,
            "sealed_at_utc": "2026-11-20T19:00:00+00:00",
            "direct_calibrator_sha256": sha256_file(cal),
            "head": head,
        }
        write_json(seal, release)
        start = datetime.fromisoformat(spec["origin_start_inclusive"])
        origins = [
            {
                "window_id": f"112194/{(start + timedelta(hours=h)).isoformat()}",
                "eligible": h < count,
            }
            for h in range(168)
        ]
        ids = np.asarray([r["window_id"] for r in origins if r["eligible"]], dtype=str)
        history = np.arange(count)[:, None] + np.arange(24)[None, :]
        y = history[:, -1:] + np.arange(1, 7)[None, :]
        np.savez(infer / "data.npz", history=history, window_id=ids)
        np.savez(scoring / "observed.npz", observed=y, window_id=ids)
        write_json(scoring / "origins.json", origins)
        bundle = {
            "head": head,
            "schema": "forecast-input-v1",
            "block": "external_test",
            "phase": "infer",
            "unit": "ug/m3",
            "files": {"data.npz": sha256_file(infer / "data.npz")},
            "checkpoint_sha256": ck,
            "weights_manifest_sha256": release["base_weights_sha256"],
            "seal_sha256": sha256_file(seal),
        }
        write_json(infer / "manifest.json", bundle)
        bs = sha256_file(infer / "manifest.json")
        rec = {
            "version": "lima-cohorte-campo-marte-v1",
            "protocol_sha256": sha256_file(protocol),
            "seal_sha256": sha256_file(seal),
            "observation_vintage_utc": spec["observation_vintage_utc"],
            "files": {
                name: sha256_file(cohort / name)
                for name in ("infer/manifest.json", "scoring/observed.npz", "scoring/origins.json")
            },
        }
        write_json(cohort / "receipt.json", rec)
        forecast = y.copy()
        forecast[:, 5] += 2
        values = {
            "window_id": ids,
            "forecast_hour": np.arange(1, 7),
            "predicted": forecast,
            "checkpoint_sha256": ck,
        }
        if head == "quantile":
            values.update(
                quantiles=np.stack([forecast - 1, forecast, forecast + 1], axis=-1),
                task=head,
                levels=[0.1, 0.5, 0.9],
                unit="ug/m3",
                schema_version=2,
                input_sha256=sha256_file(infer / "data.npz"),
                input_manifest_sha256=bs,
                model_revision="fixture",
            )
        np.savez(out / "predictions-step-00014838.npz", **values)
        write_json(
            out / ".infer-step-00014838.intent.json",
            {
                "phase": "infer",
                "head": head,
                "bundle_sha256": bs,
                "image": spec["image"],
                "step": 14838,
                "seed": 27,
                "run_id": "test-forecast",
            },
        )
        write_json(
            out / ".infer-step-00014838.receipt.json",
            sha256_file(out / "predictions-step-00014838.npz"),
        )
        track(out)
        return (
            protocol,
            sha256_file(protocol),
            seal,
            sha256_file(seal),
            cohort,
            sha256_file(cohort / "receipt.json"),
            threshold,
            cal,
        ), out

    def test_seven_days_and_both_heads_use_the_same_denominator(self):
        for head in ("quantile", "direct"):
            with self.subTest(head=head), TemporaryDirectory() as tmp:
                inputs, output = self.stage(Path(tmp), head, 168)
                with self.assertRaisesRegex(ValueError, "abierto"):
                    score(*inputs, output, now=CLOSED - timedelta(seconds=1))
                answer = score(*inputs, output, now=CLOSED)
                self.assertEqual(answer["decision"], "review_for_station_concentration_pilot")
                self.assertEqual(answer["distinct_observed_target_hours"], 173)
                self.assertEqual(list(answer["complete_origins_by_date"].values()), [24] * 7)
                result = answer["concentration"]["all"]
                self.assertEqual(result["targets"], 1008)
                self.assertAlmostEqual(result["coverage"], 5 / 6)
                self.assertAlmostEqual(result["mae"], 1 / 3)
                self.assertEqual(result["mae_persistence"], 3.5)
                self.assertEqual(answer["concentration"]["by_horizon"][-1]["mae_persistence"], 6)
                self.assertGreater(answer["concentration"]["high"]["targets"], 0)
                intent = output / ".infer-step-00014838.intent.json"
                meta = json.loads(intent.read_bytes())
                write_json(intent, {**meta, "bundle_sha256": "0" * 64})
                with self.assertRaisesRegex(ValueError, "otra inferencia"):
                    score(*inputs, output, now=CLOSED)

    def test_quantile_width_uses_the_same_physical_bounds_as_selection(self):
        with TemporaryDirectory() as tmp:
            inputs, out = self.stage(Path(tmp), "quantile", 168)
            pred = out / "predictions-step-00014838.npz"
            with np.load(pred, allow_pickle=False) as z:
                values = dict(z)
            values["quantiles"][:, :, 0] = -8
            np.savez(pred, **values)
            write_json(out / ".infer-step-00014838.receipt.json", sha256_file(pred))
            with self.assertRaisesRegex(ValueError, "MLflow"):
                score(*inputs, out, now=CLOSED)
            track(out)
            result = score(*inputs, out, now=CLOSED)
            self.assertAlmostEqual(
                result["concentration"]["all"]["width"], values["quantiles"][:, :, 2].mean()
            )

    def test_sparse_and_empty_cohort(self):
        for n in (0, 4):
            with self.subTest(n=n), TemporaryDirectory() as tmp:
                inputs, out = self.stage(Path(tmp), "direct", n)
                result = score(*inputs, out if n else None, now=CLOSED)
                self.assertEqual(result["decision"], "inconclusive")
                self.assertEqual(result["eligible_histories"], n)
                self.assertEqual(result["concentration"]["all"]["targets"], 6 * n)

    def test_veto_and_mismatched_receipt(self):
        with TemporaryDirectory() as tmp:
            inputs, out = self.stage(Path(tmp), "direct", 168)
            pred = out / "predictions-step-00014838.npz"
            with np.load(pred, allow_pickle=False) as z:
                values = dict(z)
            values["predicted"][:] = 0
            np.savez(pred, **values)
            with self.assertRaisesRegex(ValueError, "huella"):
                score(*inputs, out, now=CLOSED)
            write_json(out / ".infer-step-00014838.receipt.json", sha256_file(pred))
            with self.assertRaisesRegex(ValueError, "MLflow"):
                score(*inputs, out, now=CLOSED)
            track(out)
            result = score(*inputs, out, now=CLOSED)
            self.assertEqual(result["decision"], "veto_pilot_on_this_release")
            self.assertFalse(result["gates"]["lower_mae_than_persistence"])
