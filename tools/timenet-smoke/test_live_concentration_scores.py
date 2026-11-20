"""Comparar la primera versión y las correcciones solo cuando ya han llegado."""

import hashlib
import json
import unittest
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from live_concentration_scores import report, summarize
from station_receipts import chart_url, register
from test_station_receipts import chart


def issue(origin="2026-11-20T15:00:00", issued="2026-11-20T20:30:00+00:00"):
    start = datetime.fromisoformat(origin)
    return {
        "mode": "private_live_shadow",
        "station": "Campo de Marte / 112194",
        "unit": "ug/m3",
        "checkpoint_sha256": "a" * 64,
        "origin": origin,
        "issued_at_utc": issued,
        "input_cutoff_utc": issued,
        "last_ug_m3": 10,
        "hours": [
            {
                "station_label": (start + timedelta(hours=i)).isoformat(),
                "qwen": 13,
                "lower80": 11,
                "upper80": 15,
            }
            for i in range(1, 7)
        ],
    }


def reading(hour, at, value):
    return {"station_hour": f"2026-11-20T{hour}:00:00", "seen_utc": at, "value": value}


class LiveScoresTest(unittest.TestCase):
    def test_recepcion_correccion_retiro_y_objetivo_conocido(self):
        forecast = issue()
        first = "2026-11-20T21:00:00+00:00"
        second = "2026-11-20T22:00:00+00:00"
        later = "2026-11-20T23:00:00+00:00"
        changes = [
            reading(16, first, 15),
            reading(17, first, 12),
            reading(18, forecast["issued_at_utc"], 10),
            reading(16, second, 21),
            reading(17, second, None),
            reading(18, second, 20),
            reading(16, later, 100),
        ]
        r = summarize([forecast], list(reversed(changes)), second)
        self.assertEqual(r["issued"], 1)
        self.assertEqual(
            r["counts"],
            {"available_before_issue": 1, "awaiting_first": 3, "observed": 1, "withdrawn": 1},
        )
        self.assertEqual(
            r["overall"]["first"],
            {
                "pairs": 2,
                "distinct_target_hours": 2,
                "qwen_mae": 1.5,
                "persistence_mae": 3.5,
                "coverage80": 1.0,
                "mean_width80": 4,
            },
        )
        self.assertEqual(r["overall"]["latest"]["qwen_mae"], 8)
        self.assertEqual(r["overall"]["latest"]["persistence_mae"], 11)
        self.assertEqual(r["overall"]["latest"]["coverage80"], 0)
        self.assertEqual(r["overall"]["mean_seconds_to_first_receipt"], 1800)
        self.assertEqual(r["by_horizon"][1]["first"]["pairs"], 1)
        self.assertIsNone(r["by_horizon"][1]["latest"]["qwen_mae"])
        self.assertEqual(r["by_horizon"][0]["latest"]["pairs"], 1)
        self.assertEqual([s["forecast_hour"] for s in r["by_horizon"]], list(range(1, 7)))
        early = summarize([forecast], changes, first)
        self.assertEqual(early["overall"]["latest"], early["overall"]["first"])
        self.assertEqual(summarize([forecast], changes, "2026-11-20T20:00:00+00:00")["issued"], 0)

    def test_horas_compartidas_y_reloj_de_recepcion(self):
        r = summarize(
            [issue(), issue("2026-11-20T16:00:00", "2026-11-20T20:45:00+00:00")],
            [reading(17, "2026-11-20T16:00:00-05:00", 13)],
            "2026-11-20T21:00:00+00:00",
        )
        self.assertEqual(r["overall"]["first"]["pairs"], 2)
        self.assertEqual(r["overall"]["first"]["distinct_target_hours"], 1)
        self.assertEqual(r["overall"]["mean_seconds_to_first_receipt"], 1350)

    def test_rechaza_datos_incompatibles(self):
        good = issue()
        cutoff = "2026-11-20T22:00:00+00:00"
        changed = deepcopy(good)
        changed["hours"][1]["station_label"] = good["hours"][0]["station_label"]
        for forecasts, readings, through in (
            ([changed], [], cutoff),
            ([good, good], [], cutoff),
            ([good], [], cutoff[:-6]),
            ([good], [reading(16, cutoff, 1), reading(16, cutoff, 2)], cutoff),
            ([dict(good, last_ug_m3=float("inf"))], [], cutoff),
            ([dict(good, unit="ppm")], [], cutoff),
        ):
            with self.subTest(through=through), self.assertRaises(ValueError):
                summarize(forecasts, readings, through)

    def test_informe_enlaza_recibos_al_corte_y_ventana_emitida(self):
        with TemporaryDirectory() as tmp:
            receipts = Path(tmp) / "recibos"
            issues = Path(tmp) / "emisiones"
            issues.mkdir()
            forecast = issue()

            def capture(at, values):
                data = chart(values)
                return register(
                    receipts,
                    data,
                    {
                        "recuperado_utc": at,
                        "url": chart_url(date(2026, 11, 20), date(2026, 11, 20)),
                        "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "http_status": 200,
                    },
                )

            at = forecast["input_cutoff_utc"]
            first = capture(at, [(15, 10)])
            digest = hashlib.sha256((first / "receipt.json").read_bytes()).hexdigest()
            forecast["receipt_sha256"] = digest
            path = issues / "2026112015.json"
            path.write_text(json.dumps(forecast))
            after = "2026-11-20T21:30:00+00:00"
            capture(after, [(15, 10), (16, 15)])
            result = report(issues, receipts, at)
            self.assertEqual(result["source_receipts_sha256"], [digest])
            self.assertEqual(
                result["issuance_sha256"], [hashlib.sha256(path.read_bytes()).hexdigest()]
            )
            self.assertEqual(result["counts"]["awaiting_first"], 6)
            self.assertEqual(report(issues, receipts, after)["overall"]["first"]["qwen_mae"], 2)
            bad = dict(forecast, last_ug_m3=99)
            path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, "persistencia"):
                report(issues, receipts, after)
            bad = dict(forecast, origin="2026-11-20T14:00:00")
            path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, "persistencia"):
                report(issues, receipts, after)
            forecast["receipt_sha256"] = "0" * 64
            path.write_text(json.dumps(forecast))
            with self.assertRaisesRegex(ValueError, "recibo"):
                report(issues, receipts, after)
            with self.assertRaisesRegex(ValueError, "carpeta"):
                report(issues.parent / "ausente", receipts, at)
