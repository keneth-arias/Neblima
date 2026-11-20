"""Verificar qué podía conocerse al recibir dos versiones de un gráfico local."""

import hashlib
import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from station_receipts import audit, chart_url, register


def chart(values):
    cats = ",".join(f"'20/11/2026{h:02}:00:'" for h, _ in values)
    obs = ",".join("null" if v is None else str(v) for _, v in values)
    return (
        "Highcharts.chart('container',{title:{text:'CAMPO DE MARTE'},"
        f"xAxis:{{categories:[{cats}]}}, "
        f"series:[{{name:'Material Particulado menor a 2.5 micras (PM2.5)',data:[{obs}]}}]}})"
    ).encode()


class ReceiptTest(TestCase):
    def record(self, root, hour, values, day=20):
        raw = chart(values)
        receipt = {
            "recuperado_utc": f"2026-11-20T{hour:02}:30:00+00:00",
            "url": chart_url(date(2026, 11, day), date(2026, 11, day)),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "http_status": None,
        }
        return register(root, raw, receipt)

    def test_new_missing_revised_and_withdrawn_hours_preserve_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.record(root, 8, [(3, 11), (4, None), (5, 9)])
            first = self.record(root, 12, [(3, 12), (4, 8), (5, None), (6, 9)])
            self.assertEqual(first, self.record(root, 12, [(3, 12), (4, 8), (5, None), (6, 9)]))
            self.record(root, 14, [], day=19)  # Otra fecha fuera del alcance de la captura.
            result = audit(root)
            self.assertEqual(result["snapshots"], 3)
            self.assertEqual(result["observation_timezone"], None)
            self.assertEqual(result["counts"], {"first_value": 4, "revision": 1, "withdrawn": 1})
            changes = result["changes"]
            row = next(r for r in changes if r["station_hour"] == "2026-11-20T06:00:00")
            self.assertIsNone(row["last_checked_without_value_utc"])
            self.assertEqual(row["previous_check_utc"], "2026-11-20T08:30:00+00:00")
            four = next(r for r in changes if r["station_hour"] == "2026-11-20T04:00:00")
            self.assertEqual(four["last_checked_without_value_utc"], "2026-11-20T08:30:00+00:00")
            coverage = result["coverage_by_station_hour"][row["station_hour"]]
            self.assertFalse(coverage["in_latest_query"])
            self.assertEqual(coverage["last_queried_utc"], "2026-11-20T12:30:00+00:00")
            self.assertIsNone(changes[0]["last_checked_without_value_utc"])
            self.assertEqual(changes[-2]["kind"], "withdrawn")

    def test_conflicts_invalid_hours_and_tampered_snapshot(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.record(root, 8, [(0, 4)])
            with self.assertRaisesRegex(ValueError, "conflicto"):
                self.record(root, 8, [(0, 6)])
            with self.assertRaisesRegex(ValueError, "[Hh]ora"):
                self.record(root, 9, [(3, 4), (3, 5)])
            with self.assertRaisesRegex(ValueError, "[Hh]ora"):
                self.record(root, 10, [(3, 4)], day=19)
            receipt = json.loads((path / "receipt.json").read_text())
            with self.assertRaisesRegex(ValueError, "fuente"):
                register(root, chart([(0, 4)]), {**receipt, "url": "https://example.org/data"})
            (path / "chart.html").write_text("alterado")
            with self.assertRaisesRegex(ValueError, "huella"):
                audit(root)

    def test_capture_failure_cannot_publish_a_snapshot(self):
        import subprocess
        from unittest.mock import patch

        from station_receipts import capture

        responses = [{"id": 1, "result": {}}, {"id": 2, "result": {"isError": True}}]
        result = subprocess.CompletedProcess([], 0, stdout="\n".join(map(json.dumps, responses)))
        with (
            TemporaryDirectory() as tmp,
            patch("station_receipts.subprocess.run", return_value=result),
        ):
            root = Path(tmp) / "recepciones"
            with self.assertRaisesRegex(ValueError, "Lightpanda"):
                capture(root)
            self.assertFalse(root.exists())

    def test_source_identity_must_match_measured_series(self):
        raw = chart([(0, 4)]).replace(b"(PM2.5)", b"(PM10)") + b"<!-- PM (PM2.5) -->"
        with TemporaryDirectory() as tmp:
            old = self.record(Path(tmp), 8, [(0, 4)])
            receipt = json.loads((old / "receipt.json").read_bytes())
            receipt.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            with self.assertRaisesRegex(ValueError, "contaminante"):
                register(Path(tmp), raw, receipt)

    def test_truncated_chart_does_not_withdraw_an_omitted_category(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.record(root, 8, [(0, 1), (1, 8)])
            self.record(root, 9, [(0, 1)])
            self.record(root, 10, [(0, 1), (1, 8), (2, 7)])
            result = audit(root)
            self.assertEqual(result["counts"], {"first_value": 3, "withdrawn": 0, "revision": 0})
            self.assertEqual(result["changes"][-1]["preceding_query_state"], "unlisted")
            cutoff = "2026-11-20T09:30:00+00:00"
            self.assertEqual(audit(root, through=cutoff)["snapshots"], 2)
