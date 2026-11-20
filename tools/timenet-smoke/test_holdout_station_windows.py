"""Contrastar el corte reservado y la separación entre historias y soluciones."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import numpy as np
from holdout_station_windows import cohort, prepare
from station_receipts import chart_url, register


class HoldoutTest(TestCase):
    def test_out_of_float32_range_is_a_reasoned_abstention(self):
        start = datetime(2026, 11, 23, 1)
        values = [
            {
                "station_hour": (start + timedelta(hours=h)).isoformat(),
                "value": 1e39 if h == 23 else 4.0,
            }
            for h in range(24)
        ]
        protocol = {
            "origin_start_inclusive": "2026-11-24T00:00:00",
            "origin_stop_exclusive": "2026-12-01T00:00:00",
            "station_code": "112194",
            "history_hours": 24,
            "forecast_hours": 6,
            "schedule_hours": 168,
        }
        origins, ids, h, y = cohort(protocol, values)
        self.assertEqual(origins[0]["out_of_range_history_hours"], 1)
        self.assertEqual(origins[0]["missing_history_hours"], 0)
        self.assertFalse(origins[0]["eligible"])
        self.assertEqual((len(ids), h.shape, y.shape), (0, (0, 24), (0, 6)))

    def test_real_receipt_parser_blind_histories_and_locked_vintage(self):
        protocol = (
            Path(__file__).resolve().parents[2]
            / "configs/training/lima-prueba-futura-campo-marte-v1.json"
        )
        protocol_sha = hashlib.sha256(protocol.read_bytes()).hexdigest()
        config = json.loads(protocol.read_bytes())
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            seal = root / "seal.json"
            seal.write_text(
                json.dumps(
                    {
                        "version": "lima-concentracion-prueba-congelada-v1",
                        "protocol_sha256": protocol_sha,
                        "scope": config["scope"],
                        "head": "direct",
                        "checkpoint_sha256": "c" * 64,
                        "base_weights_sha256": "b" * 64,
                        "image": config["image"],
                        "seed": 27,
                        "thresholds_sha256": config["thresholds_sha256"],
                        "sealed_at_utc": "2026-11-21T10:00:00+00:00",
                    }
                )
            )
            seal_sha = hashlib.sha256(seal.read_bytes()).hexdigest()
            receipts = root / "snapshots"
            output = root / "cohort"
            vintage = datetime.fromisoformat(config["observation_vintage_utc"])

            def run(now=vintage):
                return prepare(protocol, protocol_sha, seal, seal_sha, receipts, output, now)

            with self.assertRaisesRegex(ValueError, "apertura"):
                run(vintage - timedelta(seconds=1))
            self.assertFalse(output.exists())
            original = json.loads(seal.read_bytes())
            wrong = root / "sello-ajeno.json"
            for item in ({"seed": 28}, {"thresholds_sha256": "0" * 64}):
                wrong.write_text(json.dumps({**original, **item}))
                with self.assertRaisesRegex(ValueError, "incompatibles"):
                    prepare(
                        protocol,
                        protocol_sha,
                        wrong,
                        hashlib.sha256(wrong.read_bytes()).hexdigest(),
                        receipts,
                        output,
                        vintage,
                    )
            receipts.mkdir()
            empty = prepare(
                protocol, protocol_sha, seal, seal_sha, receipts, root / "empty", vintage
            )
            self.assertEqual(
                (empty["origins"], empty["eligible_histories"], empty["source_receipts"]),
                (168, 0, []),
            )
            start = datetime(2026, 11, 23, 1)

            def record(items, arrival):
                cats = ",".join(
                    f"'{(start + timedelta(hours=h)):%d/%m/%Y%H}:00:'" for h, _ in items
                )
                values = ",".join("null" if v is None else str(v) for _, v in items)
                html = (
                    "Highcharts.chart('container',{title:{text:'CAMPO DE MARTE'},"
                    f"xAxis:{{categories:[{cats}]}}, "
                    "series:[{name:'Material Particulado menor a 2.5 micras (PM2.5)',"
                    f"data:[{values}]}}]}})"
                ).encode()
                register(
                    receipts,
                    html,
                    {
                        "url": chart_url(date(2026, 11, 23), date(2026, 11, 24)),
                        "recuperado_utc": arrival.isoformat(),
                        "bytes": len(html),
                        "sha256": hashlib.sha256(html).hexdigest(),
                        "http_status": 200,
                    },
                )

            record([(h, h) for h in range(31)], datetime(2026, 11, 25, 12, tzinfo=UTC))
            record([(24, None)], vintage)
            record([(23, 1000), (24, 2000)], vintage + timedelta(seconds=1))
            receipt = run()
            self.assertEqual(receipt["origins"], 168)
            self.assertEqual(receipt["eligible_histories"], 1)
            self.assertEqual(receipt["complete_targets"], 0)
            self.assertEqual(len(receipt["source_receipts"]), 2)
            with np.load(output / "infer/data.npz", allow_pickle=False) as archive:
                self.assertEqual(set(archive.files), {"window_id", "history"})
                np.testing.assert_array_equal(archive["history"], [np.arange(24)])
                np.testing.assert_array_equal(archive["window_id"], ["112194/2026-11-24T00:00:00"])
            with np.load(output / "scoring/observed.npz", allow_pickle=False) as archive:
                np.testing.assert_equal(archive["observed"], [[np.nan, 25, 26, 27, 28, 29]])
            with self.assertRaises(FileExistsError):
                run()
