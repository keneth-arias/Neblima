"""Controles de ventanas de dos contaminantes y del corte cronológico."""

import unittest

import numpy as np
from external_pm import choose_cut, valid_starts


class ExternalPMTest(unittest.TestCase):
    def test_never_bridge_gap_or_missing_channel(self):
        times = np.r_[np.arange(31), np.arange(32, 62)]
        x = np.ones((len(times), 2))
        x[0, 1] = np.nan
        self.assertEqual(valid_starts(times, x).tolist(), [1, 31])

    def test_cut_minimizes_post_purge_ratio_without_shared_hours(self):
        starts = np.r_[np.arange(200), np.arange(110, 200)]
        cut = choose_cut(starts)

        def error(c):
            train = sum(starts + 29 < c)
            val = sum(starts >= c)
            return abs(train / (train + val) - 0.85) if train and val else 1

        self.assertEqual(error(cut), min(map(error, range(231))))
        self.assertLess(max(starts[starts + 29 < cut]) + 29, min(starts[starts >= cut]))

    def test_preserves_historical_window_id_from_release_28(self):
        from datetime import UTC, datetime

        from external_pm import historical_window_id, series_key

        station = "35170dbfe2a7135c1cecbae1e367374a284578533740ff5461d40fc764851e07"
        start = int(datetime(2018, 7, 3, 19, tzinfo=UTC).timestamp()) // 3600
        self.assertEqual(
            historical_window_id(series_key(station, "PM2_5", "PM2.5"), start),
            "0000556dd41f71b0a7d35273a9ddceea4feb121226a466b177ec738dfbaa937b",
        )

    def test_source_local_timef_roundtrip_and_eligibility(self):
        import json
        from datetime import datetime, timedelta
        from pathlib import Path
        from tempfile import TemporaryDirectory

        import pyarrow as pa
        import pyarrow.parquet as pq
        from external_pm import build
        from verify_external_pm import verify

        begin = datetime(2024, 6, 1)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for source in ("senamhi_horario", "openaq"):
                rows = []
                for i in range(66):
                    hour = begin + timedelta(hours=i)
                    for name, base in (("pm25", 0), ("pm10", 100)):
                        row = dict(
                            fuente=source,
                            sitio="Lima",
                            grupo="benchmark",
                            id_estacion="001",
                            id_sensor=name,
                            parametro=name,
                            unidad="µg/m³",
                            hora_nativa=hour,
                            observado_utc=hour if source == "openaq" else None,
                            valor=float(base + i),
                        )
                        rows.append(row)
                        if i == 0:
                            rows.append(row.copy())
                        if name == "pm10" and i == 30:
                            rows.append({**row, "valor": -1})
                        if i >= 61 and name == "pm25":
                            row["id_sensor"] = "reemplazo"
                data = root / (source + ".parquet")
                pq.write_table(pa.Table.from_pylist(rows), data)
                registry = root / source
                result = build(source, [data], registry, begin, begin + timedelta(days=3))
                (registry / "resumen.json").write_text(json.dumps(result))
                checked = verify(registry)
                self.assertEqual(set(checked.pop("split_ids_sha256")), {"test"})
                self.assertEqual(checked, {"tasks": 2, "history_values": 96, "target_values": 24})
