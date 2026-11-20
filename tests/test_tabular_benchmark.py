"""Pruebas sintéticas del benchmark tabular: ajuste solo en entrenamiento y métricas honestas."""

import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from airaware.benchmarks.features import (
    FEATURE_NAMES,
    HISTORY_HOURS,
    DesignRow,
    Window,
    design_rows,
)
from airaware.benchmarks.metrics import (
    Prediction,
    calibration_bins,
    episode_metrics,
    error_table,
    overall_errors,
)
from airaware.benchmarks.model import FitSpec, fit_lightgbm, fit_mean_double
from airaware.benchmarks.predictions import paired_evaluation, paired_join, predictions_from
from airaware.benchmarks.processing import ProcessingStats, apply_station_offset

ORIGIN = datetime(2022, 3, 1, tzinfo=UTC)


def pattern(hour_index: int, station: str) -> float:
    """Valor sintético determinista con ciclo diario y desfase por estación."""
    base = 10 + 5 * math.sin(2 * math.pi * (hour_index % 24) / 24)
    return base + (8 if station == "s2" else 0)


def make_window(
    index: int,
    station: str,
    *,
    labels: tuple[bool | None, ...] | None = None,
) -> Window:
    origin = ORIGIN + timedelta(hours=5 * index)
    history = tuple(pattern(5 * index - (23 - lag), station) for lag in range(HISTORY_HOURS))
    targets = tuple(pattern(5 * index + horizon, station) for horizon in range(1, 7))
    if labels is None:
        labels = tuple(target >= 18 for target in targets)
    return Window(
        window_id=f"w{index}",
        station=station,
        origin_at=origin,
        history=history,
        targets=targets,
        labels=labels,
    )


PARTITIONS: dict[str, list[Window]] = {
    "train": [make_window(index, "s1" if index % 2 == 0 else "s2") for index in range(12)],
    "validation": [make_window(index, "s1" if index % 2 == 0 else "s2") for index in range(20, 24)],
    "test": [make_window(index, "s1" if index % 2 == 0 else "s2") for index in range(30, 34)],
}


def rows(partition: str) -> list[DesignRow]:
    return [row for window in PARTITIONS[partition] for row in design_rows(window)]


def perturb(window: Window) -> Window:
    return Window(
        window_id=window.window_id,
        station=window.station,
        origin_at=window.origin_at,
        history=tuple(value + 1 for value in window.history),
        targets=tuple(target + 3 for target in window.targets),
        labels=window.labels,
    )


def test_las_caracteristicas_ignoran_objetivos_y_etiquetas():
    window = PARTITIONS["train"][0]
    same_inputs = Window(
        window_id=window.window_id,
        station=window.station,
        origin_at=window.origin_at,
        history=window.history,
        targets=tuple(target + 100 for target in window.targets),
        labels=tuple(not (label if label is not None else False) for label in window.labels),
    )
    altered_history = Window(
        window_id=window.window_id,
        station=window.station,
        origin_at=window.origin_at,
        history=tuple(value + 1 for value in window.history),
        targets=window.targets,
        labels=window.labels,
    )
    base_features = [row.features for row in design_rows(window)]
    assert base_features == [row.features for row in design_rows(same_inputs)]
    assert base_features != [row.features for row in design_rows(altered_history)]
    assert len(base_features[0]) == len(FEATURE_NAMES)
    assert not any("target" in name or "label" in name for name in FEATURE_NAMES)


def test_el_procesamiento_solo_participa_del_entrenamiento():
    stats_train = ProcessingStats.fit(rows("train"))
    validation_rows = rows("validation")
    stats_validation = ProcessingStats.fit(validation_rows)
    assert stats_validation.to_dict() != stats_train.to_dict()

    report_stable = fit_mean_double(PARTITIONS["train"], PARTITIONS["validation"])
    report_repeat = fit_mean_double(PARTITIONS["train"], PARTITIONS["validation"])
    report_perturbed = fit_mean_double(
        PARTITIONS["train"], [perturb(window) for window in PARTITIONS["validation"]]
    )
    assert report_stable.processing.to_dict() == report_perturbed.processing.to_dict()
    assert report_stable.processing.to_dict() == report_repeat.processing.to_dict()
    assert stats_train.to_dict() == report_stable.processing.to_dict()
    probe = rows("test")
    assert report_stable.predictor.predict(probe) == report_repeat.predictor.predict(probe)

    shifted = apply_station_offset(rows("train"), stats_train)
    first = shifted[0]
    station = stats_train.station(first.station)
    assert station is not None
    expected = (first.features[0] - station.mean) / station.std
    assert math.isclose(first.features[-1], expected)
    assert stats_train.offset(first.features[0], "estacion_desconocida") == 0.0
    with pytest.raises(ValueError, match="filas de entrenamiento"):
        ProcessingStats.fit([])


