import json
from pathlib import Path

import pytest
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
    assert summary["statuses"]["downloaded"] == 5
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


def acquisition_config(tmp_path, **changes):
    path = tmp_path / "acquire.json"
    path.write_text(
        json.dumps(
            {
                "source_id": "demo",
                "resource_url": "https://example.org/data.csv",
                "method": "lightpanda",
                "format": "csv",
                "max_bytes": 1024,
                **changes,
            }
        )
    )
    return path


def test_import_command_respects_data_directory_and_reuses_bytes(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setenv("AIRAWARE_DATA_DIR", str(data))
    original = tmp_path / "input.csv"
    original.write_bytes(b"a,b\n1,2\n")
    config = acquisition_config(tmp_path)
    args = ["acquire", "import-file", "--spec", str(config), "--file", str(original)]
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.stdout
    output = json.loads(first.stdout)
    assert Path(output["artifact"]).is_relative_to(data)
    assert Path(output["artifact"]).read_bytes() == original.read_bytes()
    assert output["reused"] is False
    second = runner.invoke(app, args)
    assert second.exit_code == 0
    assert json.loads(second.stdout)["reused"] is True


@pytest.mark.parametrize(
    "changes",
    [
        {"resource_url": "https://user:private-value@example.org/data"},
        {"resource_url": "https://example.org/?token=private-value"},
        {"max_bytes": 0},
    ],
)
def test_acquisition_cli_errors_do_not_echo_config_values(tmp_path, changes):
    original = tmp_path / "input.csv"
    original.write_bytes(b"a,b\n1,2\n")
    config = acquisition_config(tmp_path, **changes)
    result = runner.invoke(
        app,
        [
            "acquire",
            "import-file",
            "--spec",
            str(config),
            "--file",
            str(original),
            "--data-dir",
            str(tmp_path / "data"),
        ],
    )
    assert result.exit_code == 1
    assert "private-value" not in result.output
    assert "No se pudo validar" in result.output


def test_acquisition_cli_api_uses_explicit_allowlist_and_transport(tmp_path, monkeypatch):
    import httpx

    from airaware.acquisition.transfer import fetch_cached_api as fetch_api

    config = acquisition_config(
        tmp_path, method="api", api_documentation_url="https://example.org/docs"
    )
    calls = []

    def mocked_fetch(spec, data_dir, *, allowed_hosts, **options):
        calls.append(allowed_hosts)
        return fetch_api(
            spec,
            data_dir,
            allowed_hosts=allowed_hosts,
            **options,
            resolve=lambda host: ["93.184.216.34"],
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, stream=httpx.ByteStream(b"a,b\n1,2\n"))
            ),
        )

    monkeypatch.setattr("airaware.acquisition.cli.fetch_api", mocked_fetch)
    result = runner.invoke(
        app,
        [
            "acquire",
            "api",
            "--spec",
            str(config),
            "--allow-host",
            "example.org",
            "--data-dir",
            str(tmp_path / "data"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert calls == [{"example.org"}]
    assert Path(json.loads(result.stdout)["artifact"]).read_bytes() == b"a,b\n1,2\n"


def test_acquisition_help_is_in_spanish():
    result = runner.invoke(app, ["acquire", "--help"])
    assert result.exit_code == 0
    assert "Adquirir originales" in result.stdout


def test_batch_dry_run_filters_metadata_without_network_or_creating_data(tmp_path, monkeypatch):
    config = acquisition_config(
        tmp_path, method="api", api_documentation_url="https://example.org/docs"
    )
    plan = tmp_path / "batch.json"
    plan.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jobs": [
                    {
                        "spec": json.loads(config.read_text()),
                        "region": "Lima",
                        "start": "2026-01-01",
                        "end": "2026-01-31",
                        "expected_size_bytes": 123,
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(
        "socket.getaddrinfo", lambda *a, **k: pytest.fail("dry-run must not use DNS")
    )
    result = runner.invoke(
        app,
        [
            "acquire",
            "batch",
            "--plan",
            str(plan),
            "--dry-run",
            "--source",
            "demo",
            "--region",
            "Lima",
            "--start",
            "2026-01-15",
            "--data-dir",
            str(tmp_path / "data"),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["known_size_bytes"] == 123 and report["unknown_count"] == 0
    assert not (tmp_path / "data").exists()


def test_batch_offline_registers_local_original_and_reports_zero_network_bytes(tmp_path):
    original = tmp_path / "original.csv"
    original.write_bytes(b"a,b\n1,2\n")
    config = acquisition_config(tmp_path)
    plan = tmp_path / "batch.json"
    plan.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jobs": [{"spec": json.loads(config.read_text()), "local_file": str(original)}],
            }
        )
    )
    result = runner.invoke(
        app,
        [
            "acquire",
            "batch",
            "--plan",
            str(plan),
            "--offline",
            "--data-dir",
            str(tmp_path / "data"),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["network_bytes"] == 0 and len(report["completed"]) == 1
    assert Path(report["completed"][0]["artifact"]).read_bytes() == original.read_bytes()


def test_api_offline_missing_cache_fails_without_dns(tmp_path, monkeypatch):
    config = acquisition_config(
        tmp_path, method="api", api_documentation_url="https://example.org/docs"
    )
    monkeypatch.setattr(
        "socket.getaddrinfo", lambda *a, **k: pytest.fail("offline must not resolve")
    )
    result = runner.invoke(
        app,
        [
            "acquire",
            "api",
            "--spec",
            str(config),
            "--allow-host",
            "example.org",
            "--offline",
            "--data-dir",
            str(tmp_path / "data"),
        ],
    )
    assert result.exit_code == 1
    assert "No se pudo validar" in result.output
