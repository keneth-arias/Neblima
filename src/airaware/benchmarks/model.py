"""Ajuste con selección en validación; el bloque de prueba no participa del ajuste."""

import importlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from airaware.benchmarks.features import DesignRow, Window, design_rows, vectorize
from airaware.benchmarks.processing import ProcessingStats, apply_station_offset


@dataclass(frozen=True, slots=True)
class FitSpec:
    """Parámetros LightGBM; la cantidad de iteraciones la elige la validación."""

    learning_rate: float = 0.1
    num_leaves: int = 15
    min_data_in_leaf: int = 10
    max_boosting_rounds: int = 300
    early_stopping_rounds: int = 20
    seed: int = 27


class TabularPredictor(Protocol):
    """Contrato mínimo inyectable: predice desde características crudas de la ventana."""

    @property
    def name(self) -> str: ...

    def predict(self, rows: Sequence[DesignRow]) -> list[float]: ...


@dataclass(frozen=True, slots=True)
class FitReport:
    predictor: TabularPredictor
    processing: ProcessingStats
    validation_mae: float
    chosen_rounds: int | None


def _rows(windows: Sequence[Window]) -> list[DesignRow]:
    return [row for window in windows for row in design_rows(window)]


def _validation_mae(predictor: TabularPredictor, rows: Sequence[DesignRow]) -> float:
    predictions = predictor.predict(rows)
    if len(predictions) != len(rows):
        raise ValueError("El predictor devolvió una cantidad distinta de predicciones")
    return math.fsum(
        abs(prediction - row.target) for prediction, row in zip(predictions, rows, strict=True)
    ) / len(rows)


@dataclass(frozen=True, slots=True)
class MeanPredictor:
    """Doble mínimo documentado: media global o media por horizonte del entrenamiento."""

    name: str
    values: dict[int, float]

    def predict(self, rows: Sequence[DesignRow]) -> list[float]:
        predictions = []
        for row in rows:
            found = self.values.get(row.forecast_hour)
            if found is None:
                raise ValueError(f"Horizonte {row.forecast_hour} sin media de entrenamiento")
            predictions.append(found)
        return predictions


def fit_mean_double(train: Sequence[Window], validation: Sequence[Window]) -> FitReport:
    """Doble sin lightgbm: elige media global o por horizonte por MAE de validación."""
    train_rows = _rows(train)
    validation_rows = _rows(validation)
    if not train_rows or not validation_rows:
        raise ValueError("El ajuste exige filas de entrenamiento y validación")
    processing = ProcessingStats.fit(train_rows)
    horizon_values: dict[int, list[float]] = {}
    for row in train_rows:
        horizon_values.setdefault(row.forecast_hour, []).append(row.target)
    horizon_means = {
        hour: math.fsum(values) / len(values) for hour, values in horizon_values.items()
    }
    global_mean = math.fsum(row.target for row in train_rows) / len(train_rows)
    candidates = [
        MeanPredictor(
            name="global_mean",
            values={hour: global_mean for hour in horizon_means},
        ),
        MeanPredictor(name="mean_by_horizon", values=dict(horizon_means)),
    ]
    best: MeanPredictor | None = None
    best_mae = math.inf
    for candidate in candidates:
        candidate_mae = _validation_mae(candidate, validation_rows)
        if candidate_mae < best_mae:
            best_mae = candidate_mae
            best = candidate
    if best is None:
        raise ValueError("No hay candidato de ajuste disponible")
    return FitReport(
        predictor=best,
        processing=processing,
        validation_mae=best_mae,
        chosen_rounds=None,
    )


class LightGBMPredictor:
    """Envoltorio del booster; aplica el desfase de entrenamiento antes de predecir."""

    name = "lightgbm"

    def __init__(self, booster: Any, processing: ProcessingStats) -> None:
        self.booster = booster
        self.processing = processing

    def predict(self, rows: Sequence[DesignRow]) -> list[float]:
        shifted = apply_station_offset(rows, self.processing)
        values = [float(value) for value in self.booster.predict(_matrix(shifted))]
        if len(values) != len(rows) or any(not math.isfinite(value) for value in values):
            raise ValueError("LightGBM devolvió una predicción incompleta o no finita")
        return values


def _matrix(rows: Sequence[DesignRow]) -> Any:
    """Matriz para LightGBM; numpy llega como dependencia dura del extra 'tabular'."""
    numpy: Any = importlib.import_module("numpy")
    return numpy.asarray(vectorize(rows), dtype=numpy.float64)


def fit_lightgbm(
    train: Sequence[Window],
    validation: Sequence[Window],
    spec: FitSpec | None = None,
) -> FitReport:
    """LightGBM con pérdida L1 y parada temprana por MAE de validación."""
    try:
        lightgbm: Any = importlib.import_module("lightgbm")
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "LightGBM requiere el extra opcional 'tabular': uv sync --locked --extra tabular"
        ) from error
    settings = spec or FitSpec()
    train_rows = _rows(train)
    validation_rows = _rows(validation)
    if not train_rows or not validation_rows:
        raise ValueError("El ajuste exige filas de entrenamiento y validación")
    processing = ProcessingStats.fit(train_rows)
    train_set = lightgbm.Dataset(
        _matrix(apply_station_offset(train_rows, processing)),
        label=[row.target for row in train_rows],
    )
    validation_set = lightgbm.Dataset(
        _matrix(apply_station_offset(validation_rows, processing)),
        label=[row.target for row in validation_rows],
        reference=train_set,
    )
    params = {
        "objective": "regression_l1",
        "metric": "l1",
        "learning_rate": settings.learning_rate,
        "num_leaves": settings.num_leaves,
        "min_data_in_leaf": settings.min_data_in_leaf,
        "seed": settings.seed,
        "num_threads": 1,
        "deterministic": True,
        "force_row_wise": True,
        "verbose": -1,
    }
    booster = lightgbm.train(
        params=params,
        train_set=train_set,
        num_boost_round=settings.max_boosting_rounds,
        valid_sets=[validation_set],
        valid_names=["validation"],
        callbacks=[
            lightgbm.early_stopping(settings.early_stopping_rounds, verbose=False),
            lightgbm.log_evaluation(period=0),
        ],
    )
    chosen = booster.best_iteration or settings.max_boosting_rounds
    predictor = LightGBMPredictor(booster, processing)
    return FitReport(
        predictor=predictor,
        processing=processing,
        validation_mae=_validation_mae(predictor, validation_rows),
        chosen_rounds=chosen,
    )
