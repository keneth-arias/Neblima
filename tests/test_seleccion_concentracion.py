"""Conciliar los resultados publicados, el criterio registrado y el sello de Campo de Marte."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import yaml

from airaware.episode_forecast_selection import decide

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "metadata/seleccion-concentracion-lima-v1"


def test_publicacion_de_las_dos_semillas_y_del_sello():
    def read(name):
        return json.loads((RESULTS / name).read_bytes())

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    seal = read("sello.json")
    choice = read("seleccion.json")
    protocol_path = ROOT / "configs/training/lima-prueba-futura-campo-marte-v1.json"
    rule_path = ROOT / "configs/training/lima-comparacion-cuantiles-v1.yaml"
    config = yaml.safe_load(rule_path.read_bytes())
    protocol = json.loads(protocol_path.read_bytes())
    assert seal["protocol_sha256"] == digest(protocol_path)
    assert seal["selection_rule_sha256"] == digest(rule_path) == protocol["selection_rule_sha256"]
    assert seal["decision_sha256"] == digest(RESULTS / "seleccion.json")
    assert datetime.fromisoformat(seal["sealed_at_utc"]) < datetime.fromisoformat(
        protocol["seal_before_utc"]
    )
    assert choice == {
        **decide(config, choice["seeds"]),
        "rule_sha256": digest(rule_path),
        "blocks_sha256": config["blocks_sha256"],
    }

    runs = read("corridas.json")
    assert len({r["run_id"] for r in runs}) == len(runs) == 4
    run_lookup = {(r["seed"], r["head"]): r for r in runs}
    for pair in choice["seeds"]:
        seed = pair["seed"]
        path = RESULTS / f"semilla-{seed}.json"
        report = json.loads(path.read_bytes())
        assert pair["report_sha256"] == digest(path)
        assert (
            report["block"] == "selection" and report["manifest_sha256"] == config["blocks_sha256"]
        )
        for head, field in (("direct", "reference_overall"), ("quantile", "overall")):
            assert pair[head] == {stratum: report[field][stratum] for stratum in ("all", "high")}
            assert run_lookup[seed, head]["checkpoint_sha256"] == pair[head + "_checkpoint_sha256"]
        assert set(report["paired_differences"]) == {str(size) for size in config["block_hours"]}
    assert (seal["seed"], seal["head"]) == (choice["seed"], choice["selected"])
    assert seal["checkpoint_sha256"] == run_lookup[seal["seed"], seal["head"]]["checkpoint_sha256"]
    release = read("release.json")
    assert release["components"]["policy.json"] == digest(RESULTS / "sello.json")
    assert (release["checkpoint_sha256"], release["base_manifest_sha256"], release["image"]) == (
        seal["checkpoint_sha256"],
        seal["base_weights_sha256"],
        protocol["image"],
    )
    assert release["purpose"] == "retrospective_holdout_only"
    assert seal["direct_calibrator_sha256"] == digest(RESULTS / "calibrador-directo.json")
    cal = read("calibrador-directo.json")
    assert (cal["checkpoint_sha256"], cal["thresholds_sha256"]) == (
        run_lookup[seal["seed"], "direct"]["checkpoint_sha256"],
        protocol["thresholds_sha256"],
    )
