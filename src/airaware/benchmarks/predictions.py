"""Predicciones pareadas por window_id/forecast_hour sobre objetivos idénticos."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from airaware.benchmarks.features import DesignRow
from airaware.benchmarks.metrics import Prediction, mae
from airaware.benchmarks.model import TabularPredictor


def predictions_from(predictor: TabularPredictor, rows: Sequence[DesignRow]) -> list[Prediction]:
    """Convierte las salidas del predictor en predicciones pareadas con su objetivo."""
    values = predictor.predict(rows)
    if len(values) != len(rows):
        raise ValueError("El predictor devolvió una cantidad distinta de predicciones")
    predictions = []
    for row, value in zip(rows, values, strict=True):
        if not math.isfinite(value):
            raise ValueError(f"Predicción no finita para {row.window_id}")
        predictions.append(
            Prediction(
                window_id=row.window_id,
                station=row.station,
                forecast_hour=row.forecast_hour,
                target=row.target,
                prediction=value,
                label=row.label,
            )
        )
    return predictions


def _index(preds: Sequence[Prediction]) -> dict[tuple[str, int], Prediction]:
    index: dict[tuple[str, int], Prediction] = {}
    for row in preds:
        key = (row.window_id, row.forecast_hour)
        if key in index:
            raise ValueError(f"Predicciones duplicadas para {key}")
        index[key] = row
    return index


def paired_join(
    left: Sequence[Prediction],
    right: Sequence[Prediction],
) -> list[tuple[Prediction, Prediction]]:
    """Unión uno a uno por window_id/forecast_hour; exige objetivos exactamente iguales."""
    left_index = _index(left)
    right_index = _index(right)
    if left_index.keys() != right_index.keys():
        raise ValueError("La cobertura difiere: cada objetivo requiere una clave común")
    joined = []
    for key in sorted(left_index):
        first, second = left_index[key], right_index[key]
        if first.station != second.station:
            raise ValueError(f"La estación difiere para {key}: {first.station} != {second.station}")
        if first.target != second.target:
            raise ValueError(
                f"Objetivos discordantes para {key}: {first.target} != {second.target}"
            )
        joined.append((first, second))
    return joined


@dataclass(frozen=True, slots=True)
class PairedEvaluation:
    n: int
    mae_left: float
    mae_right: float
    difference: float


def paired_evaluation(left: Sequence[Prediction], right: Sequence[Prediction]) -> PairedEvaluation:
    """Compara dos modelos sobre las mismas claves, estaciones y objetivos."""
    joined = paired_join(left, right)
    if not joined:
        raise ValueError("La comparación exige al menos una clave común")
    first = [row for row, _ in joined]
    second = [row for _, row in joined]
    left_mae = mae(first)
    right_mae = mae(second)
    return PairedEvaluation(
        n=len(joined),
        mae_left=left_mae,
        mae_right=right_mae,
        difference=right_mae - left_mae,
    )
