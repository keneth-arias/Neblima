import math
import tempfile
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path

from openpyxl import Workbook
from review import clock_value, date_value, iter_records, numeric_value, parameter_family


class InterpretationTests(unittest.TestCase):
    def test_values_preserve_censoring_zero_and_nonfinite(self):
        self.assertEqual(numeric_value("<L.C.")[0], "censored")
        self.assertEqual(numeric_value("<0.01")[0], "censored")
        self.assertEqual(numeric_value("-")[0], "missing")
        self.assertEqual(numeric_value("0"), ("finite", 0.0))
        self.assertEqual(numeric_value(-2), ("finite", -2.0))
        self.assertEqual(numeric_value(math.inf)[0], "nonfinite")
        self.assertEqual(numeric_value("1,2")[0], "unparsed")
        self.assertEqual(numeric_value("ND")[0], "unparsed")
        self.assertEqual(numeric_value("N.D.")[0], "unparsed")

    def test_dates_use_explicit_workbook_epoch_and_keep_ambiguous_text_unknown(self):
        epoch = datetime(1899, 12, 30)
        self.assertEqual(str(date_value(datetime(2023, 1, 1), epoch)[0]), "2023-01-01")
        self.assertEqual(str(date_value(44927, epoch)[0]), "2023-01-01")
        self.assertIsNone(date_value("2/8/2019", epoch)[0])
        self.assertEqual(str(date_value("31/8/2019", epoch)[0]), "2019-08-31")
        self.assertIsNone(date_value("-", epoch)[0])

    def test_clock_is_not_inferred_from_date_only_or_24_hour_duration(self):
        self.assertEqual(clock_value(time(3, 0))[0], time(3, 0))
        self.assertEqual(clock_value(0.5)[0], time(12, 0))
        self.assertEqual(clock_value("03:30")[0], time(3, 30))
        self.assertIsNone(clock_value("24:00:00")[0])
        self.assertIsNone(clock_value("1899-12-31")[0])
        self.assertIsNone(clock_value(timedelta(hours=24))[0])

    def test_parameter_typo_does_not_become_confirmed_pm25(self):
        self.assertEqual(parameter_family("Material Particulado PM2,5"), "pm25")
        self.assertEqual(parameter_family("Partículas PM10"), "pm10")
        self.assertEqual(parameter_family("Menor a 25 micras (PM2,5)"), "pm25_ambiguous")
        self.assertEqual(parameter_family("Partículas PM25"), "pm25_ambiguous")

    def test_metals_and_filter_weights_are_not_total_particle_concentration(self):
        self.assertEqual(parameter_family("Plomo - PM10"), "pm_related_non_target")
        self.assertEqual(parameter_family("Estroncio en PM10"), "pm_related_non_target")
        self.assertEqual(parameter_family("Peso inicial filtro PM2.5"), "pm_related_non_target")
        self.assertEqual(parameter_family("Determinación de peso PM10"), "pm_related_non_target")
        self.assertEqual(parameter_family("Concentración de partículas en PM10"), "pm10")

    def test_reader_preserves_types_formula_and_row_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "demo.xlsx"
            w = Workbook()
            s = w.active
            s.title = "Aire"
            s.append(["Fecha inicio", "Hora inicio", "Valor", "Parámetro"])
            s.append([datetime(2024, 1, 1), time(3, 0), "=1+1", "PM10"])
            w.save(p)
            w.close()
            rows = list(iter_records(p))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["row"], 2)
            self.assertEqual(rows[0]["formula_fields"], ["Valor"])
            self.assertEqual(rows[0]["values"]["Valor"], "=1+1")
            self.assertIsInstance(rows[0]["values"]["Fecha inicio"], datetime)


class EndToEndTests(unittest.TestCase):
    def test_analysis_counts_fixture_without_modifying_original(self):
        import hashlib
        import json

        from analyze import analyze

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / "input.xlsx"
            w = Workbook()
            s = w.active
            s.title = "Aire"
            s.append(
                [
                    "Número de informe",
                    "Nombre de la Evaluación",
                    "Nombre del punto",
                    "Este",
                    "Norte",
                    "Altitud",
                    "Zona",
                    "Datum",
                    "Tipo de muestra",
                    "Tipo de análisis",
                    "Periodo",
                    "Fecha inicio",
                    "Hora inicio",
                    "Fecha fin",
                    "Hora fin",
                    "Valor",
                    "Parámetro",
                    "Unidad de medida",
                ]
            )
            for hour, value in [(0, 1), (0, 1), (1, 2), (1, 3), (2, "<L.C.")]:
                s.append(
                    [
                        "R1",
                        "Lima",
                        "CA-1",
                        1,
                        2,
                        3,
                        18,
                        "WGS84",
                        "Simple",
                        "Partículas",
                        "1 hora",
                        datetime(2024, 1, 1),
                        time(hour, 0),
                        "-",
                        "-",
                        value,
                        "PM10",
                        "µg/m3",
                    ]
                )
            w.save(p)
            w.close()
            before = hashlib.sha256(p.read_bytes()).hexdigest()
            receipt = root / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {"files": [{"source_id": "fixture", "local_path": str(p), "sha256": before}]}
                )
            )
            output = root / "reports"
            analyze(receipt, output)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["sources"][0]["rows"], 5)
            self.assertEqual(summary["sources"][0]["decoded_duplicate_extra_rows"], 1)
            self.assertEqual(summary["sources"][0]["censored_values"], 1)
            self.assertEqual(sum(r["distinct_hour_slots"] for r in summary["coverage"]), 1)
            self.assertTrue(all(r["scientific_valid_windows"] is None for r in summary["windows"]))
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), before)


class GeographicAndTimeTests(unittest.TestCase):
    def test_climatic_text_is_not_a_lima_location(self):
        from analyze import converted

        record = {
            "values": {
                "Descripción de ubicación": "Estudio climático en Cusco",
                "Fecha inicio": datetime(2024, 1, 1),
                "Hora inicio": time(1),
            },
            "formula_fields": [],
            "error_fields": [],
            "epoch": datetime(1899, 12, 30),
            "sheet": "Aire",
            "row": 2,
        }
        r = converted(record, {"source_id": "fixture", "sha256": "0" * 64})
        self.assertFalse(r["candidate_lima"])
        record["values"]["Descripción de ubicación"] = "Distrito La Victoria, Lima"
        self.assertTrue(
            converted(record, {"source_id": "fixture", "sha256": "0" * 64})["candidate_lima"]
        )

    def test_conflicting_clock_embedded_in_date_is_kept_unresolved(self):
        from analyze import converted

        record = {
            "values": {"Fecha inicio": datetime(2024, 1, 1, 12), "Hora inicio": time(11)},
            "formula_fields": [],
            "error_fields": [],
            "epoch": datetime(1899, 12, 30),
            "sheet": "Aire",
            "row": 2,
        }
        r = converted(record, {"source_id": "fixture", "sha256": "0" * 64})
        self.assertIsNone(r["start"])
        self.assertEqual(r["clock_status"], "date_hour_conflict")


if __name__ == "__main__":
    unittest.main()
