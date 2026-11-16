import json

import httpx
import pytest

from airaware.acquisition import AcquisitionError, AcquisitionSpec
from airaware.acquisition.budget import ByteBudget
from airaware.acquisition.transfer import fetch_cached_api

BODY = b"a,b\n1,2\n"


def spec(**changes):
    return AcquisitionSpec.model_validate(
        dict(
            source_id="cache-demo",
            resource_url="https://api.example.org/data",
            method="api",
            api_documentation_url="https://api.example.org/docs",
            format="csv",
            max_bytes=1024,
            **changes,
        )
    )


def response(body=BODY, status=200, headers=None):
    return httpx.Response(
        status,
        headers={"content-length": str(len(body)), **(headers or {})},
        stream=httpx.ByteStream(body),
    )


def fetch(tmp_path, handler, **kwargs):
    return fetch_cached_api(
        spec(),
        tmp_path / "data",
        allowed_hosts={"api.example.org"},
        transport=httpx.MockTransport(handler),
        resolve=kwargs.pop("resolve", lambda host: ["93.184.216.34"]),
        sleep=lambda seconds: None,
        **kwargs,
    )


def test_conditional_cache_304_and_offline_verify_originals(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return response(headers={"etag": '"v1"'})
        assert request.headers["if-none-match"] == '"v1"'
        return response(b"", status=304)

    first = fetch(tmp_path, handler)
    original_manifest = first.manifest.read_bytes()
    second = fetch(tmp_path, handler)
    assert second.reused and second.artifact == first.artifact
    assert second.manifest.read_bytes() == original_manifest
    result = fetch(
        tmp_path,
        lambda r: pytest.fail("offline must not request"),
        offline=True,
        resolve=lambda host: pytest.fail("offline must not resolve"),
    )
    assert result.artifact.read_bytes() == BODY
    assert len(requests) == 2


def test_offline_missing_cache_fails_without_network(tmp_path):
    with pytest.raises(AcquisitionError):
        fetch(tmp_path, lambda r: pytest.fail("no network"), offline=True)


def test_corrupt_cached_artifact_is_not_used_or_overwritten(tmp_path):
    first = fetch(tmp_path, lambda r: response(headers={"etag": '"v1"'}))
    first.artifact.write_bytes(b"corrupt")
    with pytest.raises(AcquisitionError):
        fetch(tmp_path, lambda r: pytest.fail("corrupt cache must stop"))
    assert first.artifact.read_bytes() == b"corrupt"


def test_partial_stream_resumes_only_with_matching_strong_validator(tmp_path):
    calls = []

    class Interrupted(httpx.SyncByteStream):
        def __iter__(self):
            yield BODY[:4]
            raise httpx.ReadError("connection interrupted")

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(
                200,
                headers={"etag": '"v1"', "content-length": str(len(BODY))},
                stream=Interrupted(),
            )
        assert request.headers["range"] == "bytes=4-"
        assert request.headers["if-range"] == '"v1"'
        return response(
            BODY[4:],
            status=206,
            headers={"etag": '"v1"', "content-range": f"bytes 4-{len(BODY) - 1}/{len(BODY)}"},
        )

    budget = ByteBudget(len(BODY))
    result = fetch(tmp_path, handler, network_budget=budget)
    assert result.artifact.read_bytes() == BODY
    assert budget.used == len(BODY)
    assert len(calls) == 2


@pytest.mark.parametrize("bad", ["range", "etag", "416"])
def test_invalid_partial_response_never_publishes(tmp_path, bad):
    calls = []

    class Interrupted(httpx.SyncByteStream):
        def __iter__(self):
            yield BODY[:4]
            raise httpx.ReadError("interrupted")

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(
                200,
                headers={"etag": '"v1"', "content-length": str(len(BODY))},
                stream=Interrupted(),
            )
        return response(
            BODY[4:],
            status=416 if bad == "416" else 206,
            headers={
                "etag": '"v2"' if bad == "etag" else '"v1"',
                "content-range": f"bytes {3 if bad == 'range' else 4}-{len(BODY) - 1}/{len(BODY)}",
            },
        )

    with pytest.raises(AcquisitionError):
        fetch(tmp_path, handler)
    assert not list((tmp_path / "data/raw").rglob("manifest.json"))


def test_ignored_range_200_restarts_without_concatenation(tmp_path):
    calls = []

    class Interrupted(httpx.SyncByteStream):
        def __iter__(self):
            yield BODY[:4]
            raise httpx.ReadError("interrupted")

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, headers={"etag": '"v1"'}, stream=Interrupted())
        assert request.headers["range"] == "bytes=4-"
        return response(headers={"etag": '"v2"'})

    budget = ByteBudget(100)
    result = fetch(tmp_path, handler, network_budget=budget)
    assert result.artifact.read_bytes() == BODY
    assert budget.used == 4 + len(BODY)


def test_unknown_or_weak_validator_restarts_without_range(tmp_path):
    calls = []

    class Interrupted(httpx.SyncByteStream):
        def __iter__(self):
            yield BODY[:4]
            raise httpx.ReadError("interrupted")

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, headers={"etag": 'W/"v1"'}, stream=Interrupted())
        assert "range" not in request.headers
        return response()

    assert fetch(tmp_path, handler).artifact.read_bytes() == BODY


