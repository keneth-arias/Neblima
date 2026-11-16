import hashlib

import httpx
import pytest
from pydantic import ValidationError

from airaware.acquisition.budget import ByteBudget
from airaware.acquisition.models import AcquisitionError, AcquisitionSpec
from airaware.acquisition.public_file import fetch_public_file, probe_public_file
from airaware.acquisition.store import ingest_file

BODY = b"a;b\n1;2\n"


def spec(**changes):
    return AcquisitionSpec.model_validate(
        {
            "source_id": "public-file",
            "resource_url": "https://example.org/data.csv",
            "source_page_url": "https://example.org/catalog",
            "method": "http_file",
            "format": "csv",
            "csv_delimiter": ";",
            "max_bytes": 1024,
            **changes,
        }
    )


def response(status=200, body=BODY, **headers):
    return httpx.Response(
        status, headers={"content-length": str(len(body)), **headers}, stream=httpx.ByteStream(body)
    )


def options(handler):
    return {
        "allowed_hosts": {"example.org"},
        "transport": httpx.MockTransport(handler),
        "resolve": lambda host: ["93.184.216.34"],
    }


def test_static_resource_requires_provenance_and_cannot_use_local_import(tmp_path):
    with pytest.raises(ValidationError):
        spec(source_page_url=None)
    with pytest.raises(ValidationError):
        spec(source_page_url="https://example.org/catalog?token=private")
    f = tmp_path / "input.csv"
    f.write_bytes(BODY)
    with pytest.raises(AcquisitionError):
        ingest_file(spec(), f, tmp_path / "data")


def test_probe_confirms_range_total_without_publishing_an_original(tmp_path):
    seen = []
    budget = ByteBudget(1024)

    def handler(request):
        seen.append(request)
        assert request.headers["range"] == "bytes=0-65535"
        assert request.headers["user-agent"].startswith("AirAware/")
        return response(
            206, **{"content-range": f"bytes 0-{len(BODY) - 1}/{len(BODY)}", "etag": '"v1"'}
        )

    result = probe_public_file(spec(), network_budget=budget, **options(handler))
    assert result.size_bytes == len(BODY) and result.range_supported and result.etag == '"v1"'
    assert result.prefix_sha256 == hashlib.sha256(BODY).hexdigest()
    assert budget.used == len(BODY) and not list(tmp_path.iterdir())


def test_probe_reads_only_prefix_if_server_ignores_range():
    body = b"x" * 200000
    budget = ByteBudget(300000)
    result = probe_public_file(
        spec(max_bytes=300000), network_budget=budget, **options(lambda r: response(body=body))
    )
    assert result.size_bytes == len(body) and not result.range_supported
    assert result.prefix_size_bytes == 65536 and budget.used == 65536


@pytest.mark.parametrize("code", [403, 418, 302, 401])
def test_denied_probe_stops_after_one_request(code):
    calls = []

    def handler(request):
        calls.append(request)
        return response(code)

    with pytest.raises(AcquisitionError, match=str(code)):
        probe_public_file(spec(), network_budget=ByteBudget(1024), **options(handler))
    assert len(calls) == 1


@pytest.mark.parametrize(
    "headers",
    [
        {"content-range": "bytes 1-8/9"},
        {"content-range": "bytes 0-7/*"},
        {"content-range": "bytes 0-7/2048"},
        {"content-range": "bytes 0-6/8"},
        {"content-range": "bytes 0-7/8", "content-encoding": "gzip"},
        {"content-range": "bytes 0-7/8", "content-type": "text/html"},
    ],
)
def test_probe_rejects_invalid_or_unbounded_range_metadata(headers):
    with pytest.raises(AcquisitionError):
        probe_public_file(
            spec(), network_budget=ByteBudget(1024), **options(lambda r: response(206, **headers))
        )


def test_unknown_size_is_not_authorized_by_default():
    with pytest.raises(AcquisitionError):
        probe_public_file(
            spec(),
            network_budget=ByteBudget(1024),
            **options(lambda r: httpx.Response(200, stream=httpx.ByteStream(BODY))),
        )


def test_probe_and_download_share_budget_then_offline_reuses_without_dns(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        if "range" in request.headers:
            return response(206, **{"content-range": "bytes 0-7/8", "etag": '"v1"'})
        return response(etag='"v1"')

    budget = ByteBudget(16)
    result = fetch_public_file(spec(), tmp_path / "data", network_budget=budget, **options(handler))
    assert result.artifact.read_bytes() == BODY and budget.used == 16 and len(calls) == 2
    again = fetch_public_file(
        spec(),
        tmp_path / "data",
        allowed_hosts=set(),
        network_budget=ByteBudget(1),
        offline=True,
        resolve=lambda h: pytest.fail("offline DNS"),
    )
    assert again.reused and again.artifact == result.artifact


def test_probe_consumption_can_exhaust_budget_before_full_get(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return response(206, **{"content-range": "bytes 0-7/8"})

    with pytest.raises(AcquisitionError):
        fetch_public_file(
            spec(), tmp_path / "data", network_budget=ByteBudget(8), **options(handler)
        )
    assert len(calls) == 1


def test_size_change_does_not_expand_confirmed_transfer_ceiling(tmp_path):
    def handler(request):
        if "range" in request.headers:
            return response(206, **{"content-range": "bytes 0-7/8"})
        return response(body=BODY + BODY)

    with pytest.raises(AcquisitionError):
        fetch_public_file(
            spec(), tmp_path / "data", network_budget=ByteBudget(1024), **options(handler)
        )
    assert not list((tmp_path / "data/raw").glob("*/*/manifest.json"))


def test_file_cli_uses_explicit_channel_and_reports_budget(tmp_path, monkeypatch):
    import json

    from typer.testing import CliRunner

    from airaware.cli import app

    original = fetch_public_file
    config = tmp_path / "spec.json"
    config.write_text(spec().model_dump_json())

    def fetch(specification, data_dir, **kwargs):
        def handler(request):
            return (
                response(206, **{"content-range": "bytes 0-7/8"})
                if "range" in request.headers
                else response()
            )

        return original(
            specification,
            data_dir,
            **kwargs,
            transport=httpx.MockTransport(handler),
            resolve=lambda h: ["93.184.216.34"],
        )

    monkeypatch.setattr("airaware.acquisition.cli.fetch_public_file", fetch)
    result = CliRunner().invoke(
        app,
        [
            "acquire",
            "file",
            "--spec",
            str(config),
            "--allow-host",
            "example.org",
            "--budget-bytes",
            "16",
            "--data-dir",
            str(tmp_path / "data"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["network_bytes"] == 16


def test_batch_recognizes_static_file_as_network_work(tmp_path):
    from airaware.acquisition.batch import AcquisitionJob, execute_jobs

    job = AcquisitionJob(spec=spec(), expected_size_bytes=8)
    with pytest.raises(AcquisitionError, match="presupuesto"):
        execute_jobs([job], tmp_path / "data", budget_bytes=0, allowed_hosts={"example.org"})


def test_legacy_api_transport_cannot_bypass_static_file_probe(tmp_path):
    from airaware.acquisition.http import fetch_api

    with pytest.raises(AcquisitionError):
        fetch_api(spec(), tmp_path / "data", **options(lambda r: pytest.fail("wrong channel")))


def test_static_file_cannot_target_a_private_address():
    with pytest.raises(AcquisitionError):
        probe_public_file(
            spec(),
            allowed_hosts={"example.org"},
            network_budget=ByteBudget(1024),
            resolve=lambda h: ["127.0.0.1"],
            transport=httpx.MockTransport(lambda r: pytest.fail("private destination")),
        )
