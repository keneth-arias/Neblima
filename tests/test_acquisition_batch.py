from datetime import date

import pytest
from pydantic import ValidationError

from airaware.acquisition import AcquisitionError, AcquisitionSpec
from airaware.acquisition.batch import AcquisitionJob, ByteBudget, estimate_jobs, select_jobs


def job(**changes):
    return AcquisitionJob.model_validate(
        {
            "spec": {
                "source_id": "demo",
                "resource_url": "https://api.example.org/data",
                "api_documentation_url": "https://api.example.org/docs",
                "method": "api",
                "format": "csv",
                "max_bytes": 1024,
            },
            "start": "2026-01-01",
            "end": "2026-01-31",
            "region": "Lima",
            "expected_size_bytes": 100,
            **changes,
        }
    )


def test_per_file_limit_is_1000_gib_not_an_allocation():
    value = job().spec.model_dump()
    value["max_bytes"] = 1000 * 1024**3
    assert AcquisitionSpec.model_validate(value).max_bytes == 1073741824000
    with pytest.raises(ValidationError):
        AcquisitionSpec.model_validate({**value, "max_bytes": 1073741824001})


def test_budget_is_shared_and_rejects_overrun():
    budget = ByteBudget(10)
    budget.consume(7)
    assert budget.used == 7
    with pytest.raises(AcquisitionError):
        budget.consume(4)
    assert budget.used == 11  # Incluye bytes recibidos aunque excedan el presupuesto.


def test_filters_use_inclusive_metadata_overlap_and_deduplicate():
    jobs = [job(), job(), job(region="Callao"), job(start=None, end=None)]
    selected = select_jobs(
        jobs, sources={"demo"}, regions={"Lima"}, start=date(2026, 1, 31), end=date(2026, 2, 1)
    )
    assert selected == [jobs[0]]
    assert select_jobs(jobs, start=date(2026, 2, 1)) == []
    assert select_jobs(jobs, sources={"other"}) == []


def test_unknown_coverage_is_not_invented_when_filtering_dates():
    assert select_jobs([job(start=None, end=None)], start=date(2026, 1, 1)) == []
    with pytest.raises(AcquisitionError):
        select_jobs([job()], start=date(2026, 2, 1), end=date(2026, 1, 1))


def test_estimate_is_local_and_separates_unknown_sizes(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("No debe resolver DNS ni consultar la red")

    monkeypatch.setattr("socket.getaddrinfo", no_network)
    jobs = [job(), job(expected_size_bytes=None)]
    result = estimate_jobs(jobs)
    assert result["known_size_bytes"] == 100
    assert result["unknown_count"] == 1
    assert result["authorized_max_bytes"] == 2048
    assert not list(tmp_path.iterdir())


def test_local_file_estimate_uses_stat_without_relabelling_catalogue_size(tmp_path):
    original = tmp_path / "file.csv"
    original.write_bytes(b"a,b\n1,2\n")
    value = job().spec.model_dump()
    value["method"] = "lightpanda"
    result = estimate_jobs([job(spec=value, local_file=original, expected_size_bytes=999)])
    assert result["known_size_bytes"] == len(original.read_bytes())
    assert result["resources"][0]["size_origin"] == "local_stat"


def test_execute_rejects_unestimated_network_jobs_without_explicit_authorization(tmp_path):
    from airaware.acquisition.batch import execute_jobs

    with pytest.raises(AcquisitionError):
        execute_jobs(
            [job(expected_size_bytes=None)],
            tmp_path / "data",
            budget_bytes=1024,
            allowed_hosts={"api.example.org"},
            fetcher=lambda *a, **k: pytest.fail("not authorized"),
        )


def test_batch_concurrency_budget_and_deduplication(tmp_path):
    import threading

    from airaware.acquisition.batch import execute_jobs
    from airaware.acquisition.models import AcquisitionResult

    barrier = threading.Barrier(2)
    seen = []

    def fetcher(spec, data_dir, **kwargs):
        seen.append((spec.source_id, id(kwargs["network_budget"])))
        barrier.wait(timeout=5)
        kwargs["network_budget"].consume(3)
        return AcquisitionResult(tmp_path / "artifact", tmp_path / "manifest", False)

    second = job().spec.model_dump()
    second["source_id"] = "second"
    first = job()
    result = execute_jobs(
        [first, first, job(spec=second)],
        tmp_path / "data",
        budget_bytes=1000,
        workers=2,
        allowed_hosts={"api.example.org"},
        fetcher=fetcher,
    )
    assert len(result["completed"]) == 2 and not result["errors"]
    assert len(seen) == 2 and len({b for _, b in seen}) == 1
    assert result["network_bytes"] == 6


def test_batch_budget_preflight_happens_before_any_transfer(tmp_path):
    from airaware.acquisition.batch import execute_jobs

    with pytest.raises(AcquisitionError):
        execute_jobs(
            [job()],
            tmp_path / "data",
            budget_bytes=50,
            allowed_hosts={"api.example.org"},
            fetcher=lambda *a, **k: pytest.fail("budget insufficient"),
        )


def test_local_offline_batch_needs_no_network_budget(tmp_path):
    from airaware.acquisition.batch import execute_jobs

    original = tmp_path / "input.csv"
    original.write_bytes(b"a,b\n1,2\n")
    value = job().spec.model_dump()
    value["method"] = "local"
    result = execute_jobs(
        [job(spec=value, local_file=original)],
        tmp_path / "data",
        budget_bytes=0,
        offline=True,
        allowed_hosts=set(),
    )
    assert not result["errors"] and result["network_bytes"] == 0
    assert result["completed"][0].artifact.read_bytes() == original.read_bytes()
