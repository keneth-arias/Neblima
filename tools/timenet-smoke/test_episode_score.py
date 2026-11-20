"""Comprobar el denominador y el estrato de cada medida horaria."""

from unittest import TestCase

import numpy as np
from episode_score import scores


class EpisodeScoreTest(TestCase):
    def test_incomplete_follow_up_and_active_history(self):
        y = np.array([[1.0, 2, 3, 4, 5, 6], [1.0, 2, 3, 4, 5, np.nan]])
        table = scores(
            y,
            np.ones_like(y),
            np.zeros_like(y),
            np.full_like(y, 4),
            np.array([5.0, 5.0]),
            np.array([0.0, 6.0]),
            np.array([0.75, 0.5]),
            np.array([1, -1]),
        )
        self.assertEqual(table["all"]["targets"], 11)
        self.assertEqual(table["high"]["targets"], 3)
        self.assertAlmostEqual(table["all"]["coverage"], 8 / 11)
        self.assertEqual(table["by_horizon"][-1]["targets"], 1)
        self.assertEqual(table["event"]["below"]["brier"], 0.25**2)
        self.assertIsNone(table["event"]["active"]["brier"])
        self.assertEqual(table["event"]["ineligible"], 1)
