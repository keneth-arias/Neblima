"""Características tabulares desde la historia de la ventana; los objetivos futuros jamás entran."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

HISTORY_HOURS = 24
MAX_FORECAST_HOURS = 48

LAG_NAMES = tuple(f"lag_{lag:02d}" for lag in range(HISTORY_HOURS))
CALENDAR_NAMES = ("valid_hour_sin", "valid_hour_cos")
HORIZON_NAME = "forecast_hour"
STATION_OFFSET_NAME = "station_offset"
FEATURE_NAMES = (*LAG_NAMES, HORIZON_NAME, *CALENDAR_NAMES, STATION_OFFSET_NAME)


def _require_finite(values: tuple[float, ...], field: str) -> None:
    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"{field} exige números finitos")


@dataclass(frozen=True, slots=True)
class Window:
    """Ventana completa de #18: historia de 24 h y objetivos por horizonte en µg/m³."""

    window_id: str
    station: str
    origin_at: datetime
    history: tuple[float, ...]
    targets: tuple[float, ...]
    labels: tuple[bool | None, ...] = ()

    def __post_init__(self) -> None:
        if not self.window_id.strip() or not self.station.strip():
            raise ValueError("Identificadores de ventana y estación son obligatorios")
        if self.origin_at.tzinfo is None or self.origin_at.utcoffset() is None:
            raise ValueError("origin_at requiere zona horaria confirmada (UTC)")
        if len(self.history) != HISTORY_HOURS:
            raise ValueError(f"La historia requiere exactamente {HISTORY_HOURS} valores")
        _require_finite(self.history, "history")
        if not 1 <= len(self.targets) <= MAX_FORECAST_HOURS:
            raise ValueError("Los objetivos deben cubrir de uno a 48 horizontes")
        _require_finite(self.targets, "targets")
        if len(self.labels) not in (0, len(self.targets)):
            raise ValueError("Las etiquetas deben cubrir todos los horizontes o ninguno")
        if any(label is not None and not isinstance(label, bool) for label in self.labels):
            raise ValueError("Cada etiqueta debe ser True, False o None")


@dataclass(frozen=True, slots=True)
class DesignRow:
    """Par ventana-horizonte listo para ajustar; target y label quedan fuera de features."""

    window_id: str
    station: str
    forecast_hour: int
    features: tuple[float, ...]
    target: float
    label: bool | None


def _features(window: Window, forecast_hour: int) -> tuple[float, ...]:
    lags = tuple(float(value) for value in reversed(window.history))
    valid_time = window.origin_at.astimezone(UTC) + timedelta(hours=forecast_hour)
    angle = 2 * math.pi * valid_time.hour / 24
    return (*lags, float(forecast_hour), math.sin(angle), math.cos(angle), 0.0)


def design_rows(window: Window) -> list[DesignRow]:
    """Una fila por horizonte; las características solo leen historia y calendario UTC."""
    if not window.targets:
        raise ValueError("La ventana no tiene objetivos")
    return [
        DesignRow(
            window_id=window.window_id,
            station=window.station,
            forecast_hour=hour,
            features=_features(window, hour),
            target=target,
            label=window.labels[hour - 1] if window.labels else None,
        )
        for hour, target in enumerate(window.targets, start=1)
    ]


def vectorize(rows: Sequence[DesignRow]) -> list[list[float]]:
    """Matriz densa en el orden de FEATURE_NAMES, lista para LightGBM."""
    if any(len(row.features) != len(FEATURE_NAMES) for row in rows):
        raise ValueError("Las características no coinciden con FEATURE_NAMES")
    return [list(row.features) for row in rows]
