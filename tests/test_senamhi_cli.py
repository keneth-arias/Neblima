"""Pruebas sintéticas de la CLI de normalización SENAMHI (#13, entrega 3).

Sin red ni datos reales: cada prueba construye su propio CSV pequeño y una política
sintética con el SHA-256 de ese contenido, ejecutando la ruta pública `airaware`.
"""

import csv
import hashlib
import io
import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from airaware.cli import app
from airaware.senamhi_preparation import load_policy

runner = CliRunner()
HEADER = ["FECHA", "HORA", "PM10", "PM2_5", "NO2", "ESTACION"]


def fila(
    fecha: str = "20240531",
    hora: str = "153045",
    pm10: str = "12.5",
    pm25: str = "0",
    no2: str = "ND",
    estacion: str = "CAMPO_DE_MARTE",
) -> list[str]:
    return [fecha, hora, pm10, pm25, no2, estacion]


def write_csv(path: Path, rows: list[list[str]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=",")
    writer.writerow(HEADER)
    writer.writerows(rows)
    data = buffer.getvalue().encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def write_policy(path: Path, sha256: str) -> Path:
    base = load_policy().model_dump()
    base["input_sha256"] = sha256
    path.write_text(yaml.safe_dump(base, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def normalize_args(tmp_path, rows, *, batch_size=None, output=None, policy_sha=None):
    source = tmp_path / "original.csv"
    sha = write_csv(source, rows)
    policy = write_policy(tmp_path / "policy.yaml", policy_sha or sha)
    salida = output if output is not None else tmp_path / "salida"
    args = [
        "normalize",
        "senamhi",
        "--input",
        str(source),
        "--policy",
        str(policy),
        "--output",
        str(salida),
    ]
    if batch_size is not None:
        args += ["--batch-size", str(batch_size)]
    return args, source, salida, sha


def test_comando_registrado_en_la_cli_publica_con_ayuda_en_espanol():
    registered = runner.invoke(app, ["normalize", "--help"])
    assert registered.exit_code == 0
    assert "senamhi" in registered.output
    shown = runner.invoke(app, ["normalize", "senamhi", "--help"])
    assert shown.exit_code == 0
    assert "Parquet" in shown.output


def test_exito_publica_salida_resumida_sin_volcar_observaciones(tmp_path):
    args, source, salida, sha = normalize_args(
        tmp_path, [fila(), fila(pm10="3.5", estacion="VILLA_EL_SALVADOR")]
    )
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    summary = json.loads(result.stdout)
    assert summary["counts"] == {"input_rows": 2, "observations": 6, "rejections": 0}
    assert summary["input_sha256"] == sha
    assert summary["policy_id"] == "senamhi-normalization-20261117-v1"
    assert Path(summary["manifest"]) == salida / "manifest.json"
    assert Path(summary["manifest"]).is_file()
    assert (salida / "rejections.jsonl").read_bytes() == b""
    assert (salida / "source_id=senamhi-lima-csv" / "year=2024" / "month=05").is_dir()
    assert "CAMPO_DE_MARTE" not in result.output
    assert f"{sha}:2:PM10" not in result.output


def test_sha_distinto_falla_sin_publicar_salida(tmp_path):
    args, source, salida, _ = normalize_args(tmp_path, [fila()], policy_sha="0" * 64)
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "SHA-256" in result.output
    assert not salida.exists()


def test_salida_existente_no_se_sobrescribe(tmp_path):
    args, source, salida, _ = normalize_args(tmp_path, [fila()])
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    antes = sorted(str(p.relative_to(salida)) for p in salida.rglob("*") if p.is_file())
    bytes_antes = {r: (salida / r).read_bytes() for r in antes}
    second = runner.invoke(app, args)
    assert second.exit_code == 1
    assert "existe" in second.output
    despues = sorted(str(p.relative_to(salida)) for p in salida.rglob("*") if p.is_file())
    assert {r: (salida / r).read_bytes() for r in despues} == bytes_antes
    assert not [p.name for p in tmp_path.iterdir() if p.name.startswith(".salida.tmp-")]


@pytest.mark.parametrize("batch_size", ["0", "-3"])
def test_tamano_de_lote_invalido_falla_sin_publicar(tmp_path, batch_size):
    args, _, salida, _ = normalize_args(tmp_path, [fila()], batch_size=batch_size)
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "positivo" in result.output
    assert not salida.exists()


def test_entrada_ausente_falla_con_mensaje_claro_sin_traza(tmp_path):
    args, _, salida, _ = normalize_args(tmp_path, [fila()])
    (tmp_path / "original.csv").unlink()
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "No se pudo normalizar" in result.output
    assert not salida.exists()


def test_politica_ausente_falla_sin_publicar(tmp_path):
    args, _, salida, _ = normalize_args(tmp_path, [fila()])
    idx = args.index("--policy")
    args[idx + 1] = str(tmp_path / "ausente.yaml")
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert not salida.exists()
