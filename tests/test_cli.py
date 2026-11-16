import json
from pathlib import Path

from typer.testing import CliRunner

from airaware.cli import app

runner = CliRunner()
CATALOG = Path(__file__).resolve().parents[1] / "configs/sources.yaml"


def test_catalog_summary_is_offline_and_reports_evidenced_statuses():
    result = runner.invoke(app, ["catalog", "validate", "--path", str(CATALOG)])
    assert result.exit_code == 0
    summary = json.loads(result.stdout)
    assert summary["total"] >= 30
    assert sum(summary["statuses"].values()) == summary["total"]
    assert summary["statuses"]["downloaded"] == 3
    assert summary["statuses"]["blocked"] > 0


def test_invalid_catalog_exits_nonzero_without_echoing_input(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text("sources: private-value")
    result = runner.invoke(app, ["catalog", "validate", "--path", str(path)])
    assert result.exit_code == 1
    assert "private-value" not in result.output
    assert "No se pudo leer o validar" in result.output


def test_workspace_init_is_idempotent_and_preserves_raw_files(tmp_path):
    data = tmp_path / "data"
    first = runner.invoke(app, ["workspace", "init", "--data-dir", str(data)])
    assert first.exit_code == 0
    raw = data / "raw" / "original.csv"
    raw.write_bytes(b"original bytes\n")
    second = runner.invoke(app, ["workspace", "init", "--data-dir", str(data)])
    assert second.exit_code == 0
    assert raw.read_bytes() == b"original bytes\n"
    assert {"raw", "staging", "normalized", "curated", "benchmarks", "timef"} <= {
        p.name for p in data.iterdir()
    }


def test_workspace_honors_environment_data_directory(tmp_path, monkeypatch):
    data = tmp_path / "external-storage"
    monkeypatch.setenv("AIRAWARE_DATA_DIR", str(data))
    result = runner.invoke(app, ["workspace", "init"])
    assert result.exit_code == 0
    assert (data / "raw").is_dir()


def test_workspace_reports_creation_failure(tmp_path):
    file = tmp_path / "existing-file"
    file.write_text("conservar")
    result = runner.invoke(app, ["workspace", "init", "--data-dir", str(file)])
    assert result.exit_code == 1
    assert file.read_text() == "conservar"


def test_doctor_reports_failure_without_creating_directories(tmp_path):
    data = tmp_path / "missing"
    result = runner.invoke(app, ["doctor", "--catalog", str(CATALOG), "--data-dir", str(data)])
    assert result.exit_code == 1
    report = json.loads(result.stdout)
    assert not report["checks"]["storage"]
    assert not data.exists()


def test_doctor_does_not_echo_secret_values(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAQ_API_KEY", "private-value")
    runner.invoke(app, ["workspace", "init", "--data-dir", str(tmp_path)])
    result = runner.invoke(app, ["doctor", "--catalog", str(CATALOG), "--data-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "private-value" not in result.output
    assert json.loads(result.stdout)["optional_credentials"]["OPENAQ_API_KEY"] is True


def test_doctor_rejects_a_nonwritable_layer(tmp_path, monkeypatch):
    runner.invoke(app, ["workspace", "init", "--data-dir", str(tmp_path)])
    monkeypatch.setattr("airaware.cli.os.access", lambda path, mode: Path(path).name != "raw")
    result = runner.invoke(app, ["doctor", "--catalog", str(CATALOG), "--data-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["checks"]["storage"] is False


def test_cli_help_uses_peruvian_spanish():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Herramientas locales" in result.stdout


def test_workspace_success_message_is_in_spanish(tmp_path):
    result = runner.invoke(app, ["workspace", "init", "--data-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Carpetas de trabajo listas" in result.stdout
