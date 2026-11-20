"""Conciliar los resultados publicados con la regla de selección y el sello de Campo de Marte."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from airaware.holdout_release import bind

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "metadata/seleccion-concentracion-lima-v1"


def read(name):
    return json.loads((RESULTS / name).read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_reconstruye_el_sello_desde_los_cuatro_manifiestos():
    seal = read("sello.json")
    protocol = ROOT / "configs/training/lima-prueba-futura-campo-marte-v1.json"
    choice = RESULTS / "seleccion.json"
    pairs = [
        (
            RESULTS / f"semilla-{seed}.json",
            RESULTS / f"checkpoint-quantile-{seed}.json",
            RESULTS / f"checkpoint-direct-{seed}.json",
            RESULTS / f"entrenamiento-directo-{seed}.json",
        )
        for seed in (27, 28)
    ]
    expected, deadline = bind(
        protocol,
        digest(protocol),
        ROOT / "configs/training/lima-comparacion-cuantiles-v1.yaml",
        choice,
        digest(choice),
        pairs,
        RESULTS / "calibrador-directo.json",
    )
    sealed_at = datetime.fromisoformat(seal.pop("sealed_at_utc"))
    assert sealed_at < deadline
    assert seal == expected
    release = read("release.json")
    assert (
        digest(RESULTS / "release.json")
        == "fd7c047dbacb311d80424f1c2e5841a868b916fcf75ca5c6e68f28044e1daf10"
    )
    assert release["components"]["transform.json"] == digest(RESULTS / "transformacion.json")
    assert release["components"]["policy.json"] == digest(RESULTS / "sello.json")
    assert release["components"]["calibration.json"] == seal["direct_calibrator_sha256"]
    assert (release["checkpoint_sha256"], release["base_manifest_sha256"], release["image"]) == (
        seal["checkpoint_sha256"],
        seal["base_weights_sha256"],
        seal["image"],
    )
    assert release["inference_batch"] == 32
    assert release["purpose"] == "retrospective_holdout_only"


def test_concilia_estaciones_persistencia_y_corridas():
    runs = read("corridas.json")
    assert len({r["run_id"] for r in runs}) == len(runs) == 4
    run_lookup = {(r["seed"], r["head"]): r for r in runs}
    for pair in read("seleccion.json")["seeds"]:
        seed = pair["seed"]
        report = read(f"semilla-{seed}.json")
        direct = read(f"directo-estaciones-{seed}.json")
        assert (direct["forecast_sha256"], direct["manifest_sha256"]) == (
            report["reference_sha256"],
            report["manifest_sha256"],
        )
        assert direct["overall"] == report["reference_overall"]
        assert set(direct["stations"]) == set(report["stations"])
        counts = direct["station_target_hours"]
        assert set(counts) == set(direct["stations"])
        for group, expected_hours in (("all", 25570), ("high", 2234)):
            assert sum(s[group] for s in counts.values()) == expected_hours
            for station, metrics in direct["stations"].items():
                assert metrics[group]["targets"] == report["stations"][station][group]["targets"]
            assert direct["persistence_mae"][group]["targets"] == pair["direct"][group]["targets"]
        for head in ("direct", "quantile"):
            run = run_lookup[seed, head]
            assert run["checkpoint_sha256"] == pair[head + "_checkpoint_sha256"]
            assert run["status"] == "FINISHED"
            assert (
                read(f"checkpoint-{head}-{seed}.json")["identity"]["trainer"] == run["trainer_sha"]
            )
