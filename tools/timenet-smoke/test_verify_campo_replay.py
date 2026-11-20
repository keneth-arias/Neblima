"""Casos límite del cotejo retrospectivo de Campo de Marte."""

import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from verify_campo_replay import compare, compare_calibration, partitions, verify_live_predictions


class CampoReplayTest(unittest.TestCase):
    def test_umbral_exige_la_estacion_y_el_percentil_del_sello(self):
        from verify_campo_replay import METADATA, RESULTS, frozen_threshold, read

        seal = read(METADATA / "seleccion-concentracion-lima-v1/sello.json")
        protocol = read(RESULTS / "recalibracion/protocolo.json")
        self.assertEqual(frozen_threshold(seal, protocol), 34.95)
        with self.assertRaisesRegex(ValueError, "umbral"):
            frozen_threshold(seal, dict(protocol, threshold_ug_m3=35.3875))
        with self.assertRaisesRegex(ValueError, "estación"):
            frozen_threshold(seal, dict(protocol, station="otra"))
        with self.assertRaisesRegex(ValueError, "huella"):
            frozen_threshold(dict(seal, thresholds_sha256="0" * 64), protocol)

    def test_separacion_usa_toda_la_historia_y_seis_objetivos(self):
        train, evaluation = partitions(np.array([93, 94, 122, 123]), 100)
        self.assertEqual(train.tolist(), [True, False, False, False])
        self.assertEqual(evaluation.tolist(), [False, False, False, True])

    def test_cotejo_rechaza_cambios_numericos_o_de_forma(self):
        compare([1.0, 2.0], [1.0, 2.0])
        for other in ([1.0, 2.01], [1.0], [1.0, float("nan")]):
            with self.subTest(other=other), self.assertRaises(ValueError):
                compare([1.0, 2.0], other)

    def test_concilia_denominadores_estratos_y_remuestreo(self):
        y = np.full((2, 6), 10.0)
        hours = np.array([0, 168])
        groups = np.zeros_like(y, dtype=int)
        original = (y - 2, y + 2)
        candidate = (y - 1, y + 1)

        def row(pairs, paired=False):
            result = {
                "pairs": pairs,
                "station_hours": pairs,
                "original": {"coverage": 1.0 if pairs else None, "width": 4.0 if pairs else None},
                "candidate": {"coverage": 1.0 if pairs else None, "width": 2.0 if pairs else None},
            }
            if paired:
                for key, diff in (("coverage", 0.0), ("width", -2.0)):
                    result["paired_" + key] = {
                        "blocks": 2 if pairs else 0,
                        "difference": diff if pairs else None,
                        "ci95": [diff, diff] if pairs else None,
                    }
            return result

        report = {
            "overall": row(12, True),
            "observed_high": row(12, True),
            "by_horizon": [row(2) for _ in range(6)],
            "high_by_horizon": [row(2) for _ in range(6)],
            "by_forecast_quartile": [row(12), row(0), row(0), row(0)],
            "gates": {
                "pooled_coverage": False,
                "smaller_mean_width": True,
                "retains_high_coverage": True,
            },
            "decision": "reject_candidate",
        }

        def verify(r, threshold=10):
            compare_calibration(r, hours, y, original, candidate, groups, threshold)

        verify(report)
        for path in (
            ("observed_high", "station_hours"),
            ("by_horizon", 0, "pairs"),
            ("overall", "paired_width", "ci95"),
            ("observed_high", "paired_coverage", "blocks"),
            ("by_forecast_quartile", 0, "candidate", "width"),
        ):
            altered = deepcopy(report)
            parent = altered
            for field in path[:-1]:
                parent = parent[field]
            parent[path[-1]] = [0, 0] if path[-1] == "ci95" else 0
            with self.subTest(path=path), self.assertRaises(ValueError):
                verify(altered)
        report["observed_high"] = row(0, True)
        report["high_by_horizon"] = [row(0) for _ in range(6)]
        report["gates"]["retains_high_coverage"] = None
        report["decision"] = "inconclusive"
        verify(report, 11)
        report["decision"] = "reject_candidate"
        with self.assertRaises(ValueError):
            verify(report, 11)

    def test_concilia_archivo_operativo_y_recibo_antes_de_aceptar_la_emision(self):
        with TemporaryDirectory() as tmp:
            work = Path(tmp)
            output = work / "predicciones.npz"
            origin = "2026-01-01T00:00:00"
            ck = "c" * 64
            np.savez(
                output,
                window_id=["112194/" + origin],
                forecast_hour=np.arange(1, 7),
                predicted=np.arange(1, 7).reshape(1, 6),
                checkpoint_sha256=ck,
            )
            record = {
                "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "bundle_sha256": "b" * 64,
                "checkpoint_sha256": ck,
                "run_id": "run",
                "image": "test",
            }
            (work / "inferencia.json").write_text(json.dumps(record))
            issue = dict(
                record,
                origin=origin,
                hours=[
                    {
                        "station_label": f"2026-01-01T{i:02}:00:00",
                        "qwen": i,
                        "lower80": i - 1,
                        "upper80": i + 1,
                    }
                    for i in range(1, 7)
                ],
            )
            q = [[-1] * 6, [1] * 6]
            verify_live_predictions(work, issue, q)
            wrong = deepcopy(issue)
            wrong["hours"][0]["qwen"] += 1
            with self.assertRaises(ValueError):
                verify_live_predictions(work, wrong, q)
            output.write_bytes(b"archivo truncado")
            with self.assertRaises(ValueError):
                verify_live_predictions(work, issue, q)
            output.unlink()
            with self.assertRaises(FileNotFoundError):
                verify_live_predictions(work, issue, q)
