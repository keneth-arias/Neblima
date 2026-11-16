from datetime import UTC, datetime

import httpx
import pytest

from airaware.acquisition import AcquisitionError, AcquisitionSpec
from airaware.acquisition.http import fetch_api

BODY = b'{"results": []}\n'


def request_spec(**changes):
    return AcquisitionSpec.model_validate(
        {
            "source_id": "demo-api",
            "resource_url": "https://api.example.org/data",
            "method": "api",
            "api_documentation_url": "https://api.example.org/docs",
            "format": "json",
            "json_required_keys": ["results"],
            "max_bytes": 1024,
            **changes,
        }
    )


def response(status=200, body=BODY, **headers):
    return httpx.Response(status, stream=httpx.ByteStream(body), headers=headers)


def acquire(tmp_path, handler, **kwargs):
    return fetch_api(
        request_spec(**kwargs.pop("changes", {})),
        tmp_path / "data",
        allowed_hosts={"api.example.org"},
        transport=httpx.MockTransport(handler),
        resolve=lambda host: ["93.184.216.34"],
        **kwargs,
    )


def test_api_success_preserves_bytes_and_http_provenance(tmp_path):
    def handler(request):
        assert request.headers["accept-encoding"] == "identity"
        assert "authorization" not in request.headers
        assert request.extensions["timeout"]["read"] == 10
        return response(**{"content-type": "application/json"})

    result = acquire(tmp_path, handler)
    assert result.artifact.read_bytes() == BODY
    manifest = result.manifest.read_text()
    assert '"http_status": 200' in manifest
    assert '"attempts": 1' in manifest
    assert "api_documentation_url" in manifest


@pytest.mark.parametrize("status", [301, 302, 307, 403, 404, 206, 204])
def test_permanent_errors_and_redirects_do_not_retry(tmp_path, status):
    calls = []

    def handler(request):
        calls.append(request)
        return response(status, **{"location": "https://evil.example/a"})

    with pytest.raises(AcquisitionError):
        acquire(tmp_path, handler)
    assert len(calls) == 1
    assert not list((tmp_path / "data").rglob("manifest.json"))


@pytest.mark.parametrize("kind", ["timeout", "500", "429", "broken-stream"])
def test_transient_failures_retry_with_bounded_attempts_and_no_real_sleep(tmp_path, kind):
    calls, waits = [], []

    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{"results":'
            raise httpx.ReadError("private-value")

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            if kind == "timeout":
                raise httpx.ReadTimeout("private-value")
            if kind == "broken-stream":
                return httpx.Response(200, stream=Broken())
            return response(int(kind), **({"retry-after": "2"} if kind == "429" else {}))
        return response()

    result = acquire(tmp_path, handler, sleep=waits.append)
    assert len(calls) == 2
    assert waits == ([2] if kind == "429" else [1])
    assert result.artifact.read_bytes() == BODY
    assert '"attempts": 2' in result.manifest.read_text()
    assert not list((tmp_path / "data").rglob(".pending-*"))


def test_retries_are_exhausted_safely(tmp_path):
    calls, waits = [], []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("private-value")

    with pytest.raises(AcquisitionError) as error:
        acquire(tmp_path, handler, sleep=waits.append)
    assert len(calls) == 3
    assert waits == [1, 2]
    assert "private-value" not in str(error.value)
    assert not list((tmp_path / "data").rglob("manifest.json"))


@pytest.mark.parametrize(
    "headers,body,changes",
    [
        ({"content-type": "text/html"}, b"<html>denied</html>", {}),
        ({"content-type": "application/json"}, b"<html>denied</html>", {}),
        ({"content-length": "5000"}, BODY, {}),
        ({"content-length": "1"}, BODY, {}),
        ({"content-length": "nonsense"}, BODY, {}),
        ({"content-encoding": "gzip"}, b"compressed", {}),
        ({}, BODY, {"max_bytes": 4}),
        ({}, BODY, {"expected_sha256": "0" * 64}),
    ],
)
def test_invalid_content_never_retries_or_publishes(tmp_path, headers, body, changes):
    calls = []

    def handler(request):
        calls.append(request)
        return response(body=body, **headers)

    with pytest.raises(AcquisitionError):
        acquire(tmp_path, handler, changes=changes)
    assert len(calls) == 1
    assert not list((tmp_path / "data").rglob("manifest.json"))


@pytest.mark.parametrize("retry_after", ["31", "invalid", "-1"])
def test_retry_after_outside_budget_does_not_retry(tmp_path, retry_after):
    waits = []
    with pytest.raises(AcquisitionError):
        acquire(
            tmp_path, lambda r: response(429, **{"retry-after": retry_after}), sleep=waits.append
        )
    assert waits == []


def test_retry_after_http_date_uses_injected_clock(tmp_path):
    calls, waits = [], []

    def handler(request):
        calls.append(request)
        return (
            response(429, **{"retry-after": "Thu, 01 Jan 2026 00:00:02 GMT"})
            if len(calls) == 1
            else response()
        )

    acquire(
        tmp_path,
        handler,
        sleep=waits.append,
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert waits == [2]


@pytest.mark.parametrize(
    "host,addresses",
    [
        ("unlisted.example", ["93.184.216.34"]),
        ("api.example.org", ["127.0.0.1"]),
        ("api.example.org", ["169.254.169.254"]),
        ("api.example.org", ["::1"]),
        ("api.example.org", ["93.184.216.34", "10.0.0.1"]),
    ],
)
def test_unapproved_or_private_destination_is_rejected_before_transfer(tmp_path, host, addresses):
    calls = []

    def handler(request):
        calls.append(request)
        return response()

    with pytest.raises(AcquisitionError):
        fetch_api(
            request_spec(resource_url=f"https://{host}/data"),
            tmp_path / "data",
            allowed_hosts={"api.example.org"},
            resolve=lambda host: addresses,
            transport=httpx.MockTransport(handler),
        )
    assert calls == []


def test_total_stream_time_is_bounded(tmp_path):
    ticks = iter([0, 0, 0, 100, 100])
    with pytest.raises(AcquisitionError):
        acquire(tmp_path, lambda r: response(), monotonic=lambda: next(ticks))
    assert not list((tmp_path / "data").rglob("manifest.json"))


def test_server_cookies_are_not_replayed_on_retry(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        assert "cookie" not in request.headers
        if len(calls) == 1:
            return response(429, **{"set-cookie": "session=private-value", "retry-after": "0"})
        return response()

    acquire(tmp_path, handler, sleep=lambda seconds: None)
    assert len(calls) == 2


def test_multicast_destination_is_rejected(tmp_path):
    with pytest.raises(AcquisitionError):
        fetch_api(
            request_spec(),
            tmp_path / "data",
            allowed_hosts={"api.example.org"},
            resolve=lambda host: ["224.0.0.1"],
            transport=httpx.MockTransport(lambda r: response()),
        )


def test_api_records_the_known_final_url_without_redirects(tmp_path):
    import json

    result = acquire(tmp_path, lambda r: response())
    manifest = json.loads(result.manifest.read_text())
    assert manifest["spec"]["final_url"] == "https://api.example.org/data"
    assert manifest["original_name"] is None
