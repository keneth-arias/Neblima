"""Simular avisos por estación respetando el orden de emisión y el horizonte de seis horas."""

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median, quantiles
from typing import TypedDict


@dataclass(frozen=True)
class Origin:
    """Horas UTC desde la época, lectura disponible al emitir y probabilidad calibrada."""

    hour: int
    issued: float
    probability: float | None
    latest: float | None


class WarningReport(TypedDict):
    counts: dict[str, int]
    cohort_sha256: str
    min_lead: float
    cooldown: float
    cut: float
    expired_origins: int
    excluded_onsets: list[int]
    unanchored_high: list[int]
    evaluable_origins: int
    emitted: int
    late: int
    delayed_emissions: int
    emission_delays: list[float]
    matched_onsets: list[int]
    observable_onsets: list[int]
    lead_hours: list[float]
    false_per_station_week: float | None
    calendar_fraction: float | None


def evaluate(
    origins: Sequence[Origin],
    observations: Mapping[int, float | None],
    threshold: float,
    cut: float,
    *,
    cooldown: float = 6,
    min_lead: float = 0,
) -> WarningReport:
    if (
        not math.isfinite(threshold)
        or not 0 <= cut <= 1
        or not math.isfinite(cooldown)
        or cooldown < 0
        or not math.isfinite(min_lead)
        or min_lead < 0
    ):
        raise ValueError("Umbral, corte, pausa o anticipación inválidos")
    if len({row.hour for row in origins}) != len(origins):
        raise ValueError("Origen duplicado para esta estación")
    known = {h: v for h, v in observations.items() if v is not None and math.isfinite(v)}
    onsets = {
        h
        for h, v in known.items()
        if v >= threshold and h - 1 in known and known[h - 1] < threshold
    }
    counts = dict.fromkeys(
        ("hit", "false", "indeterminate", "active", "suppressed", "below_cut", "abstained"), 0
    )
    matched: list[int] = []
    eligible: set[int] = set()
    leads: list[float] = []
    emission_delays = []
    next_issue = -math.inf
    opportunities = late = expired = 0
    cohort = []
    for row in sorted(origins, key=lambda o: (o.issued, o.hour)):
        if not math.isfinite(row.issued) or row.issued < row.hour:
            raise ValueError("La emisión precede al origen o no es finita")
        cohort.append(
            (
                row.hour,
                row.issued,
                row.latest if row.latest is not None and math.isfinite(row.latest) else None,
                [known.get(h) for h in range(row.hour, row.hour + 7)],
            )
        )
        if row.issued >= row.hour + 6 or row.hour + 6 - row.issued < min_lead:
            expired += 1
            counts["abstained"] += 1
            continue
        if row.latest is None or not math.isfinite(row.latest):
            counts["abstained"] += 1
            continue
        if row.latest >= threshold:
            counts["active"] += 1
            continue
        horizon = range(row.hour + 1, row.hour + 7)
        complete = all(h in known for h in range(row.hour, row.hour + 7))
        future = [
            h for h in horizon if h in onsets and h > row.issued and h - row.issued >= min_lead
        ]
        if complete:
            opportunities += 1
            eligible.update(future)
        if row.probability is None:
            counts["abstained"] += 1
            continue
        if not 0 <= row.probability <= 1:
            raise ValueError("Probabilidad fuera de rango")
        if row.probability < cut:
            counts["below_cut"] += 1
            continue
        if row.issued < next_issue:
            counts["suppressed"] += 1
            continue
        next_issue = row.issued + cooldown
        emission_delays.append(row.issued - row.hour)
        if not complete:
            counts["indeterminate"] += 1
            continue
        first = next((h for h in future if h not in matched), None)
        late += int(any(h in onsets and h <= row.issued for h in horizon))
        if first is None:
            counts["false"] += 1
        else:
            counts["hit"] += 1
            matched.append(first)
            leads.append(first - row.issued)
    span = max((r.hour for r in origins), default=0) - min((r.hour for r in origins), default=0) + 1
    return {
        "counts": counts,
        "cohort_sha256": hashlib.sha256(
            json.dumps([threshold, cooldown, min_lead, cohort], allow_nan=False).encode()
        ).hexdigest(),
        "min_lead": min_lead,
        "cooldown": cooldown,
        "cut": cut,
        "expired_origins": expired,
        "excluded_onsets": sorted(onsets - eligible),
        "unanchored_high": sorted(
            h for h, v in known.items() if v >= threshold and h - 1 not in known
        ),
        "evaluable_origins": opportunities,
        "emitted": sum(counts[k] for k in ("hit", "false", "indeterminate")),
        "late": late,
        "delayed_emissions": sum(delay > 0 for delay in emission_delays),
        "emission_delays": emission_delays,
        "observable_onsets": sorted(eligible),
        "matched_onsets": matched,
        "lead_hours": leads,
        "false_per_station_week": 168 * counts["false"] / opportunities if opportunities else None,
        "calendar_fraction": opportunities / span if origins else None,
    }


