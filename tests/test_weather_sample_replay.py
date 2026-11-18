import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from airaware.acquisition.batch import BatchPlan
from airaware.acquisition.models import AcquisitionError, AcquisitionSpec
from airaware.acquisition.store import ingest_chunks
from airaware.acquisition.weather_sample import verify_sample

ROOT = Path(__file__).resolve().parents[1]


def test_weather_plan_pins_the_reviewed_receipt():
    plan = BatchPlan.model_validate_json(
        (ROOT / "configs/acquisition/weather-lima-sample-plan.json").read_bytes()
    )
    receipt = json.loads((ROOT / "metadata/weather-acquisition.json").read_bytes())
    keys = {
        "open-meteo-historical-weather": "era5",
        "open-meteo-previous-model-runs": "gfs_previous_day1",
    }
    assert len(plan.jobs) == receipt["totals"]["resources_published"] == 15
    assert len({job.spec.resource_url for job in plan.jobs}) == 15
    for job in plan.jobs:
        url = str(job.spec.resource_url)
        if job.spec.source_id == "noaa-isd-global-hourly":
            expected = receipt["totals"]["noaa_isd"]
            assert url == expected["resource_url"]
        else:
            query = parse_qs(urlsplit(url).query)
            lat, lon = (float(query[k][0]) for k in ("latitude", "longitude"))
            (station,) = (
                row
                for row in receipt["stations"].values()
                if row["requested"] == {"latitude": lat, "longitude": lon}
            )
            expected = station[keys[job.spec.source_id]]
        assert job.spec.expected_sha256 == expected["sha256"]
        assert job.expected_size_bytes == expected["size_bytes"]


def test_replay_requires_reviewed_bytes_without_a_transfer_cache(tmp_path):

    body = b"a,b\n1,2\n"
    source = tmp_path / "sample.csv"
    source.write_bytes(body)
    unpinned = AcquisitionSpec(
        source_id="sample",
        resource_url="https://example.org/weather.csv",
        source_page_url="https://example.org/weather",
        method="http_file",
        format="csv",
        max_bytes=1024,
    )
    data = tmp_path / "data"
    original = ingest_chunks(unpinned, [source.read_bytes()], data)
    pinned = unpinned.model_copy(update={"expected_sha256": hashlib.sha256(body).hexdigest()})
    plan = BatchPlan.model_validate({"jobs": [{"spec": pinned}]})
    assert verify_sample(plan, data) == 1

    source.write_bytes(b"a,b\n2,3\n")
    ingest_chunks(unpinned, [source.read_bytes()], data)
    original.artifact.unlink()
    with pytest.raises(AcquisitionError):
        verify_sample(plan, data)
