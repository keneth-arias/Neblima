"""Congelar la selección histórica para una prueba posterior por estación."""

import argparse
import hashlib
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml

from airaware.episode_forecast_selection import decide, read_pair


def checked(path: Path, digest: str) -> bytes:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"La huella difiere para {path.name}")
    return raw


def bind(protocol_path, protocol_sha, rule_path, decision_path, decision_sha, pairs, calibrator):
    protocol = json.loads(checked(protocol_path, protocol_sha))
    if protocol["version"] != "lima-prueba-futura-campo-marte-v1":
        raise ValueError("Protocolo de prueba desconocido")
    rule = yaml.safe_load(checked(rule_path, protocol["selection_rule_sha256"]))
    evidence = [read_pair(rule, *paths) for paths in pairs]
    choice = decide(rule, evidence)
    choice.update(
        rule_sha256=protocol["selection_rule_sha256"], blocks_sha256=rule["blocks_sha256"]
    )
    recorded = json.loads(checked(decision_path, decision_sha))
    if recorded != choice:
        raise ValueError("La selección registrada difiere de las dos comparaciones pareadas")
    i = next(i for i, row in enumerate(evidence) if row["seed"] == choice["seed"])
    row = evidence[i]
    report = json.loads(checked(pairs[i][0], row["report_sha256"]))
    cal_sha = report.get("reference_calibrator_sha256")
    if not isinstance(cal_sha, str) or len(cal_sha) != 64:
        raise ValueError("El informe pareado debe identificar el calibrador directo por su huella")
    cal = json.loads(checked(calibrator, cal_sha))
    residuals = cal["residual_q10_q90"]
    if (
        cal["version"] != "pm25-six-hour-calibration-v1"
        or cal["unit"] != protocol["unit"]
        or cal["manifest_sha256"] != rule["blocks_sha256"]
        or cal["checkpoint_sha256"] != row["direct_checkpoint_sha256"]
        or cal["thresholds_sha256"] != protocol["thresholds_sha256"]
        or len(residuals) != 2
        or any(len(r) != 6 or not all(math.isfinite(x) for x in r) for r in residuals)
        or any(lo > hi for lo, hi in zip(*residuals, strict=True))
    ):
        raise ValueError("Calibrador incompatible con el control directo de la semilla fijada")
    head = choice["selected"]
    return {
        "version": "lima-concentracion-prueba-congelada-v1",
        "scope": protocol["scope"],
        "protocol_sha256": protocol_sha,
        "decision_sha256": decision_sha,
        "selection_rule_sha256": choice["rule_sha256"],
        "blocks_sha256": choice["blocks_sha256"],
        "seed": choice["seed"],
        "head": head,
        "image": protocol["image"],
        "base_weights_sha256": row["base_weights_sha256"],
        "model_revision": row["model_revision"],
        "checkpoint_sha256": row[head + "_checkpoint_sha256"],
        "thresholds_sha256": protocol["thresholds_sha256"],
        "interval_method": "calibration_residuals" if head == "direct" else "quantile_head",
        "direct_calibrator_sha256": cal_sha,
    }, datetime.fromisoformat(protocol["seal_before_utc"])


def publish(path: Path, binding: dict, deadline: datetime) -> dict:
    def existing():
        record = json.loads(path.read_bytes())
        sealed = datetime.fromisoformat(record.pop("sealed_at_utc"))
        if sealed >= deadline or record != binding:
            raise ValueError("El destino contiene otra versión o una congelación fuera de plazo")
        return {**record, "sealed_at_utc": sealed.isoformat()}

    if path.exists():
        return existing()
    with NamedTemporaryFile(dir=path.parent) as tmp:
        now = datetime.now(UTC)
        if now >= deadline:
            raise ValueError("Venció el plazo para congelar la selección")
        record = {**binding, "sealed_at_utc": now.isoformat()}
        tmp.write(
            (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        )
        tmp.flush()
        try:
            os.link(tmp.name, path)
        except FileExistsError:
            return existing()
    return record


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "rule", "decision", "calibrator", "output"):
        p.add_argument(name, type=Path)
    p.add_argument("--protocol-sha256", required=True)
    p.add_argument("--decision-sha256", required=True)
    p.add_argument(
        "--pair",
        type=Path,
        nargs=4,
        action="append",
        required=True,
        metavar=("INFORME", "CUANTILES", "DIRECTO", "PAQUETE_DIRECTO"),
    )
    a = p.parse_args()
    binding, deadline = bind(
        a.protocol, a.protocol_sha256, a.rule, a.decision, a.decision_sha256, a.pair, a.calibrator
    )
    publish(a.output, binding, deadline)