@dataclass(frozen=True)
class WarningRule:
    sha256: str
    min_lead: float
    cooldown: float
    budget: float
    max_brier_excess: float

    @classmethod
    def read(cls, path: Path, expected_sha256: str) -> "WarningRule":
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("La huella de la regla de selección difiere")
        spec = json.loads(raw)
        if (
            spec["version"] != "lima-regla-inicios-v1"
            or spec["reference"] != "calibrated_forecast_max_minus_threshold"
            or spec["ties"] != "retain_reference"
        ):
            raise ValueError("Versión, referencia o desempate de regla incompatible")
        rule = cls(
            expected_sha256,
            spec["minimum_lead_hours"],
            spec["cooldown_hours"],
            spec["max_false_per_168_evaluable_origins"],
            spec["maximum_brier_excess_over_training_frequency"],
        )
        for value in (rule.min_lead, rule.cooldown, rule.budget, rule.max_brier_excess):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Criterio de selección inválido")
        if rule.min_lead > 6 or rule.max_brier_excess > 1:
            raise ValueError("Anticipación o tolerancia de Brier fuera del rango")
        return rule


class Policy(TypedDict):
    rule_sha256: str
    method: str
    cut: float
    detected: int
    median_lead: float | None


def select_policy(
    candidates: Sequence[tuple[str, float, Mapping[str, WarningReport]]],
    *,
    calibration: Mapping[str, Mapping[str, tuple[float, float] | None]],
    rule: WarningRule,
) -> Policy | None:
    """Aplicar el presupuesto por estación y conservar la referencia ante empate."""
    refs = [stations for method, _, stations in candidates if method == "reference"]
    if not refs or not refs[0]:
        return None
    common = {key: s["cohort_sha256"] for key, s in refs[0].items()}
    options: list[Policy] = []
    for method, cut, stations in candidates:
        if method not in ("reference", "episode"):
            raise ValueError("Método de aviso desconocido")
        if not 0 <= cut <= 1 or any(s["cut"] != cut for s in stations.values()):
            raise ValueError("El corte declarado difiere del aplicado")
        if any(
            s["min_lead"] != rule.min_lead or s["cooldown"] != rule.cooldown
            for s in stations.values()
        ):
            raise ValueError("Anticipación o pausa incompatibles con la regla congelada")
        if {key: s["cohort_sha256"] for key, s in stations.items()} != common:
            raise ValueError("Los métodos deben compartir estaciones y oportunidades")
        evidence = calibration.get(method, {})
        if set(evidence) != set(stations):
            continue
        calibrated = True
        for station, measures in evidence.items():
            if measures is None:
                if stations[station]["evaluable_origins"]:
                    calibrated = False
                continue
            brier, frequency_brier = measures
            reference = calibration.get("reference", {}).get(station)
            if reference is not None and reference[1] != frequency_brier:
                raise ValueError("La referencia de frecuencia debe ser común por estación")
            if not (
                0 <= brier <= 1
                and 0 <= frequency_brier <= 1
                and brier - frequency_brier <= rule.max_brier_excess
            ):
                calibrated = False
        if not calibrated:
            continue
        if not stations or any(
            168 * s["counts"]["false"] > rule.budget * s["evaluable_origins"]
            for s in stations.values()
        ):
            continue
        leads = [lead for s in stations.values() for lead in s["lead_hours"]]
        options.append(
            {
                "method": method,
                "cut": cut,
                "rule_sha256": rule.sha256,
                "detected": sum(len(s["matched_onsets"]) for s in stations.values()),
                "median_lead": float(median(leads)) if leads else None,
            }
        )
    if not any(p["method"] == "reference" for p in options):
        return None
    return max(
        (p for p in options if p["detected"] > 0),
        key=lambda p: (p["detected"], p["method"] == "reference", p["median_lead"] or 0, p["cut"]),
        default=None,
    )


