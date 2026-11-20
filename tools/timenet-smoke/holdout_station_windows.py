"""Preparar las historias y los objetivos reservados de Campo de Marte al corte registrado."""

import argparse
import fcntl
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from episode_calibration import check_file
from station_receipts import audit

HOUR = timedelta(hours=1)


def write_json(path, obj):
    path.write_text(json.dumps(obj, allow_nan=False, indent=2, sort_keys=True) + "\n")


def cohort(protocol, observations):
    start = datetime.fromisoformat(protocol["origin_start_inclusive"])
    end = datetime.fromisoformat(protocol["origin_stop_exclusive"])
    if (
        start.tzinfo is not None
        or end.tzinfo is not None
        or (protocol["history_hours"], protocol["forecast_hours"], protocol["schedule_hours"])
        != (24, 6, 168)
        or end - start != 168 * HOUR
    ):
        raise ValueError("Se requieren 168 orígenes en el reloj publicado y ventanas H24/F6")
    hours = {datetime.fromisoformat(r["station_hour"]): r["value"] for r in observations}
    origins, histories, targets, ids = [], [], [], []
    for i in range(168):
        origin = start + i * HOUR
        key = f"112194/{origin.isoformat()}"
        h = [hours.get(origin - j * HOUR) for j in range(23, -1, -1)]
        missing = h.count(None)
        origins.append(
            {"window_id": key, "missing_history_hours": missing, "eligible": missing == 0}
        )
        if not missing:
            ids.append(key)
            histories.append(h)
            targets.append([hours.get(origin + j * HOUR) for j in range(1, 7)])
    return (
        origins,
        np.asarray(ids, dtype=str),
        np.asarray(histories, dtype="f4").reshape(-1, 24),
        np.asarray(targets, dtype="f8").reshape(-1, 6),
    )


def prepare(protocol_path, protocol_sha, seal_path, seal_sha, root, output, now):
    protocol = json.loads(check_file(protocol_path, protocol_sha).read_bytes())
    seal = json.loads(check_file(seal_path, seal_sha).read_bytes())
    vintage = datetime.fromisoformat(protocol["observation_vintage_utc"])
    if (
        protocol["version"] != "lima-prueba-futura-campo-marte-v1"
        or protocol["scope"] != "retrospective_concentration_only"
        or (protocol["feed"], protocol["station_code"], protocol["parameter"], protocol["unit"])
        != ("senamhi_horario", "112194", "N_PM25", "ug/m3")
        or protocol["clock"] != "published_station_labels"
        or seal["version"] != "lima-concentracion-prueba-congelada-v1"
        or seal["scope"] != protocol["scope"]
        or seal["protocol_sha256"] != protocol_sha
        or seal["image"] != protocol["image"]
        or seal["head"] not in ("direct", "quantile")
        or datetime.fromisoformat(seal["sealed_at_utc"])
        >= datetime.fromisoformat(protocol["seal_before_utc"])
        or now < vintage
    ):
        raise ValueError("Protocolo, sello o fecha de apertura incompatibles")
    observed = audit(root, through=vintage.isoformat(), include_receipts=True)
    origins, ids, histories, targets = cohort(protocol, observed["changes"])
    with (output.parent / f".{output.name}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if output.exists():
            raise FileExistsError(output)
        with TemporaryDirectory(dir=output.parent) as tmp:
            stage = Path(tmp) / "cohorte"
            infer, scoring = stage / "infer", stage / "scoring"
            infer.mkdir(parents=True)
            scoring.mkdir()
            np.savez(infer / "data.npz", window_id=ids, history=histories)
            np.savez(scoring / "observed.npz", window_id=ids, observed=targets)
            write_json(scoring / "origins.json", origins)
            spec = {
                "phase": "infer",
                "head": seal["head"],
                "block": "external_test",
                "schema": "forecast-input-v1",
                "unit": protocol["unit"],
                "checkpoint_sha256": seal["checkpoint_sha256"],
                "weights_manifest_sha256": seal["base_weights_sha256"],
                "seal_sha256": seal_sha,
                "files": {
                    "data.npz": hashlib.sha256((infer / "data.npz").read_bytes()).hexdigest()
                },
            }
            write_json(infer / "manifest.json", spec)
            receipt = {
                "version": "lima-cohorte-campo-marte-v1",
                "protocol_sha256": protocol_sha,
                "seal_sha256": seal_sha,
                "observation_vintage_utc": vintage.isoformat(),
                "source_receipts": observed["receipts"],
                "origins": len(origins),
                "eligible_histories": len(ids),
                "complete_targets": int(np.isfinite(targets).all(axis=1).sum()),
                "files": {
                    name: hashlib.sha256((stage / name).read_bytes()).hexdigest()
                    for name in (
                        "infer/manifest.json",
                        "scoring/observed.npz",
                        "scoring/origins.json",
                    )
                },
            }
            write_json(stage / "receipt.json", receipt)
            stage.rename(output)
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "seal", "receipts", "output"):
        p.add_argument(name, type=Path)
    p.add_argument("--protocol-sha256", required=True)
    p.add_argument("--seal-sha256", required=True)
    a = p.parse_args()
    prepare(
        a.protocol,
        a.protocol_sha256,
        a.seal,
        a.seal_sha256,
        a.receipts,
        a.output,
        datetime.now(UTC),
    )
