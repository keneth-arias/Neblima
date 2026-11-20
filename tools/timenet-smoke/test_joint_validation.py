"""Controles del emparejamiento de ambas salidas y la referencia independiente."""

import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import numpy as np
from joint_validation import paired_table, read_predictions, summarize, training_events


class JointValidationTest(unittest.TestCase):
    def test_record_only_unterminated_nul_padding_after_a_complete_event(self):
        with TemporaryDirectory() as tmp:
            log = Path(tmp) / "events-1.jsonl"
            prefix = b'{"step":1}\n'
            tails = {}
            log.write_bytes(prefix + bytes(17))
            self.assertEqual(list(training_events(log, tails)), [{"step": 1}])
            self.assertEqual(
                tails,
                {
                    log.name: {
                        "nul_bytes": 17,
                        "sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
                    }
                },
            )
            for bad in [b"", b'{"step":', bytes(17) + b'\n{"step":2}\n', bytes(2) + b"x"]:
                with self.subTest(bad=bad):
                    log.write_bytes(prefix + bad if bad else bytes(17))
                    with self.assertRaises(ValueError):
                        list(training_events(log, {}))

    def setUp(self):
        self.ids = np.array(["a", "c", "d"])
        self.channels = np.array(["pm25", "pm10"])
        self.y = np.arange(36, dtype=float).reshape(3, 6, 2)
        self.x = np.ones((3, 24, 2))
        self.x[:, -1, 1] = 10
        self.data = dict(
            window_id=self.ids,
            station_key=np.array(["x", "x", "z"]),
            origin_hour=np.array([100, 101, 102]),
            targets=self.y,
            history=self.x,
            channels=self.channels,
        )
        self.pred = dict(
            window_id=self.ids[::-1],
            forecast_hour=np.arange(1, 7),
            channels=self.channels,
            predicted=(self.y + 2)[::-1],
            checkpoint_sha256="c",
            scaler_sha256="s",
            view="first",
        )

    def test_align_and_score_in_original_units(self):
        a = read_predictions(self.pred, self.ids, "first", "c", "s")
        with duckdb.connect() as db:
            table = paired_table(
                self.data, a, self.y + np.array([1, 4]), {"x": [0, 0], "z": [0, 0]}
            )
            db.register("pairs", table)
            score = summarize(db)
            self.assertEqual(score["station_target_hours"], 13)
            g = score["groups"]["channel"]
            for row in g:
                delta = {"pm25": -1, "pm10": 2}[row["channel"]]
                self.assertEqual(row["targets"], 18)
                self.assertEqual(row["delta_b_a"], delta)
            self.assertEqual(table["persistence"].to_pylist()[:2], [1, 10])

    def test_reject_invalid_identity_horizons_and_keys(self):
        for update in (
            {"window_id": self.ids[[0, 0, 1]]},
            {"window_id": np.array(["a", "c", "e"])},
            {"forecast_hour": np.arange(6)},
            {"channels": self.channels[::-1]},
            {"view": "both"},
            {"checkpoint_sha256": "x"},
            {"predicted": self.y[:1]},
        ):
            with self.subTest(update=tuple(update)), self.assertRaises(ValueError):
                read_predictions({**self.pred, **update}, self.ids, "first", "c", "s")

    def test_reject_duplicate_keys_in_scoring(self):
        table = paired_table(self.data, self.y, self.y, {"x": [0, 0], "z": [0, 0]})
        import pyarrow as pa

        with duckdb.connect() as db:
            db.register("pairs", pa.concat_tables([table, table.slice(0, 1)]))
            with self.assertRaisesRegex(ValueError, "clave"):
                summarize(db)