def paired_interval(
    hours: Sequence[int],
    first: Sequence[float],
    second: Sequence[float],
    *,
    block_hours: int = 168,
    draws: int = 1000,
    seed: int = 27,
) -> dict[str, int | float | None]:
    """IC percentil de la diferencia media con bloques calendario comunes a las estaciones."""
    import random

    if not (len(hours) == len(first) == len(second)) or block_hours <= 0 or draws < 2:
        raise ValueError("Series pareadas o remuestreo inválidos")
    totals: dict[int, tuple[float, int]] = {}
    for hour, a, b in zip(hours, first, second, strict=True):
        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError("Las contribuciones deben estar emparejadas y ser finitas")
        block = hour // block_hours
        value, count = totals.get(block, (0.0, 0))
        totals[block] = (value + a - b, count + 1)
    values = [totals[k] for k in sorted(totals)]
    result: dict[str, int | float | None] = {
        "blocks": len(values),
        "difference": sum(t for t, _ in values) / len(hours) if hours else None,
        "lower": None,
        "upper": None,
    }
    if len(values) > 1:
        rng = random.Random(seed)
        samples = []
        for _ in range(draws):
            sample = rng.choices(values, k=len(values))
            samples.append(sum(v for v, _ in sample) / sum(n for _, n in sample))
        percentiles = quantiles(samples, n=40, method="inclusive")
        result.update(lower=percentiles[0], upper=percentiles[-1])
    return result


def paired_detection(
    first: Mapping[str, WarningReport],
    second: Mapping[str, WarningReport],
    *,
    block_hours: int = 168,
):
    """Emparejar en la cronología completa y remuestrear cada inicio en su hora."""
    if set(first) != set(second):
        raise ValueError("Estaciones no emparejadas")
    hours, a, b = [], [], []
    for station, left in first.items():
        right = second[station]
        if (
            left["cohort_sha256"] != right["cohort_sha256"]
            or left["observable_onsets"] != right["observable_onsets"]
        ):
            raise ValueError("Inicios no emparejados")
        detected_left, detected_right = set(left["matched_onsets"]), set(right["matched_onsets"])
        for hour in left["observable_onsets"]:
            hours.append(hour)
            a.append(float(hour in detected_left))
            b.append(float(hour in detected_right))
    return paired_interval(hours, a, b, block_hours=block_hours)


def replay_fixture(inputs, evaluation) -> dict[str, WarningReport]:
    """Evaluar una política sintética que siempre propone aviso para verificar la contabilidad."""
    import json
    from datetime import datetime

    histories = json.loads(inputs.read_text())
    outcomes = json.loads(evaluation.read_text())
    if (
        outcomes["version"] != "lima-episode-fixture-v1"
        or histories["version"] != outcomes["version"]
        or histories["unit"] != "ug/m3"
    ):
        raise ValueError("Se requiere el ejemplo sintético versionado de AirAware")
    by_id = {row["window_id"]: row for row in outcomes["rows"]}
    if len(by_id) != len(outcomes["rows"]) or set(by_id) != set(histories["window_id"]):
        raise ValueError("Objetivos e historias difieren")
    rows: dict[str, list[Origin]] = {}
    observations: dict[str, dict[int, float | None]] = {}
    limits: dict[str, float] = {}
    for wid, station, stamp, history, limit in zip(
        *(
            histories[k]
            for k in ("window_id", "station_key", "origin_at", "history", "threshold_ug_m3")
        ),
        strict=True,
    ):
        hour = int(datetime.fromisoformat(stamp).timestamp()) // 3600
        rows.setdefault(station, []).append(Origin(hour, float(hour), 1.0, float(history[-1])))
        if limits.setdefault(station, limit) != limit:
            raise ValueError("Umbral inestable por estación")
        values = observations.setdefault(station, {})
        answer = by_id[wid]
        future = answer["targets"]
        if len(history) != 24 or len(future) != 6:
            raise ValueError("Dimensiones del ejemplo incompatibles")
        event = onset = None
        if None not in future:
            event = max(future) >= limit
            transitions = zip([history[-1], *future[:-1]], future, strict=True)
            onset = next((n for n, (a, b) in enumerate(transitions, 1) if a < limit <= b), None)
        if (answer["event"], answer["first_onset_hour"], answer["ongoing_at_origin"]) != (
            event,
            onset,
            history[-1] >= limit,
        ):
            raise ValueError("La solución publicada difiere de las lecturas sintéticas")
        for offset, value in enumerate([history[-1], *future]):
            if values.setdefault(hour + offset, value) != value:
                raise ValueError("Observaciones inconsistentes en una hora compartida")
    return {s: evaluate(frames, observations[s], limits[s], 1.0) for s, frames in rows.items()}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("observations", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay_fixture(args.inputs, args.observations), sort_keys=True, indent=2))
