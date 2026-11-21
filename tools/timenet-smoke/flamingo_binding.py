"""Vincular los roles congelados del ajuste de Lima con el modelo Flamingo."""

import argparse
import hashlib
import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[2] / "configs/training"
REVISION = "5e030b001fb8d4be6d10ebb3a8b9bc3e6ef80983"
WEIGHTS_SHA256 = "7f8562992f1cf3852ced581f331247c6420fc90292d45453424c77f0a29c199f"


def digest(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Se requiere un archivo regular: {path}")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def bind(frozen, release_sha256, protocol_path, weights_manifest):
    if frozen.is_symlink() or (frozen / "trainer").is_symlink():
        raise ValueError("La entrega y la carpeta del entrenador deben ser carpetas reales")
    root = frozen / "manifest.json"
    if digest(root) != release_sha256 or digest(weights_manifest) != WEIGHTS_SHA256:
        raise ValueError("La entrega o el manifiesto de pesos no corresponde a la revisión fijada")
    record = json.loads(root.read_bytes())
    protocol = json.loads(protocol_path.read_bytes())
    if (
        record["protocol_sha256"] != digest(protocol_path)
        or record["source_manifest_sha256"] != protocol["source_manifest_sha256"]
        or record["cohorts"] != protocol["cohorts"]
        or record["fit_graph_sample"] != protocol["fit_graph_sample"]
    ):
        raise ValueError("El protocolo no coincide con la entrega")
    roles = {}
    for role in ("fit", "inner_validation"):
        folder = frozen / "trainer" / role
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError(f"El rol {role} debe ser una carpeta real")
        manifest = folder / "manifest.json"
        actual = digest(manifest)
        if actual != record["manifests"][role]:
            raise ValueError(f"Huellas incompatibles para {role}")
        spec = json.loads(manifest.read_bytes())
        required = {
            "schema": "forecast-direct-cohort-v1",
            "phase": role,
            "head": "direct",
            "unit": "ug/m3",
            "protocol_sha256": record["protocol_sha256"],
            "source_manifest_sha256": record["source_manifest_sha256"],
            "weights_manifest_sha256": protocol["weights_manifest_sha256"],
            **protocol["cohorts"][role],
        }
        if any(spec.get(k) != v for k, v in required.items()):
            raise ValueError(f"Contrato de cohorte incorrecto para {role}")
        files = {"data.npz", "thresholds.json"}
        if (
            set(spec["files"]) != files
            or {p.name for p in folder.iterdir()} != files | {"manifest.json"}
            or any(digest(folder / f) != spec["files"][f] for f in files)
        ):
            raise ValueError(f"Archivos incorrectos para {role}")
        roles[role] = actual
    return {
        "schema": "airaware-flamingo-binding-v1",
        "model": "opentime/tslm-nov26",
        "revision": REVISION,
        "weights_manifest_sha256": WEIGHTS_SHA256,
        "cohort_weights_manifest_sha256": protocol["weights_manifest_sha256"],
        "roles": roles,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frozen", type=Path)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    obj = bind(
        args.frozen,
        args.release_sha256,
        CONFIG / "lima-directo-cohortes-v1.json",
        CONFIG / "tslm-nov26-SHA256SUMS",
    )
    payload = (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with args.output.open("xb") as file:
        file.write(payload)
    print(hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    main()
