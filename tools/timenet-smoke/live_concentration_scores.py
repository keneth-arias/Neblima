"""Puntaje provisional de pronósticos emitidos en Campo de Marte al corte de recepción elegido."""

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import fmean

from station_receipts import audit

STATION = "Campo de Marte / 112194"


def instant(value):
    time = datetime.fromisoformat(value)
    if time.tzinfo is None:
        raise ValueError("La emisión, la recepción y el corte requieren zona horaria")
    return time.astimezone(UTC)


def metrics(rows, version):
    scored = [(row, row[version]) for row in rows if row[version] is not None]
    n = len(scored)
    return {
        "pairs": n,
        "distinct_target_hours": len({r["label"] for r, _ in scored}),
        "qwen_mae": fmean(abs(r["qwen"] - y) for r, y in scored) if n else None,
        "persistence_mae": fmean(abs(r["last"] - y) for r, y in scored) if n else None,
        "coverage80": fmean(r["lo"] <= y <= r["hi"] for r, y in scored) if n else None,
        "mean_width80": fmean(r["hi"] - r["lo"] for r, _ in scored) if n else None,
    }


def summary(rows):
    return {
        "first": metrics(rows, "first"),
        "latest": metrics(rows, "latest"),
        "mean_seconds_to_first_receipt": fmean(r["seconds"] for r in rows) if rows else None,
    }


def summarize(issues, changes, through):
    cutoff = instant(through)
    versions = defaultdict(dict)
    for change in changes:
        arrival = instant(change["seen_utc"])
        if arrival > cutoff:
            continue
        value = change["value"]
        series = versions[change["station_hour"]]
        if value is not None and not math.isfinite(value):
            raise ValueError("La recepción tiene una medición no finita")
        if arrival in series and series[arrival] != value:
            raise ValueError("Hay dos versiones de la misma lectura en una recepción")
        series[arrival] = value

    observations = {}
    for label, series in versions.items():
        ordered = sorted(series.items())
        first = next(((at, y) for at, y in ordered if y is not None), None)
        if first is not None:
            observations[label] = (*first, ordered[-1][1])

    counts = Counter(
        dict.fromkeys(("available_before_issue", "awaiting_first", "observed", "withdrawn"), 0)
    )
    rows, origins, checkpoints = [], set(), set()
    for issue in issues:
        issued = instant(issue["issued_at_utc"])
        if issued > cutoff:
            continue
        origin = datetime.fromisoformat(issue["origin"])
        last = issue["last_ug_m3"]
        if (
            issue["station"] != STATION
            or issue["mode"] != "private_live_shadow"
            or issue["unit"] != "ug/m3"
            or origin.tzinfo is not None
            or origin != origin.replace(minute=0, second=0, microsecond=0)
            or origin in origins
            or instant(issue["input_cutoff_utc"]) > issued
            or not isinstance(issue["checkpoint_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", issue["checkpoint_sha256"])
            or not math.isfinite(last)
        ):
            raise ValueError(
                "Emisión repetida o incompatible con la estación, la unidad o el reloj"
            )
        origins.add(origin)
        checkpoints.add(issue["checkpoint_sha256"])
        for h, point in zip(range(1, 7), issue["hours"], strict=True):
            label = (origin + timedelta(hours=h)).isoformat()
            pred, lo, hi = point["qwen"], point["lower80"], point["upper80"]
            if (
                point["station_label"] != label
                or not all(map(math.isfinite, (pred, lo, hi)))
                or lo > hi
            ):
                raise ValueError("Horizonte, predicción o intervalo inválido")
            if label not in observations:
                counts["awaiting_first"] += 1
                continue
            arrived, first, latest = observations[label]
            if arrived <= issued:
                counts["available_before_issue"] += 1
                continue
            counts["withdrawn" if latest is None else "observed"] += 1
            rows.append(
                {
                    "h": h,
                    "label": label,
                    "seconds": (arrived - issued).total_seconds(),
                    "qwen": pred,
                    "last": last,
                    "lo": lo,
                    "hi": hi,
                    "first": first,
                    "latest": latest,
                }
            )
    if len(checkpoints) > 1:
        raise ValueError("La comparación contiene varias generaciones del modelo")
    return {
        "version": "campo-pm25-puntaje-provisional-v1",
        "station": "112194",
        "unit": "ug/m3",
        "through_utc": cutoff.isoformat(),
        "issued": len(origins),
        "checkpoint_sha256": next(iter(checkpoints), None),
        "counts": dict(counts),
        "overall": summary(rows),
        "by_horizon": [
            {"forecast_hour": h, **summary([row for row in rows if row["h"] == h])}
            for h in range(1, 7)
        ],
    }


def report(issuances, receipts, through):
    """Auditar los recibos hasta el corte y fijar la identidad de las emisiones puntuadas."""
    if not issuances.is_dir():
        raise ValueError("Falta la carpeta de emisiones")
    observations = audit(receipts, through=through, include_receipts=True, allow_empty=True)
    cutoff = instant(through)
    receipt_at = {instant(r["seen_utc"]): r["receipt_sha256"] for r in observations["receipts"]}
    issues, fingerprints = [], []
    for path in sorted(issuances.glob("*.json")):
        raw = path.read_bytes()
        issue = json.loads(raw)
        if instant(issue["issued_at_utc"]) <= cutoff:
            input_time = instant(issue["input_cutoff_utc"])
            if input_time not in receipt_at or issue["receipt_sha256"] != receipt_at[input_time]:
                raise ValueError("El corte de insumos de la emisión difiere del recibo de SENAMHI")
            issues.append(issue)
            fingerprints.append(hashlib.sha256(raw).hexdigest())
    result = summarize(issues, observations["changes"], through)
    result["issuance_sha256"] = fingerprints
    result["source_receipts_sha256"] = [r["receipt_sha256"] for r in observations["receipts"]]
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("emisiones", type=Path)
    cli.add_argument("recibos", type=Path)
    cli.add_argument("--through", required=True, help="Corte de evaluación con zona horaria")
    args = cli.parse_args()
    print(
        json.dumps(
            report(args.emisiones, args.recibos, args.through),
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )
