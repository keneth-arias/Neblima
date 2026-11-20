"""Integración estructural de ventanas #18 con etiquetas PM2.5; elegibilidad cerrada.

Separa dos comprobaciones: la compatibilidad estructural (límites, estación, reconstrucción
y conciliación de conteos) y la elegibilidad científica para etiquetar. Verifica además la
separación temporal historia/objetivo: ningún campo derivado de etiquetas entra en las
entradas del modelo y las etiquetas publicadas solo refieren horas posteriores a origin_at.
La elegibilidad exige evidencia explícita de unidades, método, posición del intervalo y
calidad; sin esa evidencia se publica solo un informe de compatibilidad, nunca etiquetas
aparentemente válidas.
"""

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean as arithmetic_mean
from typing import Annotated, Any, Literal

import duckdb
import typer
from pydantic import BaseModel, ConfigDict, Field, field_validator

from airaware.derived_artifacts import new_bundle, sha256_file
from airaware.event_labels import (
    HourlyPM25,
    LabelPolicy,
    SeriesContext,
    label_window,
    load_policy,
)
from airaware.senamhi_timeline import HOURS_FILE, TIMELINE_VERSION
from airaware.senamhi_windows import CANDIDATES, WINDOWS_FILE, WINDOWS_VERSION

labels_app = typer.Typer(no_args_is_help=True, help="Evaluar etiquetas sobre ventanas reales.")
LABELS_FILE = "labels.parquet"
COMPATIBILITY_FILE = "compatibility.json"
LABELS_VERSION = "senamhi-pm25-window-labels-v1"
COMPATIBILITY_VERSION = "senamhi-pm25-label-compatibility-v1"

# Columnas: 0 window_id, 1 series_id, 2 origin_at, 3 target_start, 4 target_end,
# 5 target_values, 6 target_mean, 7 station_key de la ventana, 8 station_key de la grilla,
# 9 observed_at, 10 value, 11 observation_id, 12 source_observation_ids, 13 status,
# 14 is_missing, 15 is_imputed, 16 quality. Los instantes se leen como hora UTC ingenua
# porque la sesión fija UTC y la grilla declara esa zona; _utc readjunta la zona explícita.
WINDOW_QUERY = """
SELECT w.window_id, w.series_id, w.origin_at::TIMESTAMP, w.target_start::TIMESTAMP,
       w.target_end::TIMESTAMP, w.target_values, w.target_mean, w.station_key,
       g.station_key, g.observed_at::TIMESTAMP, g.value, g.observation_id,
       g.source_observation_ids, g.status, g.is_missing, g.is_imputed, g.quality
FROM read_parquet(?) AS w
JOIN read_parquet(?) AS g
  ON g.series_id = w.series_id AND g.observed_at BETWEEN w.target_start AND w.target_end
WHERE w.series_id = ?
ORDER BY w.origin_at, g.observed_at
"""

COUNTS_QUERY = """
WITH candidates AS ({candidates})
SELECT series_id, count(*) AS candidates,
       count(*) FILTER (WHERE history_complete AND future_complete) AS complete,
       count(*) FILTER (WHERE NOT history_complete) AS history_missing,
       count(*) FILTER (WHERE history_complete AND NOT future_complete) AS future_missing
FROM candidates GROUP BY series_id ORDER BY series_id
"""

LABEL_COLUMNS = (
    "window_id",
    "series_id",
    "station_key",
    "policy_id",
    "kind",
    "origin_at",
    "target_start",
    "target_end",
    "mean_ug_m3",
    "label",
    "valid_hours",
    "required_hours",
    "reason",
    "observation_ids",
    "valid_observation_ids",
    "source_observation_ids",
)

LABEL_COUNTS = {"above_reference": 0, "not_above_reference": 0, "not_evaluable": 0}

# Campos que solo pueden existir en la emisión de etiquetas; si alguno aparece en el paquete
# de entradas (windows.parquet) es una fuga del objetivo y detiene la evaluación.
LABEL_DERIVED_FIELDS = frozenset(
    {
        "kind",
        "label",
        "mean_ug_m3",
        "policy_id",
        "reason",
        "required_hours",
        "valid_hours",
        "observation_ids",
        "valid_observation_ids",
        "source_observation_ids",
    }
)

LEAKAGE_BOUNDARY_QUERY = """
SELECT count(*) FROM read_parquet(?) AS w
WHERE w.history_start > w.origin_at OR w.target_start <= w.origin_at
   OR date_diff('hour', w.origin_at, w.target_end) != ?
"""

LEAKAGE_OVERLAP_QUERY = """
SELECT count(*) FROM read_parquet(?) AS w
JOIN read_parquet(?) AS h
  ON h.series_id = w.series_id AND h.observed_at >= w.history_start
 AND h.observed_at <= w.origin_at AND h.observation_id IS NOT NULL
JOIN read_parquet(?) AS t
  ON t.series_id = w.series_id AND t.observed_at > w.origin_at
 AND t.observed_at <= w.target_end AND t.observation_id = h.observation_id
"""

LEAKAGE_LABEL_HOURS_QUERY = """
WITH refs AS (
    SELECT l.series_id, l.origin_at, unnest(l.observation_ids) AS observation_id
    FROM read_parquet(?) AS l
)
SELECT count(*) FROM refs
LEFT JOIN read_parquet(?) AS g
  ON g.series_id = refs.series_id AND g.observation_id = refs.observation_id
WHERE g.observed_at IS NULL OR g.observed_at <= refs.origin_at
"""

LEAKAGE_LABEL_MEAN_QUERY = """
WITH expanded AS (
    SELECT l.window_id, l.mean_ug_m3, unnest(w.target_values) AS value
    FROM read_parquet(?) AS l
    JOIN read_parquet(?) AS w
      ON w.window_id = l.window_id AND w.series_id = l.series_id
    WHERE l.reason = 'evaluated' AND l.valid_hours = ?
)
SELECT count(*) FROM (
    SELECT window_id, mean_ug_m3, count(*) AS hours, avg(value) AS future_mean
    FROM expanded GROUP BY window_id, mean_ug_m3
)
WHERE hours != ? OR mean_ug_m3 IS NULL OR NOT isfinite(mean_ug_m3)
   OR abs(mean_ug_m3 - future_mean) > 1e-9
"""


class LabelingEvidence(BaseModel):
    """Evidencia explícita para mapear mediciones reales a HourlyPM25; su ausencia bloquea."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    method: Literal["automatic_hourly"]
    interval_position: Literal["hour_ending"]
    unit_evidence: str = Field(min_length=1)
    quality_evidence: str = Field(min_length=1)
    quality_valid_values: tuple[str, ...] = Field(min_length=1)

    @field_validator("quality_valid_values")
    @classmethod
    def _unique_quality_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(value.strip() for value in values)
        if any(not value for value in cleaned) or len(set(cleaned)) != len(cleaned):
            raise ValueError("Los valores de calidad admitidos deben ser únicos y no vacíos")
        return cleaned


def load_evidence(path: Path) -> LabelingEvidence:
    content = path.read_bytes()
    if len(content) > 65536:
        raise ValueError("La evidencia supera 64 KiB")
    return LabelingEvidence.model_validate(json.loads(content))


@dataclass(frozen=True)
class BundleLinks:
    timeline_dir: Path
    windows_dir: Path
    hours: Path
    windows: Path
    timeline_manifest: Any
    windows_manifest: Any
    timeline_sha256: str
    windows_sha256: str
    history_hours: int
    horizon_hours: int
    step_hours: int


def verify_bundle(timeline_dir: Path, windows_dir: Path) -> BundleLinks:
    """Verificar versiones, sumas SHA-256 y el vínculo grilla → ventanas de ambos manifiestos."""
    hours = timeline_dir / HOURS_FILE
    windows = windows_dir / WINDOWS_FILE
    timeline_manifest = json.loads((timeline_dir / "manifest.json").read_text(encoding="utf-8"))
    windows_manifest = json.loads((windows_dir / "manifest.json").read_text(encoding="utf-8"))
    timeline_sha256 = sha256_file(hours)
    windows_sha256 = sha256_file(windows)
    if (
        timeline_manifest.get("version") != TIMELINE_VERSION
        or windows_manifest.get("version") != WINDOWS_VERSION
        or timeline_manifest.get("output_sha256") != timeline_sha256
        or windows_manifest.get("output_sha256") != windows_sha256
    ):
        raise ValueError("Versión o SHA-256 de la grilla o de las ventanas distinto del manifiesto")
    if windows_manifest.get("input_sha256") != timeline_sha256:
        raise ValueError("El vínculo de entrada de las ventanas no coincide con la grilla")
    if timeline_manifest.get("timezone") != "UTC":
        raise ValueError("La grilla debe declarar tiempo universal coordinado")
    if timeline_manifest.get("frequency_hours") != 1:
        raise ValueError("La grilla debe declarar frecuencia horaria de una hora")
    history = windows_manifest.get("history_hours")
    horizon = windows_manifest.get("horizon_hours")
    step = windows_manifest.get("step_hours")
    if (
        type(history) is not int
        or type(horizon) is not int
        or type(step) is not int
        or not 1 <= history <= 168
        or not 1 <= horizon <= 48
        or step < 1
    ):
        raise ValueError("Historia, horizonte o paso fuera del contrato")
    return BundleLinks(
        timeline_dir=timeline_dir,
        windows_dir=windows_dir,
        hours=hours,
        windows=windows,
        timeline_manifest=timeline_manifest,
        windows_manifest=windows_manifest,
        timeline_sha256=timeline_sha256,
        windows_sha256=windows_sha256,
        history_hours=history,
        horizon_hours=horizon,
        step_hours=step,
    )


def _utc(instant: datetime) -> datetime:
    """Readjuntar la zona UTC a la hora ingenua leída de la grilla verificada."""
    if instant.tzinfo is not None:
        raise ValueError("La grilla no debería traer zona horaria en la lectura")
    return instant.replace(tzinfo=UTC)


def verify_no_label_leakage(links: BundleLinks, labels: Path | None = None) -> dict:
    """Verificar que ningún campo derivado de etiquetas entra en las entradas del modelo.

    Las entradas solo pueden usar horas con observed_at <= origin_at (historia) y los
    objetivos solo horas > origin_at; los identificadores del objetivo no pueden repetir
    los de la historia y la media publicada debe reconstruirse con el bloque futuro
    completo. Si se pasa un archivo de etiquetas publicado, también se verifican sus
    identificadores y su media. Cualquier violación detiene el proceso.
    """
    with duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone = 'UTC'")
        inputs = sorted(
            row[0]
            for row in db.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)", [str(links.windows)]
            ).fetchall()
        )
        leaked = sorted(set(inputs) & LABEL_DERIVED_FIELDS)
        if leaked:
            raise ValueError("Campos derivados de etiquetas en las entradas: " + ", ".join(leaked))
        windows_checked = db.execute(
            "SELECT count(*) FROM read_parquet(?)", [str(links.windows)]
        ).fetchone()
        boundary = db.execute(
            LEAKAGE_BOUNDARY_QUERY, [str(links.windows), links.horizon_hours]
        ).fetchone()
        overlaps = db.execute(
            LEAKAGE_OVERLAP_QUERY,
            [str(links.windows), str(links.hours), str(links.hours)],
        ).fetchone()
        if windows_checked is None or boundary is None or overlaps is None:
            raise ValueError("La verificación antifuga no pudo leer el paquete de entradas")
        if boundary[0]:
            raise ValueError("Los límites de la historia o del objetivo no respetan origin_at")
        if overlaps[0]:
            raise ValueError("Identificadores de la historia aparecen en el bloque futuro")
        summary = {
            "label_derived_columns": leaked,
            "windows_checked": windows_checked[0],
            "boundary_violations": boundary[0],
            "history_future_id_overlaps": overlaps[0],
            "labels_checked": 0,
            "label_hours_at_or_before_origin": 0,
            "label_mean_not_future_only": 0,
        }
        if labels is None:
            return summary
        hours_before = db.execute(
            LEAKAGE_LABEL_HOURS_QUERY, [str(labels), str(links.hours)]
        ).fetchone()
        mean_mismatch = db.execute(
            LEAKAGE_LABEL_MEAN_QUERY,
            [str(labels), str(links.windows), links.horizon_hours, links.horizon_hours],
        ).fetchone()
        if hours_before is None or mean_mismatch is None:
            raise ValueError("La verificación antifuga no pudo leer las etiquetas publicadas")
        if hours_before[0]:
            raise ValueError("Etiquetas con horas de la historia o desconocidas en observation_ids")
        if mean_mismatch[0]:
            raise ValueError("La media publicada no se reconstruye con el bloque futuro")
        labels_checked = db.execute(
            "SELECT count(*) FROM read_parquet(?)", [str(labels)]
        ).fetchone()
        summary.update(
            {
                "labels_checked": labels_checked[0] if labels_checked else 0,
                "label_hours_at_or_before_origin": hours_before[0],
                "label_mean_not_future_only": mean_mismatch[0],
            }
        )
        return summary


def _measured_value(*, status, is_missing, is_imputed, value) -> float | None:
    """Solo una medición observada, sin imputar y finita aporta valor; el cero es real."""
    if status != "observed" or is_missing or is_imputed or value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _audit_window(rows: list, *, horizon: int) -> dict:
    """Verificar límites, estación, reconstrucción de valores y promedio de un objetivo."""
    window_id, series_id = rows[0][0], rows[0][1]
    origin_at, target_start, target_end = (_utc(rows[0][i]) for i in (2, 3, 4))
    target_values, target_mean, station = rows[0][5], rows[0][6], rows[0][7]
    if target_start != origin_at + timedelta(hours=1) or target_end != origin_at + timedelta(
        hours=horizon
    ):
        raise ValueError("Los límites del objetivo no corresponden a origin_at más el horizonte")
    hours = [_utc(row[9]) for row in rows]
    if len(hours) != horizon:
        raise ValueError("Las horas del objetivo no están completas en la grilla")
    if len(set(hours)) != horizon:
        raise ValueError("Las horas del objetivo están duplicadas en la grilla")
    if hours != [target_start + timedelta(hours=offset) for offset in range(horizon)]:
        raise ValueError("Las horas del objetivo no coinciden con los límites de la ventana")
    if any(row[8] != station for row in rows):
        raise ValueError("La estación de la grilla difiere de la identidad de la ventana")
    if len(target_values) != horizon or any(value is None for value in target_values):
        raise ValueError("Los valores del objetivo no están completos o contienen nulos")
    measured = [
        value
        for row in rows
        if (
            value := _measured_value(
                status=row[13], is_missing=row[14], is_imputed=row[15], value=row[10]
            )
        )
        is not None
    ]
    if measured != list(target_values):
        raise ValueError("Los valores reconstruidos de la grilla no coinciden con target_values")
    if target_mean is None or not math.isclose(
        arithmetic_mean(measured), target_mean, rel_tol=1e-12, abs_tol=1e-9
    ):
        raise ValueError("El promedio reconstruido del objetivo no coincide con target_mean")
    return {
        "window_id": window_id,
        "series_id": series_id,
        "station_key": station,
        "origin_at": origin_at,
        "target_start": target_start,
        "target_end": target_end,
        "rows": rows,
        "measured_hours": len(measured),
        "complete": len(measured) == horizon,
        "quality_values": {row[16] for row in rows if row[16] is not None},
        "quality_missing": any(row[16] is None for row in rows),
    }


def _iter_window_groups(db, links: BundleLinks, series_id: str, batch_size: int = 4096):
    result = db.execute(WINDOW_QUERY, [str(links.windows), str(links.hours), series_id])
    current_id = None
    group: list = []
    while batch := result.fetchmany(batch_size):
        for row in batch:
            if row[0] != current_id:
                if group:
                    yield group
                current_id, group = row[0], []
            group.append(row)
    if group:
        yield group


def inspect_structure(links: BundleLinks) -> dict:
    """Conciliar conteos y reconstruir cada objetivo; cualquier inconsistencia detiene todo."""
    counts = {
        "windows_total": 0,
        "series_total": 0,
        "measured_complete_windows": 0,
        "target_hours_total": 0,
        "target_hours_measured": 0,
    }
    quality_values: set[str] = set()
    quality_missing = False
    with duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone = 'UTC'")
        parameters = {
            "history": links.history_hours,
            "lookback": links.history_hours - 1,
            "horizon": links.horizon_hours,
            "step": links.step_hours,
        }
        manifest_counts = {
            entry["series_id"]: {
                key: entry[key]
                for key in ("candidates", "complete", "history_missing", "future_missing")
            }
            for entry in links.windows_manifest["counts"]
        }
        recomputed = {
            row[0]: {
                "candidates": row[1],
                "complete": row[2],
                "history_missing": row[3],
                "future_missing": row[4],
            }
            for row in db.execute(
                COUNTS_QUERY.format(candidates=CANDIDATES).format(**parameters),
                [str(links.hours)],
            ).fetchall()
        }
        if recomputed != manifest_counts:
            raise ValueError("Los conteos de candidatos no coinciden con el manifiesto")
        bundle_counts = {
            row[0]: row[1]
            for row in db.execute(
                "SELECT series_id, count(*) FROM read_parquet(?) GROUP BY series_id",
                [str(links.windows)],
            ).fetchall()
        }
        for series_id, entry in manifest_counts.items():
            if bundle_counts.get(series_id, 0) != entry["complete"]:
                raise ValueError("Las ventanas del paquete no coinciden con el manifiesto")
        counts["series_total"] = len(bundle_counts)
        timeline_units = {
            row[0]
            for row in db.execute(
                "SELECT DISTINCT unit FROM read_parquet(?) WHERE parameter_raw = 'PM2_5'",
                [str(links.hours)],
            ).fetchall()
        }
        for series_id in sorted(bundle_counts):
            seen: set[str] = set()
            for group in _iter_window_groups(db, links, series_id):
                audit = _audit_window(group, horizon=links.horizon_hours)
                if audit["window_id"] in seen:
                    raise ValueError("Ventanas duplicadas en el paquete")
                seen.add(audit["window_id"])
                counts["windows_total"] += 1
                counts["target_hours_total"] += links.horizon_hours
                counts["target_hours_measured"] += audit["measured_hours"]
                counts["measured_complete_windows"] += audit["complete"]
                quality_values |= audit["quality_values"]
                quality_missing = quality_missing or audit["quality_missing"]
    return {
        "counts": counts,
        "target_quality_values": quality_values,
        "target_quality_missing": quality_missing,
        "timeline_units": timeline_units,
        "candidate_reconciliation": {
            series_id: {**entry, "windows_in_bundle": bundle_counts.get(series_id, 0)}
            for series_id, entry in manifest_counts.items()
        },
    }


def assess_eligibility(
    links: BundleLinks,
    inspection: dict,
    policy: LabelPolicy,
    evidence: LabelingEvidence | None,
) -> list[str]:
    """Reunir motivos de inadmisibilidad; sin evidencia explícita no se mapea nada real."""
    reasons: list[str] = []
    if links.horizon_hours != policy.period_hours:
        reasons.append("horizon_not_24")
    if not inspection["timeline_units"]:
        reasons.append("empty_pm25_timeline")
    elif any(unit != policy.unit for unit in inspection["timeline_units"]):
        reasons.append("unit_not_admissible")
    if evidence is None:
        reasons.append("labeling_evidence_missing")
        return reasons
    if evidence.timezone != links.timeline_manifest.get("timezone"):
        reasons.append("timezone_mismatch")
    if inspection["target_quality_missing"]:
        reasons.append("quality_missing")
    admitted = set(evidence.quality_valid_values)
    if inspection["target_quality_values"] - admitted:
        reasons.append("quality_values_not_admissible")
    # ADR-005: la calidad desconocida nunca se convierte en quality=valid.
    if any(value.casefold() == "unknown" for value in admitted):
        reasons.append("quality_evidence_unknown_not_admissible")
    return reasons


def _label_row(
    audit: dict,
    policy: LabelPolicy,
    evidence: LabelingEvidence,
    admitted_quality: set[str],
) -> dict:
    context = SeriesContext(
        source_id=evidence.source_id,
        station_id=audit["station_key"],
        unit=policy.unit,
        timezone=evidence.timezone,
        method=evidence.method,
        semantic_evidence=(
            f"units:{evidence.unit_evidence};method:{evidence.method};"
            f"quality:{evidence.quality_evidence}"
        ),
    )
    # Las horas no medidas quedan como huecos; la auditoría estructural exige 24 valores
    # medidos por ventana. quality_valid solo es verdadero si la evidencia admite ese valor.
    records = []
    for row in audit["rows"]:
        value = _measured_value(
            status=row[13], is_missing=row[14], is_imputed=row[15], value=row[10]
        )
        if value is None:
            continue
        records.append(
            HourlyPM25(
                end=_utc(row[9]),
                value=value,
                quality_valid=row[16] in admitted_quality,
                observation_id=row[11],
            )
        )
    result = label_window(
        records,
        start=audit["origin_at"],
        kind="forecast_24h",
        context=context,
        policy=policy,
    )
    return {
        "window_id": audit["window_id"],
        "series_id": audit["series_id"],
        "station_key": audit["station_key"],
        "policy_id": policy.policy_id,
        "kind": "forecast_24h",
        "origin_at": audit["origin_at"],
        "target_start": audit["target_start"],
        "target_end": audit["target_end"],
        "mean_ug_m3": result.mean_ug_m3,
        "label": result.label,
        "valid_hours": result.valid_hours,
        "required_hours": result.required_hours,
        "reason": result.reason,
        "observation_ids": list(result.observation_ids),
        "valid_observation_ids": list(result.valid_observation_ids),
        "source_observation_ids": sorted({sid for row in audit["rows"] for sid in row[12]}),
    }


def _write_labels(
    links: BundleLinks,
    policy: LabelPolicy,
    evidence: LabelingEvidence,
    output_file: Path,
) -> dict:
    counts = dict(LABEL_COUNTS)
    reasons = {reason: 0 for reason in ("evaluated", "insufficient_valid_hours")}
    constructor = {entry["series_id"]: entry for entry in links.windows_manifest["counts"]}
    reconciliation: dict[str, dict] = {}
    admitted_quality = set(evidence.quality_valid_values)
    columns = ", ".join(LABEL_COLUMNS)
    with duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone = 'UTC'")
        db.execute("""
            CREATE TABLE labels (
                window_id VARCHAR, series_id VARCHAR, station_key VARCHAR, policy_id VARCHAR,
                kind VARCHAR, origin_at TIMESTAMPTZ, target_start TIMESTAMPTZ,
                target_end TIMESTAMPTZ, mean_ug_m3 DOUBLE, label VARCHAR, valid_hours BIGINT,
                required_hours BIGINT, reason VARCHAR, observation_ids VARCHAR[],
                valid_observation_ids VARCHAR[], source_observation_ids VARCHAR[]
            )
        """)
        series = [
            row[0]
            for row in db.execute(
                "SELECT DISTINCT series_id FROM read_parquet(?) ORDER BY series_id",
                [str(links.windows)],
            ).fetchall()
        ]
        for series_id in series:
            labeled = [
                _label_row(
                    _audit_window(group, horizon=links.horizon_hours),
                    policy,
                    evidence,
                    admitted_quality,
                )
                for group in _iter_window_groups(db, links, series_id)
            ]
            entry = constructor.get(series_id, {})
            candidates = {
                key: entry.get(key, 0)
                for key in ("candidates", "complete", "history_missing", "future_missing")
            }
            evaluated = sum(1 for row in labeled if row["reason"] == "evaluated")
            discarded = len(labeled) - evaluated
            if candidates["complete"] != evaluated + discarded or candidates["candidates"] != (
                candidates["complete"]
                + candidates["history_missing"]
                + candidates["future_missing"]
            ):
                raise ValueError(
                    "Las etiquetas emitidas no coinciden con las ventanas completas de la serie"
                )
            reconciliation[series_id] = {
                **candidates,
                "labels_evaluated": evaluated,
                "labels_discarded": discarded,
            }
            for row in labeled:
                counts[row["label"]] += 1
                reasons[row["reason"]] += 1
            if labeled:
                placeholders = ", ".join("?" for _ in LABEL_COLUMNS)
                db.executemany(
                    f"INSERT INTO labels VALUES ({placeholders})",
                    [tuple(row[column] for column in LABEL_COLUMNS) for row in labeled],
                )
        db.execute(
            f"COPY (SELECT {columns} FROM labels ORDER BY series_id, origin_at) "
            "TO ? (FORMAT PARQUET)",
            [str(output_file)],
        )
    return {"labels": counts, "reasons": reasons, "reconciliation": reconciliation}


def evaluate_windows(
    timeline_dir: Path,
    windows_dir: Path,
    policy_path: Path,
    output: Path,
    *,
    evidence: LabelingEvidence | None = None,
) -> dict:
    """Inspeccionar el paquete, decidir elegibilidad y publicar etiquetas o el informe."""
    policy_sha256 = sha256_file(policy_path)
    policy = load_policy(policy_path)
    links = verify_bundle(timeline_dir, windows_dir)
    leakage = verify_no_label_leakage(links)
    inspection = inspect_structure(links)
    reasons = assess_eligibility(links, inspection, policy, evidence)
    counts = dict(inspection["counts"])
    counts["labels"] = dict(LABEL_COUNTS)
    counts["label_reasons"] = {"evaluated": 0, "insufficient_valid_hours": 0}
    reconciliation: dict[str, dict] = {}
    common = {
        "policy_id": policy.policy_id,
        "policy_sha256": policy_sha256,
        "evidence": evidence.model_dump(mode="json") if evidence is not None else None,
        "timeline_version": links.timeline_manifest["version"],
        "windows_version": links.windows_manifest["version"],
        "timeline_sha256": links.timeline_sha256,
        "windows_sha256": links.windows_sha256,
        "history_hours": links.history_hours,
        "horizon_hours": links.horizon_hours,
        "step_hours": links.step_hours,
        "leakage": leakage,
    }
    with new_bundle(output) as staging:
        if reasons:
            output_file = staging / COMPATIBILITY_FILE
            compatibility = {
                "version": COMPATIBILITY_VERSION,
                "labeling": "inadmissible",
                "nota": (
                    "Informe de compatibilidad. La completitud estructural no valida unidades, "
                    "semántica temporal ni calidad de las mediciones; no se generaron etiquetas "
                    "ni afirmaciones de seguridad o cumplimiento."
                ),
                "blocked_reasons": reasons,
                "data": {
                    "target_quality_values": sorted(inspection["target_quality_values"]),
                    "target_quality_missing": inspection["target_quality_missing"],
                    "timeline_units": sorted(inspection["timeline_units"]),
                },
                "counts": counts,
                "candidate_reconciliation": inspection["candidate_reconciliation"],
                **common,
            }
            output_file.write_text(
                json.dumps(compatibility, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            labeling = "blocked"
        else:
            if evidence is None:
                raise ValueError("La etiqueta admitida requiere evidencia de etiquetado")
            output_file = staging / LABELS_FILE
            written = _write_labels(links, policy, evidence, output_file)
            counts["labels"] = written["labels"]
            counts["label_reasons"] = written["reasons"]
            if sum(counts["labels"].values()) != counts["windows_total"]:
                raise ValueError("El número de etiquetas no coincide con las ventanas auditadas")
            leakage = verify_no_label_leakage(links, labels=output_file)
            reconciliation = written["reconciliation"]
            labeling = "evaluated"
        if (
            sha256_file(links.hours) != links.timeline_sha256
            or sha256_file(links.windows) != links.windows_sha256
        ):
            raise ValueError("La grilla o las ventanas cambiaron durante la evaluación")
        if sha256_file(policy_path) != policy_sha256:
            raise ValueError("La política cambió durante la evaluación")
        manifest = {
            "version": LABELS_VERSION,
            "labeling": labeling,
            "blocked_reasons": reasons,
            "counts": counts,
            "output_sha256": sha256_file(output_file),
            **common,
            "leakage": leakage,
        }
        if reconciliation:
            manifest["labels_reconciliation"] = reconciliation
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return {
        "labeling": labeling,
        "blocked_reasons": reasons,
        "counts": counts,
        "output": str(output),
    }


@labels_app.command("senamhi")
def senamhi_labels(
    timeline: Annotated[Path, typer.Option(help="Carpeta de grilla horaria verificada.")],
    windows: Annotated[Path, typer.Option(help="Carpeta de ventanas de pronóstico y manifiesto.")],
    output: Annotated[Path, typer.Option(help="Carpeta nueva de etiquetas o informe.")],
    policy: Annotated[Path, typer.Option(help="Configuración del umbral versionado.")] = Path(
        "configs/thresholds.yaml"
    ),
    evidence: Annotated[
        Path | None, typer.Option(help="JSON de evidencia semántica; si falta, se bloquea.")
    ] = None,
) -> None:
    """Evaluar etiquetas forecast_24h sobre ventanas reales, con elegibilidad cerrada."""
    try:
        loaded = load_evidence(evidence) if evidence is not None else None
        summary = evaluate_windows(timeline, windows, policy, output, evidence=loaded)
    except (OSError, ValueError, KeyError, duckdb.Error) as error:
        typer.echo(f"No se pudieron evaluar etiquetas: {error}", err=True)
        raise typer.Exit(1) from None
    typer.echo(json.dumps(summary, indent=2, sort_keys=True))
