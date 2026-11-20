"""Estadísticas de procesamiento calculadas SOLO con filas de entrenamiento."""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from airaware.benchmarks.features import FEATURE_NAMES, STATION_OFFSET_NAME, DesignRow


@dataclass(frozen=True, slots=True)
class StationStats:
    station: str
    n: int
    mean: float
    std: float
    p95: float


@dataclass(frozen=True, slots=True)
class ProcessingStats:
    """Resumen por estación de los objetivos de entrenamiento; no mutar stations."""

    stations: dict[str, StationStats]

    @classmethod
    def fit(cls, rows: Iterable[DesignRow]) -> "ProcessingStats":
        """Ajusta medias, desviación y p95 por estación; solo participa el entrenamiento."""
        grouped: dict[str, list[float]] = {}
        for row in rows:
            grouped.setdefault(row.station, []).append(row.target)
        if not grouped:
            raise ValueError("El procesamiento exige filas de entrenamiento")
        stations: dict[str, StationStats] = {}
        for station, targets in grouped.items():
            count = len(targets)
            mean = math.fsum(targets) / count
            variance = math.fsum((target - mean) ** 2 for target in targets) / count
            stations[station] = StationStats(
                station=station,
                n=count,
                mean=mean,
                std=math.sqrt(variance),
                p95=_percentile(sorted(targets), 0.95),
            )
        return cls(stations=stations)

    def station(self, name: str) -> StationStats | None:
        return self.stations.get(name)

    def offset(self, origin_value: float, station: str) -> float:
        """Desfase respecto de la media de entrenamiento; 0.0 si la estación es desconocida."""
        found = self.stations.get(station)
        if found is None or found.std == 0:
            return 0.0
        return (origin_value - found.mean) / found.std

    def thresholds(self) -> dict[str, float]:
        """Umbral p95 por estación, ajustado solo con entrenamiento (agrupación exploratoria)."""
        return {name: item.p95 for name, item in self.stations.items()}

    def to_dict(self) -> dict[str, dict[str, float | int]]:
        return {
            name: {"n": item.n, "mean": item.mean, "std": item.std, "p95": item.p95}
            for name, item in sorted(self.stations.items())
        }


def apply_station_offset(rows: Sequence[DesignRow], stats: ProcessingStats) -> list[DesignRow]:
    """Sustituye la última característica por el desfase de entrenamiento de cada estación."""
    position = FEATURE_NAMES.index(STATION_OFFSET_NAME)
    shifted = []
    for row in rows:
        features = list(row.features)
        features[position] = stats.offset(features[0], row.station)
        shifted.append(
            DesignRow(
                window_id=row.window_id,
                station=row.station,
                forecast_hour=row.forecast_hour,
                features=tuple(features),
                target=row.target,
                label=row.label,
            )
        )
    return shifted


def _percentile(sorted_values: list[float], quantile: float) -> float:
    position = quantile * (len(sorted_values) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return sorted_values[low]
    weight = position - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight
