"""Métricas honestas en Python puro; lo indefinido se declara, nunca se disimula con ceros."""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import fmean
from typing import Literal

EpisodeStatus = Literal["defined", "no_labels", "no_positives"]


@dataclass(frozen=True, slots=True)
class Prediction:
    """Par ventana-horizonte con su objetivo, su predicción y su etiqueta si existe."""

    window_id: str
    station: str
    forecast_hour: int
    target: float
    prediction: float
    label: bool | None = None


def _residuals(preds: Sequence[Prediction]) -> list[float]:
    if not preds:
        raise ValueError("Las métricas exigen al menos una predicción")
    return [row.prediction - row.target for row in preds]


def mae(preds: Sequence[Prediction]) -> float:
    return math.fsum(abs(value) for value in _residuals(preds)) / len(preds)


def rmse(preds: Sequence[Prediction]) -> float:
    return math.sqrt(math.fsum(value * value for value in _residuals(preds)) / len(preds))


@dataclass(frozen=True, slots=True)
class ErrorSummary:
    n: int
    mae: float
    rmse: float


def overall_errors(preds: Sequence[Prediction]) -> ErrorSummary:
    return ErrorSummary(n=len(preds), mae=mae(preds), rmse=rmse(preds))


@dataclass(frozen=True, slots=True)
class ErrorRow:
    station: str
    forecast_hour: int
    n: int
    mae: float
    rmse: float


def error_table(preds: Sequence[Prediction]) -> list[ErrorRow]:
    """MAE y RMSE por estación y horizonte, en orden determinista."""
    groups: dict[tuple[str, int], list[Prediction]] = {}
    for row in preds:
        groups.setdefault((row.station, row.forecast_hour), []).append(row)
    return [
        ErrorRow(
            station=station,
            forecast_hour=hour,
            n=len(items),
            mae=mae(items),
            rmse=rmse(items),
        )
        for (station, hour), items in sorted(groups.items())
    ]


@dataclass(frozen=True, slots=True)
class EpisodeReport:
    """Precisión, exhaustividad, F1 y PR-AUC solo cuando hay etiquetas y positivos."""

    status: EpisodeStatus
    n: int
    positives: int
    precision: float | None
    recall: float | None
    f1: float | None
    average_precision: float | None


def episode_metrics(
    preds: Sequence[Prediction],
    thresholds: Mapping[str, float],
) -> EpisodeReport:
    """Detecta episodios comparando la predicción puntual con el umbral p95 de entrenamiento."""
    labeled = [row for row in preds if row.label is not None]
    if not labeled:
        return EpisodeReport("no_labels", 0, 0, None, None, None, None)
    positives = sum(1 for row in labeled if row.label)
    if positives == 0:
        return EpisodeReport("no_positives", len(labeled), 0, None, None, None, None)
    true_positive = 0
    false_positive = 0
    for row in labeled:
        threshold = thresholds.get(row.station)
        if threshold is None:
            raise ValueError(f"Falta el umbral de entrenamiento para {row.station}")
        called = row.prediction >= threshold
        if called and row.label:
            true_positive += 1
        elif called:
            false_positive += 1
    precision = true_positive / (true_positive + false_positive)
    recall = true_positive / positives
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return EpisodeReport(
        "defined",
        len(labeled),
        positives,
        precision,
        recall,
        f1,
        _average_precision(labeled, positives),
    )


def _average_precision(labeled: Sequence[Prediction], positives: int) -> float:
    ordered = sorted(labeled, key=lambda row: (-row.prediction, row.window_id, row.forecast_hour))
    hits = 0
    seen = 0
    total = 0.0
    for row in ordered:
        seen += 1
        if row.label:
            hits += 1
            total += hits / seen
    return total / positives


@dataclass(frozen=True, slots=True)
class BinRow:
    bin: int
    lower: float
    upper: float
    n: int
    positives: int
    mean_score: float | None
    event_rate: float | None


def calibration_bins(
    scores: Sequence[float],
    labels: Sequence[bool],
    *,
    bins: int = 10,
    lower: float | None = None,
    upper: float | None = None,
) -> list[BinRow]:
    """Calibración por intervalos de ancho igual; un bin sin casos queda indefinido."""
    if len(scores) != len(labels) or not scores:
        raise ValueError("Calibración exige la misma cantidad de puntuaciones y etiquetas")
    if bins < 1:
        raise ValueError("Se requiere al menos un intervalo")
    low = min(scores) if lower is None else lower
    high = max(scores) if upper is None else upper
    if not (math.isfinite(low) and math.isfinite(high)) or low >= high:
        raise ValueError("Rango de puntuación vacío para calibrar")
    width = (high - low) / bins
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for score, label in zip(scores, labels, strict=True):
        if not isinstance(label, bool):
            raise ValueError("Las etiquetas de calibración deben ser booleanas")
        if not math.isfinite(score) or score < low or score > high:
            raise ValueError("Puntuación fuera del rango declarado")
        index = min(int((score - low) / width), bins - 1)
        buckets[index].append((score, label))
    return [
        BinRow(
            bin=position,
            lower=low + position * width,
            upper=low + (position + 1) * width,
            n=len(items),
            positives=sum(1 for _, label in items if label),
            mean_score=fmean(score for score, _ in items) if items else None,
            event_rate=(sum(1 for _, label in items if label) / len(items) if items else None),
        )
        for position, items in enumerate(buckets)
    ]
