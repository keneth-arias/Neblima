"""Casos límite del cotejo retrospectivo de Campo de Marte."""

import unittest

import numpy as np
from verify_campo_replay import compare, partitions


class CampoReplayTest(unittest.TestCase):
    def test_separacion_usa_toda_la_historia_y_seis_objetivos(self):
        train, evaluation = partitions(np.array([93, 94, 122, 123]), 100)
        self.assertEqual(train.tolist(), [True, False, False, False])
        self.assertEqual(evaluation.tolist(), [False, False, False, True])

    def test_cotejo_rechaza_cambios_numericos_o_de_forma(self):
        compare([1.0, 2.0], [1.0, 2.0])
        for other in ([1.0, 2.01], [1.0], [1.0, float("nan")]):
            with self.subTest(other=other), self.assertRaises(ValueError):
                compare([1.0, 2.0], other)
