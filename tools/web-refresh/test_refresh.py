"""Exportación pública: sin imputación ni confusión entre hora publicada y UTC."""

import importlib.util
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

spec = importlib.util.spec_from_file_location("refresh", Path(__file__).with_name("refresh.py"))
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class RefreshTests(unittest.TestCase):
    def chart(self, title="CARABAYLLO", value="12"):
        return f"""Highcharts.chart('chart', {{title: {{text: '{title}'}},
          xAxis: {{categories: ['22/11/202623:00:','23/11/202600:00:']}},
          series: [{{name: 'Material Particulado menor a 2.5 micras (PM2.5)',
          data: [{value}, null]}}]}});""".encode("latin-1")

    def test_verifica_estacion_contaminante_y_conserva_nulos(self):
        points = refresh.parse_chart(self.chart(), "CARABAYLLO")
        self.assertEqual(points[datetime(2026, 11, 22, 23)], 12)
        self.assertIsNone(points[datetime(2026, 11, 23)])
        for payload in (self.chart("SAN BORJA"), self.chart(value="nan")):
            with self.assertRaises(ValueError):
                refresh.parse_chart(payload, "CARABAYLLO")
        with self.assertRaises(ValueError):
            refresh.parse_chart(self.chart().replace(b"PM2.5", b"PM10"), "CARABAYLLO")

    def test_rechaza_etiquetas_duplicadas(self):
        raw = self.chart().replace(b"23/11/202600:00:", b"22/11/202623:00:")
        with self.assertRaises(ValueError):
            refresh.parse_chart(raw, "CARABAYLLO")

    def test_alinea_24_entradas_y_seis_objetivos_sin_horas_futuras_inventadas(self):
        origin = datetime(2026, 11, 23, 0)
        points = {origin + timedelta(hours=i): float(i + 30) for i in range(-30, 1)}
        window = refresh.window_at(points, origin)
        self.assertEqual(window["history"], list(map(float, range(7, 31))))
        self.assertEqual(window["observed"], [None] * 6)
        self.assertEqual(window["origin"], "2026-11-23T00:00:00")
        self.assertEqual(window["target_times"][-1], "2026-11-23T06:00:00")
        self.assertTrue(refresh.eligible(window))
        del points[origin - timedelta(hours=3)]
        self.assertFalse(refresh.eligible(refresh.window_at(points, origin)))

    def test_no_combina_instrumentos_para_completar_una_historia(self):
        origin = datetime(2026, 11, 23)
        old = {origin - timedelta(hours=i): 10 for i in range(24)}
        new = {origin: 20}
        self.assertEqual(refresh.choose_series([("old", old), ("new", new)])[0], "old")
        self.assertFalse(refresh.eligible(refresh.window_at(new, origin)))

    def test_solo_exporta_resultados_del_checkpoint_corregido(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            window = refresh.window_at({}, datetime(2026, 11, 22, 21))
            window["history"] = list(range(24))
            snapshot = {"stations": {"SAN_BORJA": {"source_code": "00112270", "windows": [window]}}}
            refresh.write_json(root / "capture.json", snapshot)
            refresh.write_history(root, snapshot)
            fields = dict(
                window_id=["SAN_BORJA/" + window["origin"]],
                predicted=[range(6)],
                forecast_hour=np.arange(1, 7),
                checkpoint_sha256=refresh.CHECKPOINT,
                history_sha256=refresh.digest(root / "history.npz"),
                correction_sha256=refresh.CORRECTION,
            )
            for key in ("history_sha256", "checkpoint_sha256", "correction_sha256"):
                np.savez(root / "predictions.npz", **(fields | {key: "0" * 64}))
                with self.assertRaises(ValueError):
                    refresh.export(root)
            np.savez(root / "predictions.npz", **fields)
            refresh.export(root)
            result = json.loads((root / "actual.json").read_text())
            self.assertEqual(result["model"]["name"], "Gemma 3 1B")
            self.assertEqual(
                result["stations"]["SAN_BORJA"]["windows"][0]["forecast"], list(range(6))
            )

    def test_programacion_no_se_adelanta_a_las_nueve_de_lima(self):
        self.assertFalse(refresh.started("2026-11-23T13:59:59+00:00", "2026-11-23T14:00:00Z"))
        self.assertTrue(refresh.started("2026-11-23T14:00:00+00:00", "2026-11-23T14:00:00Z"))


if __name__ == "__main__":
    unittest.main()
