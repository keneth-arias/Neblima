from pathlib import Path

import pytest

from airaware.pilot_issue import Pilot


def test_late_updates_retries_rollback_and_maturity(tmp_path: Path):
    db = tmp_path / "pilot.sqlite"
    origin = 3600 * 100
    source = "a" * 64
    with Pilot(db) as p:
        p.register("f", 30, source)
        for h in range(24):
            hour = origin - (23 - h) * 3600
            p.receive("f", "s", hour, h, 10.0, hour, source)
        issue = p.begin("f", "s", origin, "b" * 64, origin + 2, max_age=3600)
        assert issue["history"] == [10.0] * 24
        p.receive("f", "s", origin, 42, 19.0, origin + 5, source)
        assert p.begin("f", "s", origin, "b" * 64, origin + 20, max_age=3600) == issue
        with pytest.raises(ValueError, match="versión"):
            p.begin("f", "s", origin, "c" * 64, origin + 21, max_age=3600)
    with Pilot(db) as p:
        saved = p.publish(issue, {"concentration": [10.0] * 6}, origin + 30)
        assert p.publish(issue, {"concentration": [10.0] * 6}, origin + 90) == saved
        with pytest.raises(ValueError, match="resultado"):
            p.publish(issue, {"concentration": [11.0] * 6}, origin + 95)
        for h in range(1, 7):
            t = origin + h * 3600
            p.receive("f", "s", t, 1, 12.0, t + 5, source)
        assert p.mature(issue, origin + 6 * 3600 + 15, delay=30) is None
        vintage = p.mature(issue, origin + 6 * 3600 + 40, delay=30)
        assert vintage is not None and vintage["observed"] == [12.0] * 6
        p.receive("f", "s", origin + 3600, 2, 17.0, origin + 7 * 3600, source)
        assert p.mature(issue, origin + 8 * 3600, delay=30) == vintage
        assert (
            p.begin("f", "s", origin + 3600, "c" * 64, origin + 3610, max_age=3600)["history"][-2]
            == 19.0
        )


def test_missing_or_stale_issue_is_explicit(tmp_path: Path):
    with Pilot(tmp_path / "db") as p:
        p.register("f", 30, "a" * 64)
        issue = p.begin("f", "s", 360000, "f" * 64, 360001, max_age=600)
        assert issue["reason"] == "missing_history"
        late = p.begin("f", "s", 363600, "f" * 64, 365000, max_age=600)
        assert late["reason"] == "stale"


def test_two_writers_obtain_same_first_issue(tmp_path: Path):
    from concurrent.futures import ThreadPoolExecutor

    db = tmp_path / "pilot.sqlite"
    with Pilot(db) as p:
        p.register("feed", 30, "a" * 64)
        first = p.begin("feed", "station", 360000, "a" * 64, 360000, max_age=3600)

    def publish(second):
        with Pilot(db) as writer:
            same = writer.begin("feed", "station", 360000, "a" * 64, 360000 + second, max_age=3600)
            assert same == first
            return writer.publish(same, {"abstained": "missing_history"}, 360000 + second)

    with ThreadPoolExecutor(2) as pool:
        a, b = pool.map(publish, [5, 6])
    assert a == b


def test_source_maturity_cannot_be_reselected_after_issuance(tmp_path: Path):
    with Pilot(tmp_path / "db") as p:
        p.register("s", 3600, "c" * 64)
        with pytest.raises(ValueError):
            p.register("s", 0, "d" * 64)
        issue = p.begin("s", "station", 360000, "b" * 64, 360010, max_age=90)
        p.publish(issue, {"abstained": "missing_history"}, 360000 + 8 * 3600)
        assert p.mature(issue, 360000 + 7 * 3600, delay=3600) is None
        with pytest.raises(ValueError):
            p.mature(issue, 360000 + 8 * 3600, delay=0)