def test_la_union_exige_objetivos_identicos():
    report = fit_mean_double(PARTITIONS["train"], PARTITIONS["validation"])
    left = predictions_from(report.predictor, rows("test"))
    right = predictions_from(report.predictor, rows("test"))
    assert len(left) == 24

    paired = paired_join(left, right)
    assert len(paired) == 24
    evaluation = paired_evaluation(left, right)
    assert evaluation.n == 24
    assert evaluation.mae_left == evaluation.mae_right

    discordant = [replace(right[0], target=right[0].target + 0.5), *right[1:]]
    with pytest.raises(ValueError, match="discordantes"):
        paired_join(left, discordant)
    with pytest.raises(ValueError, match="duplicadas"):
        paired_join(left, [*right, right[0]])
    with pytest.raises(ValueError, match="clave común"):
        paired_evaluation([], right)


def test_metricas_de_error_por_estacion_y_horizonte():
    preds = [
        Prediction("w0", "s1", 1, 10, 12),
        Prediction("w1", "s1", 2, 11, 8),
        Prediction("w2", "s2", 1, 18, 20),
    ]
    summary = overall_errors(preds)
    assert summary.n == 3
    assert math.isclose(summary.mae, 7 / 3)
    assert math.isclose(summary.rmse, math.sqrt(17 / 3))
    table = error_table(preds)
    assert [(row.station, row.forecast_hour, row.n) for row in table] == [
        ("s1", 1, 1),
        ("s1", 2, 1),
        ("s2", 1, 1),
    ]
    assert math.isclose(table[1].mae, 3.0)
    assert math.isclose(table[2].rmse, 2.0)
    with pytest.raises(ValueError, match="al menos una predicción"):
        overall_errors([])


def test_episodios_definidos_con_positivos():
    thresholds = {"s1": 15.0, "s2": 30.0}
    preds = [
        Prediction("a", "s1", 1, 20, 35, True),
        Prediction("b", "s1", 2, 9, 12, False),
        Prediction("c", "s2", 1, 31, 32, True),
        Prediction("d", "s2", 2, 10, 33, False),
        Prediction("e", "s2", 3, 28, 25, True),
        Prediction("f", "s1", 3, 5, 1, None),
    ]
    report = episode_metrics(preds, thresholds)
    assert report.status == "defined"
    assert report.n == 5
    assert report.positives == 3
    assert report.precision is not None
    assert report.recall is not None
    assert report.f1 is not None
    assert report.average_precision is not None
    assert math.isclose(report.precision, 2 / 3)
    assert math.isclose(report.recall, 2 / 3)
    assert math.isclose(report.f1, 2 / 3)
    assert math.isclose(report.average_precision, 29 / 36)
    with pytest.raises(ValueError, match="umbral"):
        episode_metrics([Prediction("g", "s9", 1, 1, 2, True)], {"s1": 15.0})


def test_episodios_sin_positivos_quedan_indefinidos():
    thresholds = {"s1": 15.0}
    preds = [
        Prediction("a", "s1", 1, 9, 12, False),
        Prediction("b", "s1", 2, 8, 16, False),
    ]
    report = episode_metrics(preds, thresholds)
    assert report.status == "no_positives"
    assert report.n == 2
    assert report.positives == 0
    assert report.precision is None
    assert report.recall is None
    assert report.f1 is None
    assert report.average_precision is None


def test_episodios_sin_etiquetas_quedan_indefinidas():
    preds = [Prediction("a", "s1", 1, 9, 12, None)]
    report = episode_metrics(preds, {})
    assert report.status == "no_labels"
    assert report.n == 0
    assert report.positives == 0
    assert report.precision is None
    assert report.average_precision is None


