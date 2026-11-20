"""Comprobar los avisos anticipados con observaciones y una emisión tardía."""

from airaware.episode_warnings import Origin, evaluate, select_policy


def test_cooldown_overlap_holes_and_active_state():
    measurements = {h: (21.0 if h in (4, 6, 7, 8) else 5.0) for h in range(30)}
    measurements.pop(13)
    origins = [Origin(h, h + 0.1, 0.9, measurements[h]) for h in (0, 1, 6, 9, 16, 23)]
    result = evaluate(origins, measurements, 20, 0.7)
    assert result["counts"] == {
        "hit": 1,
        "false": 2,
        "indeterminate": 1,
        "active": 1,
        "suppressed": 1,
        "below_cut": 0,
        "abstained": 0,
    }
    assert result["matched_onsets"] == [4]
    assert result["lead_hours"] == [3.9]
    assert result["evaluable_origins"] == 4
    assert result["emitted"] == 4


def test_delayed_warning_cannot_claim_earlier_onset():
    y = {i: float(i == 2) * 20 for i in range(15)}
    r = evaluate([Origin(0, 2.5, 0.9, 0.0)], y, 20, 0.5)
    assert r["counts"]["false"] == 1 and r["late"] == 1


def test_selection_prefers_new_onsets_under_station_budget():
    observations = {h: float(h == 5) * 20 for h in range(180)}
    frames = [Origin(h, float(h), float(h == 2), observations[h]) for h in range(170)]
    good = evaluate(frames, observations, 20, 0.7)
    over = evaluate(
        [Origin(o.hour, o.issued, 0.99, o.latest) for o in frames], observations, 20, 0.8
    )
    selected = select_policy(
        [
            ("reference", 0.7, {"s": good}),
            ("episode", 0.8, {"s": over}),
            ("episode", 0.9, {"s": good}),
        ],
        calibration={"reference": (0.1, 0.2), "episode": (0.1, 0.2)},
    )
    assert selected is not None and selected["method"] == "reference"


def test_one_to_one_and_block_uncertainty():
    from airaware.episode_warnings import paired_interval

    y = {h: 25.0 if h in (5, 6) else 10.0 for h in range(15)}
    r = evaluate([Origin(0, 0.0, 0.9, 10.0), Origin(1, 1.0, 0.9, 10.0)], y, 20, 0.5, cooldown=0)
    assert r["counts"]["hit"] == 1 and r["counts"]["false"] == 1
    estimate = paired_interval(
        [0, 1, 168, 169], [2.0, 3.0, 6.0, 7.0], [1.0, 2.0, 5.0, 6.0], draws=50
    )
    assert estimate == {"blocks": 2, "difference": 1.0, "lower": 1.0, "upper": 1.0}
    assert paired_interval([0], [2.0], [3.0], draws=10)["lower"] is None


def test_reference_fixture_reconciles_abstentions_and_misses():
    from pathlib import Path

    from airaware.episode_warnings import replay_fixture

    root = Path(__file__).resolve().parents[1] / "docs/methodology/episodios-v1"
    result = replay_fixture(root / "inferencia/ventanas.json", root / "evaluacion/objetivos.json")
    assert sum(s["counts"]["hit"] for s in result.values()) == 2
    assert sum(s["counts"]["active"] for s in result.values()) == 1
    assert sum(s["counts"]["indeterminate"] for s in result.values()) == 1
    assert sum(s["counts"]["false"] for s in result.values()) == 1


def test_expired_origins_cannot_subsidize_false_warnings():
    y = {h: 0.0 for h in range(180)}
    origins = [Origin(0, 0.0, 1.0, 0.0), *[Origin(h, h + 7.0, 0.0, 0.0) for h in range(1, 168)]]
    r = evaluate(origins, y, 1.0, 0.5)
    assert (r["evaluable_origins"], r["false_per_station_week"], r["expired_origins"]) == (
        1,
        168.0,
        167,
    )
    assert select_policy([("episode", 0.5, {"s": r})], calibration={"episode": (0.1, 0.2)}) is None


def test_onset_crossing_block_retains_original_warning():
    from airaware.episode_warnings import paired_detection

    y = {h: float(h in (168, 335)) for h in range(160, 343)}
    a = [Origin(166, 166.0, 1.0, 0.0), Origin(333, 333.0, 0.0, 0.0)]
    b = [Origin(166, 166.0, 0.0, 0.0), Origin(333, 333.0, 0.0, 0.0)]
    r = paired_detection({"s": evaluate(a, y, 1.0, 0.5)}, {"s": evaluate(b, y, 1.0, 0.5)})
    assert r["difference"] == 0.5
