"""Retención (holdout) de estaciones para la evaluación secundaria nacional (#32).

La evaluación secundaria reserva estaciones completas: ninguna ventana de esas
estaciones puede entrar a entrenamiento, validación, prueba ni preentrenamiento.
El módulo planifica la retención de forma declarativa y determinista (plan
versionado con hash SHA-256) y verifica, fallando cerrado, el aislamiento de las
estaciones reservadas frente a los manifiestos del contrato de particiones de
#19 (`senamhi_splits`), el aislamiento espacial (distancia haversine con umbral
declarado) y el aislamiento temporal (periodos UTC explícitos de la grilla
horaria de #15, `senamhi_timeline`).

Política de frontera temporal: la igualdad exacta de instante entre el periodo
reservado y otro periodo se considera solape (verificación inclusiva), coherente
con la purga de fronteras de #19 donde la hora de un corte pertenece al bloque
siguiente. Es mejor rechazar un límite compartido que permitir una hora ambigua.

Este módulo no ejecuta la evaluación real: opera sobre los esquemas de los
manifiestos con datos sintéticos de prueba. La ejecución sobre el paquete real
queda pendiente de #19/#30 y debe verificar los SHA-256 de los archivos con
`derived_artifacts.sha256_file` antes de entregar los manifiestos aquí.
"""

import json
import math
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from hashlib import sha256

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from airaware.senamhi_splits import SPLITS_VERSION
from airaware.senamhi_timeline import TIMELINE_VERSION

HOLDOUT_PLAN_VERSION = "senamhi-holdout-plan-v1"
PARAMETER_RAW = "PM2_5"
EARTH_RADIUS_KM = 6371.0088

STATION_KEY_PATTERN = r"^[0-9a-f]{64}$"


