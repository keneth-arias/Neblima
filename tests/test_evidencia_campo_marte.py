"""Verificar las huellas y las decisiones disponibles en Git sin acceder a bm."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "metadata"
EVIDENCE = ROOT / "campo-marte-inmediato-v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def test_vinculos_entre_puntajes_calibracion_y_emision_privada():
    selected = ROOT / "seleccion-concentracion-lima-v1"
    model = read(selected / "sello.json")
    folder = EVIDENCE / "recalibracion"
    protocol = read(folder / "protocolo.json")
    candidate = read(folder / "candidato.json")
    comparison = read(folder / "comparacion.json")
    tracking = read(folder / "seguimiento.json")
    archive = read(EVIDENCE / "archivo.json")
    recent = read(EVIDENCE / "reciente.json")
    live = read(EVIDENCE / "primera-emision.json")
    assert (
        comparison["protocol_sha256"]
        == candidate["protocol_sha256"]
        == digest(folder / "protocolo.json")
    )
    assert comparison["candidate_sha256"] == digest(folder / "candidato.json")
    assert tracking["report_sha256"] == digest(folder / "comparacion.json")
    assert protocol["archive_report_sha256"] == digest(EVIDENCE / "archivo.json")
    assert protocol["forecast_sha256"] == archive["output_sha256"]
    assert protocol["original_calibrator_sha256"] == digest(selected / "calibrador-directo.json")
    assert tracking["parent"] == archive["run_id"]
    assert all(
        r["checkpoint_sha256"] == model["checkpoint_sha256"]
        for r in (archive, recent, protocol, candidate, live)
    )
    for score in (archive, recent):
        assert score["image"] == model["image"]
        assert score["all"]["targets"] == 6 * score["windows"]
        pooled = score["all"]
        assert score["passes"] == (
            pooled["mae"] < pooled["mae_persistence"] and 0.75 <= pooled["coverage"] <= 0.85
        )
    assert archive["windows"] == sum(
        comparison[k] for k in ("n_calibration", "n_comparison", "n_purged")
    )
    assert comparison["gates"] == {
        "pooled_coverage": True,
        "retains_high_coverage": False,
        "smaller_mean_width": True,
    }
    assert comparison["decision"] == "reject_candidate"