def test_insufficient_disk_is_rejected_before_body_consumption(tmp_path):
    class Unread(httpx.SyncByteStream):
        def __iter__(self):
            pytest.fail("disk preflight must precede reading")
            yield b""

    with pytest.raises(AcquisitionError):
        fetch(
            tmp_path,
            lambda r: httpx.Response(200, headers={"content-length": "100"}, stream=Unread()),
            available_space=lambda path: 0,
        )


def test_payload_budget_survives_retries_and_stops_publication(tmp_path):
    with pytest.raises(AcquisitionError):
        fetch(tmp_path, lambda r: response(), network_budget=ByteBudget(3))
    assert not list((tmp_path / "data/raw").rglob("manifest.json"))


def test_resumed_manifest_records_observed_206_not_fabricated_200(tmp_path):
    count = []

    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield BODY[:4]
            raise httpx.ReadError("interrupted")

    def handler(request):
        count.append(request)
        if len(count) == 1:
            return httpx.Response(200, headers={"etag": '"a"'}, stream=Broken())
        return response(
            BODY[4:],
            status=206,
            headers={"etag": '"a"', "content-range": f"bytes 4-{len(BODY) - 1}/{len(BODY)}"},
        )

    result = fetch(tmp_path, handler)
    assert json.loads(result.manifest.read_text())["http_status"] == 206


def test_no_store_payload_is_not_retained_on_budget_failure(tmp_path):
    with pytest.raises(AcquisitionError):
        fetch(
            tmp_path,
            lambda r: response(headers={"etag": '"a"', "cache-control": "no-store"}),
            network_budget=ByteBudget(3),
        )
    assert not list((tmp_path / "data").rglob("partial"))


def test_new_expected_digest_does_not_block_fetch_of_a_new_version(tmp_path):
    import hashlib

    first = fetch(tmp_path, lambda r: response(headers={"etag": '"a"'}))
    changed = b"a,b\n3,4\n"
    result = fetch_cached_api(
        spec(expected_sha256=hashlib.sha256(changed).hexdigest()),
        tmp_path / "data",
        allowed_hosts={"api.example.org"},
        resolve=lambda host: ["93.184.216.34"],
        transport=httpx.MockTransport(lambda r: response(changed, headers={"etag": '"b"'})),
    )
    assert first.artifact.read_bytes() == BODY
    assert result.artifact.read_bytes() == changed


def test_retained_no_store_checkpoint_is_removed_after_process_loss(tmp_path):
    import hashlib

    from airaware.acquisition.cache import CacheState, TransferCache

    cache = TransferCache(spec(), tmp_path / "data")
    cache.partial.write_bytes(BODY[:4])
    state = CacheState(
        request_key=cache.key,
        partial_size=4,
        partial_sha256=hashlib.sha256(BODY[:4]).hexdigest(),
        partial_reusable=False,
    )
    cache.save(state)
    with pytest.raises(AcquisitionError):
        fetch(tmp_path, lambda r: pytest.fail("offline must not fetch"), offline=True)
    assert not cache.partial.exists()


def test_partial_bytes_and_saved_checksum_are_verified_before_a_new_request(tmp_path):
    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield BODY[:4]
            raise httpx.ReadError("interrupted")

    def handler(request):
        if "range" not in request.headers:
            return httpx.Response(200, headers={"etag": '"a"'}, stream=Broken())
        raise httpx.ConnectError("network unavailable")

    with pytest.raises(AcquisitionError):
        fetch(tmp_path, handler)
    partial = next((tmp_path / "data").rglob("partial"))
    partial.write_bytes(b"xxxx")
    with pytest.raises(AcquisitionError):
        fetch(tmp_path, lambda r: pytest.fail("corrupt partial must not be requested"))
    assert not list((tmp_path / "data/raw").rglob("manifest.json"))


def test_last_modified_is_used_when_no_etag_is_available(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return response(headers={"last-modified": "Thu, 01 Jan 2026 00:00:00 GMT"})
        assert request.headers["if-modified-since"] == "Thu, 01 Jan 2026 00:00:00 GMT"
        return response(b"", status=304)

    first = fetch(tmp_path, handler)
    second = fetch(tmp_path, handler)
    assert second.reused and first.artifact == second.artifact


def test_offline_refresh_is_rejected_without_network(tmp_path):
    with pytest.raises(AcquisitionError):
        fetch(tmp_path, lambda r: pytest.fail("no network"), offline=True, refresh=True)


def test_304_no_store_removes_http_cache_pointer_but_preserves_original(tmp_path):
    from airaware.acquisition.cache import TransferCache

    first = fetch(tmp_path, lambda r: response(headers={"etag": '"v1"'}))
    again = fetch(
        tmp_path, lambda r: response(b"", status=304, headers={"cache-control": "no-store"})
    )
    assert again.artifact == first.artifact and first.artifact.read_bytes() == BODY
    assert TransferCache(spec(), tmp_path / "data").load().complete_sha256 is None


def test_exhausted_budget_stops_before_starting_request(tmp_path):
    budget = ByteBudget(4)
    budget.consume(4)
    with pytest.raises(AcquisitionError):
        fetch(tmp_path, lambda r: pytest.fail("budget exhausted"), network_budget=budget)