class HoldoutIsolationError(ValueError):
    """Aislamiento incumplido o manifiesto fuera del contrato; falla cerrada."""

    def __init__(self, message: str, violations: Sequence[Mapping] = ()) -> None:
        self.violations = [dict(item) for item in violations]
        super().__init__(message)


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _require_utc_instant(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("El instante debe declarar su zona: se exige desplazamiento UTC explícito")
    return value.astimezone(UTC)


def _require_exact_hour(value: datetime) -> datetime:
    if value.minute != 0 or value.second != 0 or value.microsecond != 0:
        raise ValueError(
            "La grilla del contrato es horaria: el instante debe caer en una hora exacta"
        )
    return value


class StationIdentity(BaseModel):
    """Identidad provisional de estación con coordenadas declaradas."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    station_key: str = Field(pattern=STATION_KEY_PATTERN)
    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PeriodUtc(BaseModel):
    """Intervalo de horas UTC exactas, cerrado en ambos extremos."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def _grid_instant(cls, value: datetime) -> datetime:
        return _require_exact_hour(_require_utc_instant(value))

    @model_validator(mode="after")
    def _ordered(self) -> "PeriodUtc":
        if self.start >= self.end:
            raise ValueError("El periodo reservado exige inicio anterior al fin")
        return self

    @field_serializer("start", "end")
    def _iso(self, value: datetime) -> str:
        return value.isoformat()

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    def hours(self) -> int:
        """Horas de la grilla dentro del intervalo cerrado."""
        return int((self.end - self.start).total_seconds() // 3600) + 1


class HoldoutConfig(BaseModel):
    """Configuración declarativa del holdout; nada se elige al azar."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    criterion: str = Field(min_length=1)
    created_at_utc: datetime
    reserved_stations: tuple[StationIdentity, ...] = Field(min_length=1)
    training_stations: tuple[StationIdentity, ...] = Field(min_length=1)
    reserved_period: PeriodUtc
    min_distance_km: float = Field(gt=0)
    min_hours_per_station: int = Field(ge=1)

    @field_validator("created_at_utc")
    @classmethod
    def _aware_creation(cls, value: datetime) -> datetime:
        return _require_utc_instant(value)

    @model_validator(mode="after")
    def _disjoint_roles(self) -> "HoldoutConfig":
        reserved = [item.station_key for item in self.reserved_stations]
        training = [item.station_key for item in self.training_stations]
        if len(set(reserved)) != len(reserved):
            raise ValueError("Estación reservada duplicada en la configuración")
        if len(set(training)) != len(training):
            raise ValueError("Estación de entrenamiento duplicada en la configuración")
        shared = set(reserved) & set(training)
        if shared:
            detail = ", ".join(sorted(shared))
            raise ValueError(
                f"Una estación reservada no puede ser también de entrenamiento: {detail}"
            )
        return self

    @field_serializer("created_at_utc")
    def _iso_creation(self, value: datetime) -> str:
        return value.isoformat()


class HoldoutPlan(HoldoutConfig):
    """Plan versionado y auditable; el hash cubre todo el contenido declarado."""

    version: str
    plan_sha256: str = Field(pattern=STATION_KEY_PATTERN)

    @model_validator(mode="after")
    def _verify_content(self) -> "HoldoutPlan":
        if self.version != HOLDOUT_PLAN_VERSION:
            raise ValueError("Versión desconocida del plan de retención")
        if self.plan_sha256 != _plan_digest(self.content_dict()):
            raise ValueError("El SHA-256 del plan no coincide con el contenido declarado")
        return self

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    def content_dict(self) -> dict:
        payload = self.to_dict()
        del payload["plan_sha256"]
        return payload


def _plan_digest(content: dict) -> str:
    return sha256(_canonical_json(content).encode("utf-8")).hexdigest()


def plan_holdout(config: HoldoutConfig) -> HoldoutPlan:
    """Fijar el plan de retención con hash SHA-256 de su contenido declarado."""
    content = {**config.model_dump(mode="json"), "version": HOLDOUT_PLAN_VERSION}
    return HoldoutPlan.model_validate({**content, "plan_sha256": _plan_digest(content)})


def haversine_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    """Distancia haversine en kilómetros entre (latitud, longitud) en grados."""
    lat1, lon1 = math.radians(first[0]), math.radians(first[1])
    lat2, lon2 = math.radians(second[0]), math.radians(second[1])
    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _contract_error(message: str) -> HoldoutIsolationError:
    return HoldoutIsolationError(message)


def _manifest_counts(manifest: object, label: str) -> list[Mapping]:
    """Leer counts de un manifiesto del contrato de particiones de #19."""
    if not isinstance(manifest, Mapping):
        raise _contract_error(f"El manifiesto '{label}' no es un objeto de contrato")
    version = manifest.get("version")
    if version != SPLITS_VERSION:
        raise _contract_error(
            f"El manifiesto '{label}' no pertenece al contrato de particiones de #19 "
            f"(versión observada: {version!r}, exigida: {SPLITS_VERSION!r})"
        )
    counts = manifest.get("counts")
    if not isinstance(counts, list):
        raise _contract_error(f"El manifiesto '{label}' no declara counts")
    rows: list[Mapping] = []
    for row in counts:
        if not isinstance(row, Mapping):
            raise _contract_error(
                f"El manifiesto '{label}' tiene una fila de counts sin estructura"
            )
        key = row.get("station_key")
        split = row.get("split")
        if not isinstance(key, str) or not key or not isinstance(split, str) or not split:
            raise _contract_error(
                f"El manifiesto '{label}' tiene una fila de counts sin station_key o split"
            )
        windows = row.get("windows")
        if type(windows) is not int or windows <= 0:
            raise _contract_error(f"El manifiesto '{label}' tiene un conteo de ventanas inválido")
        rows.append(row)
    splits = {row["split"] for row in rows}
    if splits - {"purged"} != {"train", "validation", "test"}:
        raise _contract_error(f"Las particiones del manifiesto '{label}' difieren de las de #19")
    return rows


def station_leakage_violations(plan: HoldoutPlan, manifests: Mapping[str, object]) -> list[dict]:
    """Estaciones reservadas presentes en manifiestos de entrenamiento o afines."""
    reserved = {item.station_key for item in plan.reserved_stations}
    violations: list[dict] = []
    training = {item.station_key for item in plan.training_stations}
    for label in manifests:
        for row in _manifest_counts(manifests[label], label):
            key = row["station_key"]
            if key not in training:
                violations.append(
                    {
                        "type": "station_leakage" if key in reserved else "undeclared_station",
                        "manifest": label,
                        "station_key": key,
                        "split": row["split"],
                    }
                )
    return violations


def spatial_isolation_violations(plan: HoldoutPlan) -> list[dict]:
    """Pares reservada-entrenamiento por debajo del umbral declarado."""
    violations: list[dict] = []
    for reserved in plan.reserved_stations:
        for training in plan.training_stations:
            distance = haversine_km(
                (reserved.latitude, reserved.longitude),
                (training.latitude, training.longitude),
            )
            if distance < plan.min_distance_km:
                violations.append(
                    {
                        "type": "spatial_proximity",
                        "reserved_station_key": reserved.station_key,
                        "training_station_key": training.station_key,
                        "distance_km": round(distance, 6),
                        "threshold_km": plan.min_distance_km,
                    }
                )
    return violations


def _coerce_period(label: str, value: object) -> PeriodUtc:
    if isinstance(value, PeriodUtc):
        return value
    if isinstance(value, Mapping):
        try:
            return PeriodUtc.model_validate(value)
        except ValueError as error:
            raise HoldoutIsolationError(
                f"El periodo '{label}' no declara zona UTC explícita o está mal ordenado: {error}"
            ) from None
    if isinstance(value, tuple) and len(value) == 2:
        try:
            return PeriodUtc.model_validate({"start": value[0], "end": value[1]})
        except ValueError as error:
            raise HoldoutIsolationError(
                f"El periodo '{label}' no declara zona UTC explícita o está mal ordenado: {error}"
            ) from None
    raise HoldoutIsolationError(f"El periodo '{label}' no es un par de instantes UTC")


def temporal_isolation_violations(
    plan: HoldoutPlan, periods: Mapping[str, object] | None
) -> list[dict]:
    """Solapes del periodo reservado con periodos declarados; frontera inclusiva."""
    violations: list[dict] = []
    reserved = plan.reserved_period
    for label, value in (periods or {}).items():
        period = _coerce_period(label, value)
        if period.start <= reserved.end and reserved.start <= period.end:
            violations.append(
                {
                    "type": "temporal_overlap",
                    "period_label": label,
                    "period": period.to_dict(),
                    "reserved_period": reserved.to_dict(),
                }
            )
    return violations


def _describe(violation: Mapping) -> str:
    kind = violation.get("type")
    if kind == "station_leakage":
        return (
            f"estación reservada {violation['station_key']} aparece en el manifiesto "
            f"'{violation['manifest']}' (split infractor: {violation['split']})"
        )
    if kind == "undeclared_station":
        return (
            f"la estación {violation['station_key']} del manifiesto '{violation['manifest']}' "
            f"({violation['split']}) carece de coordenadas en training_stations"
        )
    if kind == "spatial_proximity":
        return (
            f"la estación reservada {violation['reserved_station_key']} dista "
            f"{violation['distance_km']} km de la estación de entrenamiento "
            f"{violation['training_station_key']} "
            f"(umbral declarado: {violation['threshold_km']} km)"
        )
    if kind == "temporal_overlap":
        period = violation["period"]
        return (
            f"el periodo reservado solapa el periodo '{violation['period_label']}' "
            f"({period['start']}..{period['end']})"
        )
    return _canonical_json(violation)


def verify_isolation(
    plan: HoldoutPlan,
    manifests: Mapping[str, object],
    periods: Mapping[str, object] | None = None,
) -> dict:
    """Verificar aislamiento de estaciones, espacio y tiempo; reporte serializable."""
    required = {"entrenamiento", "preentrenamiento"}
    missing = required.difference(manifests)
    if missing:
        raise HoldoutIsolationError("Faltan manifiestos de " + ", ".join(sorted(missing)))
    period_labels = set(periods or {})
    if period_labels != set(manifests):
        detail = ", ".join(sorted(period_labels.symmetric_difference(manifests)))
        raise HoldoutIsolationError(f"Se exige un periodo por manifiesto. Revisar {detail}")
    violations = [
        *station_leakage_violations(plan, manifests),
        *spatial_isolation_violations(plan),
        *temporal_isolation_violations(plan, periods),
    ]
    return {"isolated": not violations, "violations": violations}


def assert_isolation(
    plan: HoldoutPlan,
    manifests: Mapping[str, object],
    periods: Mapping[str, object] | None = None,
) -> None:
    """Falla cerrada: lanza HoldoutIsolationError con el detalle de cada violación."""
    report = verify_isolation(plan, manifests, periods)
    if report["violations"]:
        detail = "\n".join(f"- {_describe(item)}" for item in report["violations"])
        raise HoldoutIsolationError(
            f"El holdout no está aislado ({len(report['violations'])} violaciones):\n{detail}",
            report["violations"],
        )


def _grid_counts(manifest: object) -> list[Mapping]:
    """Leer counts de la grilla horaria del periodo según el contrato de #15."""
    if not isinstance(manifest, Mapping):
        raise _contract_error("La grilla del periodo no es un objeto de contrato")
    version = manifest.get("version")
    if version != TIMELINE_VERSION:
        raise _contract_error(
            f"La grilla del periodo no pertenece al contrato horario de #15 "
            f"(versión observada: {version!r}, exigida: {TIMELINE_VERSION!r})"
        )
    counts = manifest.get("counts")
    if not isinstance(counts, list):
        raise _contract_error("La grilla del periodo no declara counts")
    rows: list[Mapping] = []
    for row in counts:
        if not isinstance(row, Mapping):
            raise _contract_error("La grilla del periodo tiene una fila de counts sin estructura")
        key = row.get("station_key")
        status = row.get("status")
        parameter = row.get("parameter_raw")
        hours = row.get("hours")
        if not isinstance(key, str) or not key or not isinstance(status, str) or not status:
            raise _contract_error("La grilla del periodo tiene una fila sin station_key o status")
        if not isinstance(parameter, str) or not parameter:
            raise _contract_error("La grilla del periodo tiene una fila sin parameter_raw")
        if type(hours) is not int or hours < 0:
            raise _contract_error(
                f"hours inválido en la grilla del periodo para {key}: "
                f"{hours!r} (se exige entero >= 0)"
            )
        rows.append(row)
    return rows


def summarize_representativity(plan: HoldoutPlan, period_grid_manifest: object) -> dict:
    """Cobertura honesta por estación reservada; marca insuficiencia sin imputar.

    `period_grid_manifest` sigue el esquema de counts de la grilla de #15 con las
    horas observadas de PM2_5 scoped al periodo reservado. Las estaciones sin
    filas se reportan con cero horas disponibles: no se inventan ni imputan.
    """
    observed: dict[str, int] = {}
    reserved_keys = {item.station_key for item in plan.reserved_stations}
    for row in _grid_counts(period_grid_manifest):
        key = row["station_key"]
        if key not in reserved_keys:
            continue
        if row["parameter_raw"] != PARAMETER_RAW or row["status"] != "observed":
            continue
        if key in observed:
            raise HoldoutIsolationError(
                f"Cuenta de horas duplicada para la estación reservada {key} "
                "en la grilla del periodo"
            )
        observed[key] = row["hours"]
    expected = plan.reserved_period.hours()
    stations: list[dict] = []
    insufficient: list[str] = []
    for station in plan.reserved_stations:
        available = observed.get(station.station_key, 0)
        if available > expected:
            raise HoldoutIsolationError(
                f"La estación {station.station_key} declara {available} horas observadas "
                f"en un periodo de {expected} horas"
            )
        sufficient = available >= plan.min_hours_per_station
        if not sufficient:
            insufficient.append(station.station_key)
        stations.append(
            {
                "station_key": station.station_key,
                "name": station.name,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "available_hours": available,
                "expected_hours": expected,
                "coverage_ratio": round(available / expected, 6),
                "minimum_hours_declared": plan.min_hours_per_station,
                "sufficient": sufficient,
            }
        )
    return {
        "version": HOLDOUT_PLAN_VERSION,
        "plan_sha256": plan.plan_sha256,
        "reserved_period": plan.reserved_period.to_dict(),
        "parameter_raw": PARAMETER_RAW,
        "expected_hours_per_station": expected,
        "minimum_hours_per_station": plan.min_hours_per_station,
        "stations": stations,
        "insufficient_station_keys": insufficient,
        "all_sufficient": not insufficient,
    }
