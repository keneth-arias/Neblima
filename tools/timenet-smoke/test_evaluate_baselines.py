"""Probar desfases, ajuste exclusivo de entrenamiento y métricas de referencias."""

from unittest import TestCase

import duckdb
from evaluate_baselines import FIT, METRICS, PREDICT


class BaselineTest(TestCase):
    def test_offsets_and_training_scale_ignore_held_out_values(self):
        with duckdb.connect() as db:
            db.execute("SET TimeZone='UTC'")
            db.execute("""
                CREATE TABLE grid AS
                SELECT 'a' AS series_id, TIMESTAMPTZ '2024-01-01 00:00:00+00'
                       + h * INTERVAL '1 hour' AS observed_at, h::DOUBLE AS value
                FROM range(100) AS hours(h)
            """)
            db.execute("""
                CREATE TABLE tasks AS SELECT 'v' AS window_id, 'a' AS series_id,
                   'lima' AS station_key, 'validation' AS split,
                   TIMESTAMPTZ '2024-01-04 00:00:00+00' AS origin_at,
                   TIMESTAMPTZ '2024-01-04 01:00:00+00' AS target_start
            """)
            db.execute("""
                CREATE TABLE targets AS SELECT 'v' AS window_id, 1 AS forecast_hour,
                       73.0::DOUBLE AS actual
            """)
            db.execute(FIT, ["2024-01-03 00:00:00+00"])
            db.execute("CREATE TABLE predictions AS " + PREDICT)
            row = db.execute("""
                SELECT persistence, daily, seasonal, scale, high_concentration
                FROM predictions
            """).fetchone()
            self.assertEqual(row[:4], (72.0, 49.0, 13.0, 24.0))
            self.assertTrue(row[4])
            db.execute("CREATE TABLE metrics AS " + METRICS)
            result = db.execute("""
                SELECT mae, rmse, mase, n, n_mase FROM metrics WHERE model='daily'
                    AND split='validation' AND station_key IS NULL AND forecast_hour IS NULL
                    AND season IS NULL AND high_concentration IS NULL
            """).fetchone()
            self.assertEqual(result, (24.0, 24.0, 1.0, 1, 1))

    def test_constant_training_scale_keeps_mase_undefined(self):
        with duckdb.connect() as db:
            db.execute("""
                CREATE TABLE predictions AS SELECT
                    'test' AS split, 'a' AS station_key, 1 AS forecast_hour,
                    'DJF' AS season, false AS high_concentration, 4.0 AS actual,
                    2.0 AS persistence, 2.0 AS daily, 2.0 AS seasonal, 0.0 AS scale
            """)
            row = db.execute(
                "SELECT mase, n_mase FROM (" + METRICS + ") WHERE model = 'persistence' LIMIT 1"
            ).fetchone()
            self.assertEqual(row, (None, 0))
