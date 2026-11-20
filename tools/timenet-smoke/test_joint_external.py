"""El reloj nativo y la separación de historias y objetivos de #88."""

import unittest

import numpy as np
from joint_external import external_arrays
from joint_validation import paired_table


class ExternalTest(unittest.TestCase):
    def test_native_clock_and_first_view(self):
        group = (("SITIO", "001", None, None), np.arange(30), np.arange(60).reshape(30, 2), [0])
        data, inputs = external_arrays("senamhi_horario", [group])
        self.assertEqual(set(inputs), {"history", "channels", "window_id"})
        np.testing.assert_array_equal(inputs["history"][0], group[2][:24])
        np.testing.assert_array_equal(data["targets"][0], group[2][24:])
        self.assertEqual(data["origin_hour"].tolist(), [23])
        table = paired_table(
            data | inputs, data["targets"], data["targets"], {"001": [0, 0]}, tz=None
        )
        self.assertIsNone(table["target_at"].type.tz)
        self.assertEqual(table["target_at"][0].as_py().hour, 0)
        self.assertEqual(table["target_at"][0].as_py().day, 2)

    def test_provider_codes_share_only_the_historical_site_threshold(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        import pyarrow.parquet as pq
        from export_senamhi import sha256_file
        from external_pm import digest_key
        from joint_external import score
        from joint_windows import write_json

        source = "senamhi_horario"
        matrices, inputs = external_arrays(
            source,
            [
                (("SITIO", code, None, None), np.arange(30), np.arange(60).reshape(30, 2), [0])
                for code in ("001", "009")
            ],
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            np.savez(root / "inputs.npz", **inputs)
            np.savez(root / "observed.npz", **matrices)
            ids_sha = digest_key(inputs["window_id"].tolist())
            write_json(
                root / "manifest.json",
                dict(
                    source=source,
                    timef_sha256="dataset",
                    ordered_ids_sha256=ids_sha,
                    files={p.name: sha256_file(p) for p in root.glob("*.npz")},
                ),
            )
            scaler = root / "scaler.json"
            write_json(scaler, {"p95": {"hist": [58.0, 99.0]}})
            frozen = root / "frozen.json"
            write_json(
                frozen,
                dict(
                    scaler_sha256=sha256_file(scaler),
                    models={view: {"checkpoint_sha256": view} for view in ("first", "both")},
                ),
            )
            for view, error in (("first", 1), ("both", 2)):
                np.savez(
                    root / f"{source}-{view}.npz",
                    window_id=inputs["window_id"],
                    predicted=matrices["targets"] + error,
                    channels=inputs["channels"],
                    forecast_hour=np.arange(1, 7),
                    view=view,
                    checkpoint_sha256=view,
                    scaler_sha256=sha256_file(scaler),
                )
            cohorts = {
                "historico": {"stations": [{"site": "SITIO", "code": "hist"}]},
                source: {
                    "manifest_sha256": "dataset",
                    "stations": [
                        {"site": "SITIO", "code": code, "test": 1} for code in ("001", "009")
                    ],
                    "verified": {"split_ids_sha256": {"test": ids_sha}, "target_values": 24},
                },
            }
            output = root / "scores"
            with (
                patch("joint_external.cohort", side_effect=cohorts.__getitem__),
                patch("joint_external.MODELS", frozen),
            ):
                score(source, root, root, scaler, output)
            stats = json.loads((output / "metrics.json").read_text())
            self.assertEqual(stats["station_target_hours"], 12)
            self.assertEqual([r["targets"] for r in stats["groups"]["high"]], [2])
            self.assertTrue(all(r["delta_b_a"] == 1 for r in stats["groups"]["station_horizon"]))
            self.assertEqual(
                set(pq.read_table(output / "paired.parquet")["source"].to_pylist()), {source}
            )
