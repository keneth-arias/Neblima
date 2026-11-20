"""Simular avisos por estación respetando el orden de emisión y el horizonte de seis horas."""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import median
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
    evaluable_origins: int
    emitted: int
    late: int
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
    next_issue = -math.inf
    opportunities = late = 0
    for row in sorted(origins, key=lambda o: (o.issued, o.hour)):
        if not math.isfinite(row.issued) or row.issued < row.hour:
            raise ValueError("La emisión precede al origen o no es finita")
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
        if not complete:
            counts["indeterminate"] += 1
            continue
        first = next((h for h in future if h not in matched), None)
        if first is None:
            counts["false"] += 1
            late += int(any(h in onsets and h <= row.issued for h in horizon))
        else:
            counts["hit"] += 1
            matched.append(first)
            leads.append(first - row.issued)
    span = max((r.hour for r in origins), default=0) - min((r.hour for r in origins), default=0) + 1
    return {
        "counts": counts,
        "evaluable_origins": opportunities,
        "emitted": sum(counts[k] for k in ("hit", "false", "indeterminate")),
        "late": late,
        "observable_onsets": sorted(eligible),
        "matched_onsets": matched,
        "lead_hours": leads,
        "false_per_station_week": 168 * counts["false"] / opportunities if opportunities else None,
        "calendar_fraction": opportunities / span if origins else None,
    }


class Policy(TypedDict):
    method: str
    cut: float
    detected: int
    median_lead: float | None


def select_policy(
    candidates: Sequence[tuple[str, float, Mapping[str, WarningReport]]], *, budget: float = 1
) -> Policy | None:
    """Aplicar el presupuesto por estación y conservar la referencia ante empate."""
    options: list[Policy] = []
    for method, cut, stations in candidates:
        if not stations or any(
            not s["evaluable_origins"]
            or 168 * s["counts"]["false"] > budget * s["evaluable_origins"]
            for s in stations.values()
        ):
            continue
        leads = [lead for s in stations.values() for lead in s["lead_hours"]]
        options.append(
            {
                "method": method,
                "cut": cut,
                "detected": sum(len(s["matched_onsets"]) for s in stations.values()),
                "median_lead": float(median(leads)) if leads else None,
            }
        )
    return max(
        options,
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
    values = list(totals.values())
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
        samples.sort()
        result.update(
            lower=samples[math.floor(0.025 * (draws - 1))],
            upper=samples[math.ceil(0.975 * (draws - 1))],
        )
    return result


def replay_fixture(inputs, evaluation) -> dict[str, WarningReport]:
    """Evaluar una política sintética que siempre propone aviso para verificar la contabilidad."""
    import json
    from datetime import datetime

    histories = json.loads(inputs.read_text())
    outcomes = json.loads(evaluation.read_text())
    if (
        outcomes["version"] != "lima-episode-fixture-v1"
        or histories["version"] != outcomes["version"]
    ):
        raise ValueError("Se requiere el ejemplo sintético versionado de AirAware")
    by_id = {row["window_id"]: row["targets"] for row in outcomes["rows"]}
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
        for offset, value in enumerate([history[-1], *by_id[wid]]):
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
