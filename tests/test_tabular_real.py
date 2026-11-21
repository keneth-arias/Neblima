"""Controles del corredor real con insumos sintéticos, sin repetir la prueba reservada."""

import hashlib
import json
from pathlib import Path
from runpy import run_path

import pytest

from airaware.benchmarks.metrics import Prediction
from airaware.benchmarks.predictions import paired_join

runner = run_path(str(Path(__file__).resolve().parents[1] / "tools/training/eval_tabular_real.py"))
Bloqueo = runner["Bloqueo"]
align_by_window = runner["align_by_window"]
assert_close = runner["assert_close"]
verify_manifest = runner["verify_manifest"]


def predictions(window="w1"):
    return [Prediction(window, "s1", hour, 10.0, 11.0) for hour in range(1, 7)]


def test_comparacion_conserva_todos_los_objetivos_congelados():
    tabular = predictions()
    reference = list(reversed(tabular))
    left, right = align_by_window(tabular, reference)
    assert len(paired_join(left, right)) == 6
    assert left == tabular and right == reference


@pytest.mark.parametrize("case", ["horizonte", "ventana", "ambos", "vacio", "extra"])
def test_comparacion_bloquea_cobertura_incompleta(case):
    tabular, reference = predictions(), predictions()
    if case == "horizonte":
        reference.pop()
    elif case == "ventana":
        reference.extend(predictions("w2"))
    elif case == "ambos":
        tabular.pop()
        reference.pop()
    elif case == "vacio":
        tabular, reference = [], []
    else:
        extra = Prediction("w1", "s1", 7, 10.0, 11.0)
        tabular.append(extra)
        reference.append(extra)
    with pytest.raises(Bloqueo, match="cobertura"):
        align_by_window(tabular, reference)


@pytest.mark.parametrize(
    ("computed", "registered"),
    [(float("nan"), 1.0), (1.0, float("nan")), (float("inf"), float("inf"))],
)
def test_cotejo_de_metricas_rechaza_valores_no_finitos(computed, registered):
    with pytest.raises(Bloqueo, match="finito"):
        assert_close("persistencia", computed, registered)


def test_cotejo_de_metricas_conserva_la_tolerancia():
    assert_close("persistencia", 1.0, 1.0 + 1e-10)
    with pytest.raises(Bloqueo, match="difiere"):
        assert_close("persistencia", 1.0, 1.01)


def test_matrices_deben_coincidir_con_la_congelacion_registrada(tmp_path):
    path = tmp_path / "inputs.npz"
    path.write_bytes(b"matriz sintetica original")
    expected = {"files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(expected))
    assert verify_manifest(tmp_path, (path.name,), expected=expected) == expected

    path.write_bytes(b"otra historia con los mismos identificadores")
    replacement = {"files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}}
    manifest.write_text(json.dumps(replacement))
    with pytest.raises(Bloqueo, match="congelaci"):
        verify_manifest(tmp_path, (path.name,), expected=expected)


def test_manifiesto_rechaza_archivos_modificados(tmp_path):
    path = tmp_path / "inputs.npz"
    path.write_bytes(b"matriz sintetica original")
    expected = {"files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}}
    (tmp_path / "manifest.json").write_text(json.dumps(expected))
    path.write_bytes(b"matriz alterada")
    with pytest.raises(Bloqueo, match="manifiesto"):
        verify_manifest(tmp_path, (path.name,))