def test_calibracion_por_bins():
    rows_bins = calibration_bins(
        [0.1, 0.35, 0.6, 0.9],
        [False, True, False, True],
        bins=4,
        lower=0.0,
        upper=1.0,
    )
    assert [row.n for row in rows_bins] == [1, 1, 1, 1]
    assert rows_bins[1].positives == 1
    assert rows_bins[1].event_rate == 1.0
    assert rows_bins[0].mean_score is not None
    assert math.isclose(rows_bins[0].mean_score, 0.1)
    assert rows_bins[3].lower == 0.75 and rows_bins[3].upper == 1.0

    sparse = calibration_bins(
        [0.05, 0.1, 1.0],
        [False, True, True],
        bins=4,
        lower=0.0,
        upper=1.0,
    )
    assert sparse[0].n == 2 and sparse[0].positives == 1
    assert [row.n for row in sparse[1:]] == [0, 0, 1]
    assert sparse[1].mean_score is None and sparse[1].event_rate is None

    with pytest.raises(ValueError, match="fuera del rango"):
        calibration_bins([1.5], [True], bins=4, lower=0.0, upper=1.0)
    with pytest.raises(ValueError, match="Rango de puntuación vacío"):
        calibration_bins([2.0, 2.0], [True, False])
    non_boolean: list[Any] = [1]
    with pytest.raises(ValueError, match="booleanas"):
        calibration_bins([0.5], non_boolean, bins=4, lower=0.0, upper=1.0)


def plan_window(index: int, station: str, targets: tuple[float, ...]) -> Window:
    origin = ORIGIN + timedelta(hours=7 * index)
    history = tuple(pattern(7 * index - (23 - lag), station) for lag in range(HISTORY_HOURS))
    return Window(
        window_id=f"p{index}",
        station=station,
        origin_at=origin,
        history=history,
        targets=targets,
        labels=(),
    )


LINEAR_TRAIN = [
    plan_window(index, "s1" if index % 2 == 0 else "s2", tuple(10.0 + h for h in range(1, 7)))
    for index in range(8)
]


def test_el_ajuste_minimo_selecciona_en_validacion():
    linear_validation = [
        plan_window(index, "s1", tuple(10.0 + h for h in range(1, 7))) for index in range(8, 10)
    ]
    by_horizon = fit_mean_double(LINEAR_TRAIN, linear_validation)
    assert by_horizon.predictor.name == "mean_by_horizon"
    assert by_horizon.validation_mae == 0.0
    assert by_horizon.chosen_rounds is None
    assert set(by_horizon.processing.stations) == {"s1", "s2"}

    constant_validation = [
        plan_window(index, "s1", tuple(13.5 for _ in range(6))) for index in range(8, 10)
    ]
    global_mean = fit_mean_double(LINEAR_TRAIN, constant_validation)
    assert global_mean.predictor.name == "global_mean"
    assert global_mean.validation_mae == 0.0

    probe = [
        row
        for window in [plan_window(20, "s1", tuple(99.0 for _ in range(6)))]
        for row in design_rows(window)
    ]
    predictions = by_horizon.predictor.predict(probe)
    assert predictions == [11.0, 12.0, 13.0, 14.0, 15.0, 16.0]


def test_lightgbm_ajusta_con_seleccion_en_validacion():
    pytest.importorskip(
        "lightgbm",
        reason="CI instala sin extras; el ajuste LightGBM exige el extra opcional 'tabular'",
    )
    spec = FitSpec(
        learning_rate=0.2,
        num_leaves=7,
        min_data_in_leaf=3,
        max_boosting_rounds=30,
        early_stopping_rounds=5,
    )
    report = fit_lightgbm(PARTITIONS["train"], PARTITIONS["validation"], spec)
    assert isinstance(report.chosen_rounds, int)
    assert 1 <= report.chosen_rounds <= 30
    assert math.isfinite(report.validation_mae)
    assert report.processing.to_dict() == ProcessingStats.fit(rows("train")).to_dict()

    test_rows = rows("test")
    preds = predictions_from(report.predictor, test_rows)
    assert len(preds) == 24
    assert all(math.isfinite(row.prediction) for row in preds)

    altered_targets = [
        Window(
            window_id=window.window_id,
            station=window.station,
            origin_at=window.origin_at,
            history=window.history,
            targets=tuple(target + 50 for target in window.targets),
            labels=tuple(not (label if label is not None else False) for label in window.labels),
        )
        for window in PARTITIONS["test"]
    ]
    altered_rows = [row for window in altered_targets for row in design_rows(window)]
    altered = predictions_from(report.predictor, altered_rows)
    assert [row.prediction for row in altered] == [row.prediction for row in preds]

    table = error_table(preds)
    assert table
    episodes = episode_metrics(preds, report.processing.thresholds())
    assert episodes.status == "defined"
    assert episodes.positives > 0
    assert episodes.average_precision is not None
