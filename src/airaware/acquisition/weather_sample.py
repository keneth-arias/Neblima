"""Verificar sin red la muestra meteorológica fijada en el plan de #16."""

import argparse
from pathlib import Path

from airaware.acquisition.batch import BatchPlan
from airaware.acquisition.models import AcquisitionError
from airaware.acquisition.store import verify_bundle


def verify_sample(plan: BatchPlan, data_dir: Path) -> int:
    """Verificar los paquetes por hash sin depender del índice de caché de transferencia."""
    raw = (data_dir / "raw").resolve()
    for job in plan.jobs:
        spec = job.spec
        digest = spec.expected_sha256
        if digest is None:
            raise AcquisitionError(f"Falta el SHA-256 esperado para {spec.resource_url}")
        directory = raw / spec.source_id / digest
        try:
            verify_bundle(spec, raw, directory)
        except (AcquisitionError, OSError) as error:
            raise AcquisitionError(f"No se pudo verificar {spec.resource_url}: {error}") from error
    return len(plan.jobs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--plan", type=Path, default=Path("configs/acquisition/weather-lima-sample-plan.json")
    )
    args = parser.parse_args()
    try:
        count = verify_sample(BatchPlan.model_validate_json(args.plan.read_bytes()), args.data_dir)
    except (AcquisitionError, OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Recursos verificados por SHA-256: {count}. Bytes de red: 0.")


if __name__ == "__main__":
    main()
