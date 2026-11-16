"""Etiquetas de referencia PM2.5; no certifican cumplimiento legal ni ausencia de riesgo."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean as arithmetic_mean
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict

WindowKind = Literal["forecast_24h", "calendar_day"]
EventLabel = Literal["above_reference", "not_above_reference", "not_evaluable"]


class LabelPolicy(BaseModel):
    """Regla versionada fija; cambiar significado requiere una nueva versión revisada."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1]
    policy_id: Literal["pe-pm25-reference-2017-v1"]
    pollutant: Literal["PM2.5"]
    unit: Literal["ug/m3"]
    threshold_ug_m3: Literal[50]
    comparison: Literal["gt"]
    period_hours: Literal[24]
    forecast_min_valid_hours: Literal[24]
    calendar_min_valid_hours: Literal[18]
    reference: Literal["DS-003-2017-MINAM"]
    completeness_reference: Literal["DS-010-2019-MINAM-anexo-1-c-i"]


def load_policy(path: Path) -> LabelPolicy:
    with path.open("rb") as stream:
        content = stream.read(65537)
    if len(content) > 65536:
        raise ValueError("La configuración supera 64 KiB")
    return LabelPolicy.model_validate(yaml.safe_load(content))


@dataclass(frozen=True)
class SeriesContext:
    source_id: str
    station_id: str
    unit: str
    timezone: str
    method: str
    semantic_evidence: str


@dataclass(frozen=True)
class HourlyPM25:
    """Promedio medido de una hora, identificado por el instante final del intervalo."""

    end: datetime
    value: float | None
    quality_valid: bool
    observation_id: str


@dataclass(frozen=True)
class LabelResult:
    kind: WindowKind
    start: datetime
    end: datetime
    calendar_date: date | None
    mean_ug_m3: float | None
    label: EventLabel
    valid_hours: int
    required_hours: int
    reason: Literal["evaluated", "insufficient_valid_hours"]
    policy_id: str
    context: SeriesContext
    observation_ids: tuple[str, ...]
    valid_observation_ids: tuple[str, ...]


def _instant(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Se requiere fecha con zona horaria confirmada")
    return value.astimezone(UTC)


def label_window(
    records: Sequence[HourlyPM25],
    *,
    start: datetime,
    kind: WindowKind,
    context: SeriesContext,
    policy: LabelPolicy,
) -> LabelResult:
    """Evaluar una sola serie; el llamador acredita semántica y calidad con evidencia."""
    if kind not in {"forecast_24h", "calendar_day"}:
        raise ValueError("Tipo de ventana no admitido")
    if (
        context.unit != policy.unit
        or context.method != "automatic_hourly"
        or not all(
            isinstance(value, str) and value.strip()
            for value in (context.source_id, context.station_id, context.semantic_evidence)
        )
        or not context.timezone
    ):
        raise ValueError("La serie requiere unidades, método y semántica documentados")
    try:
        zone = ZoneInfo(context.timezone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("La zona horaria documentada no está disponible o es inválida") from error
    start_utc = _instant(start)
    local_start = start_utc.astimezone(zone)
    if local_start.minute or local_start.second or local_start.microsecond:
        raise ValueError("El inicio debe coincidir con una hora completa")
    if kind == "calendar_day" and local_start.hour != 0:
        raise ValueError("El día calendario comienza a medianoche local")
    end_utc = start_utc + timedelta(hours=policy.period_hours)
    if kind == "calendar_day" and end_utc.astimezone(zone) != local_start + timedelta(days=1):
        raise ValueError("El día local no contiene exactamente 24 horas; regla no implementada")
    if len(records) > policy.period_hours:
        raise ValueError("Hay horas duplicadas o fuera de la ventana")
    indexed: dict[datetime, HourlyPM25] = {}
    ids: set[str] = set()
    for record in records:
        instant = _instant(record.end)
        if instant in indexed:
            raise ValueError("Hay horas duplicadas")
        offset = (instant - start_utc).total_seconds() / 3600
        if not 1 <= offset <= policy.period_hours or offset % 1 != 0:
            raise ValueError("La hora no corresponde a un intervalo de la ventana")
        if (
            not isinstance(record.observation_id, str)
            or not record.observation_id.strip()
            or record.observation_id in ids
            or not isinstance(record.quality_valid, bool)
        ):
            raise ValueError("Se requieren identificadores únicos y calidad explícita")
        indexed[instant] = record
        ids.add(record.observation_id)
    ordered = [indexed[key] for key in sorted(indexed)]
    valid: list[HourlyPM25] = []
    values: list[float] = []
    for record in ordered:
        value = record.value
        if (
            record.quality_valid
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
        ):
            valid.append(record)
            values.append(float(value))
    required = (
        policy.forecast_min_valid_hours
        if kind == "forecast_24h"
        else policy.calendar_min_valid_hours
    )
    # statistics.mean evita desbordar la suma de números finitos y no redondea a decimales.
    mean = arithmetic_mean(values) if len(valid) >= required else None
    label: EventLabel = "not_evaluable"
    if mean is not None:
        label = "above_reference" if mean > policy.threshold_ug_m3 else "not_above_reference"
    return LabelResult(
        kind=kind,
        start=local_start,
        end=end_utc.astimezone(zone),
        calendar_date=local_start.date() if kind == "calendar_day" else None,
        mean_ug_m3=mean,
        label=label,
        valid_hours=len(valid),
        required_hours=required,
        reason="evaluated" if mean is not None else "insufficient_valid_hours",
        policy_id=policy.policy_id,
        context=context,
        observation_ids=tuple(record.observation_id for record in ordered),
        valid_observation_ids=tuple(record.observation_id for record in valid),
    )
