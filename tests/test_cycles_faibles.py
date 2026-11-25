"""Pic bref suivi d'un régime faible : segmentation, cycles et comptage."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ha_stub import C, E, make  # noqa: E402

T0 = 1_800_000_000


def samples(power, step=15, end=2100):
    ts = list(range(0, end + 1, step))
    return [T0 + t for t in ts], [300 + power(t) for t in ts]


def low_load(t):
    return 1000 if 600 <= t < 615 else 100 if 615 <= t < 1500 else 0


def test_plateau_duration_power_energy():
    ts, ps = samples(low_load)
    found, opened = E.segment(ts, ps)
    assert opened is None and len(found) == 1, (found, opened)
    event = found[0]
    f = E.features(event["prof"], 12)
    assert event["start"] == T0 + 600 and event["end"] == T0 + 1500, event
    assert f["D"] == 900 and f["P"] == 100, f
    assert abs(f["wh"] - (1000 * 15 + 100 * 885) / 3600) < 0.1, f
    assert E.start_spike(event["prof"]) == 10


def small_curve(changes, end=1200):
    ts = [T0 + t for t in range(0, end + 1, 15)]
    ps = [60 + sum(delta for a, b, delta in changes if a <= t < b)
          for t in range(0, end + 1, 15)]
    return ts, ps


def test_small_plateau_is_relative_to_the_preceding_60w_baseline():
    ts, ps = small_curve([(300, 600, 10)])
    found, opened = E.segment(ts, ps, 350, 10)
    assert opened is None and len(found) == 1, (found, opened)
    assert found[0]["base"] == 60 and found[0]["start"] == T0 + 300
    assert found[0]["end"] == T0 + 600 and E.features(found[0]["prof"], 12)["P"] == 10
    assert not E.segment(ts, ps, 350, 11)[0]
    assert not E.segment(*small_curve([(300, 600, 0)]), 350, 10)[0]


def test_isolated_small_spikes_and_baseline_noise_are_rejected():
    ts, ps = small_curve([(300, 315, 10)])
    assert not E.segment(ts, ps, 350, 10)[0]
    ts, ps = small_curve([])
    for i, t in enumerate(ts):
        if t >= T0 + 300 and t < T0 + 750:
            ps[i] += 15 if i % 2 else 0
    assert not E.segment(ts, ps, 350, 10)[0]


def test_short_variable_small_load_keeps_its_whole_profile():
    ts, ps = small_curve([(300, 315, 15), (315, 330, 25), (330, 345, 12),
                          (345, 360, 20), (360, 375, 10)])
    found, opened = E.segment(ts, ps, 350, 10)
    assert opened is None and len(found) == 1, (found, opened)
    assert found[0]["start"] == T0 + 300 and found[0]["end"] == T0 + 375
    assert found[0]["prof"] == [15, 25, 12, 20, 10]
    live, opened = E.segment(ts[:23], ps[:23], 350, 10)
    assert not live and opened == T0 + 300


def test_small_load_does_not_end_after_a_larger_overlapping_peak():
    ts, ps = small_curve([(300, 900, 12), (450, 600, 1500)])
    found, opened = E.segment(ts, ps, 350, 10)
    assert opened is None and len(found) == 1, (found, opened)
    assert found[0]["end"] == T0 + 900


def test_noise_does_not_keep_small_events_running_or_hide_large_loads():
    import random
    rng = random.Random(17)
    ts, ps = small_curve([(300, 450, 90), (750, 900, 1500)])
    ps = [p + rng.gauss(0, 6) for p in ps]
    found, opened = E.segment(ts, ps, 350, 10)
    assert opened is None and len(found) == 2, (found, opened)
    assert abs(found[0]["start"] - (T0 + 300)) <= 15
    assert abs(found[0]["end"] - (T0 + 450)) <= 30
    assert abs(found[1]["start"] - (T0 + 750)) <= 15
    assert abs(found[1]["end"] - (T0 + 900)) <= 30


def test_recent_level_changes_do_not_mask_a_new_small_load():
    ts, ps = small_curve([(300, 450, 90), (750, 840, 10)])
    found, opened = E.segment(ts, ps, 350, 10)
    assert opened is None and len(found) == 2, (found, opened)
    assert found[1]["start"] == T0 + 750 and found[1]["end"] == T0 + 840


def test_small_load_can_rise_across_several_samples():
    ts, ps = small_curve([(300, 315, 6), (315, 330, 12), (330, 345, 18),
                          (345, 390, 24)])
    found, opened = E.segment(ts, ps, 350, 10)
    assert opened is None and len(found) == 1, (found, opened)
    assert found[0]["start"] == T0 + 315 and found[0]["end"] == T0 + 390


def test_small_plateau_range_without_a_startup_spike():
    for power in (60, 90, 150, 230):
        ts, ps = small_curve([(300, 900, power)])
        found, opened = E.segment(ts, ps, 350, 10)
        assert opened is None and len(found) == 1, (power, found, opened)
        assert found[0]["start"] == T0 + 300 and found[0]["end"] == T0 + 900
        assert E.features(found[0]["prof"], 12)["P"] == power
        co = make()
        live = co._live_parts(ts[:41], ps[:41], T0 + 300)
        assert len(live) == 1 and live[0]["p"] == power, (power, live)


def test_small_overlapping_load_steps_split_into_distinct_profiles():
    ts, ps = small_curve([(300, 900, 12), (450, 750, 20)])
    found, opened = E.segment(ts, ps, 350, 10)
    assert opened is None and len(found) == 1, (found, opened)
    parts = E.split_session(found[0]["prof"], 10, 10)
    assert len(parts) == 2, parts
    assert sorted(max(prof) for _, prof in parts) == [12, 20], parts
    coordinated = make()._parts(found[0])
    assert sorted(part["f"]["P"] for part in coordinated) == [12, 20], coordinated
    assert E.dist(E.features([12] * 16, 8), E.features([12] * 8 + [0] * 8, 8)) > 1
    fast_ts, fast_ps = small_curve([(300, 900, 12), (360, 750, 20)])
    fast, opened = E.segment(fast_ts, fast_ps, 350, 10)
    assert opened is None and len(fast) == 1 and fast[0]["start"] == T0 + 300, (fast, opened)
    assert len(E.split_session(fast[0]["prof"], 10, 10)) == 2


def test_dishwasher_keeps_stable_low_phase_after_later_heating_peak():
    ts, ps = small_curve([(300, 420, 1000), (420, 900, 100)])
    found, opened = E.segment(ts, ps, 350, 10)
    assert opened is None and len(found) == 1, (found, opened)
    assert found[0]["start"] == T0 + 300 and found[0]["end"] == T0 + 900
    assert E.features(found[0]["prof"], 12)["D"] == 600


def test_confirmed_group_similarity_uses_the_complete_profile():
    first = E.features([1000] * 4 + [100] * 12, 8)
    similar = E.features([950] * 4 + [100] * 12, 8)
    different = E.features([100] * 12 + [1000] * 4, 8)
    assert E._kernel(first, similar) > E._kernel(first, different)


def test_irregular_sampling_and_short_pause():
    rng = random.Random(42)
    ts = [0]
    while ts[-1] < 2100:
        ts.append(ts[-1] + rng.randint(8, 23))
    def power(t):
        if 600 <= t < 630:
            return 950
        if 630 <= t < 1500 and not 960 <= t < 1020:
            return 100
        return 0
    found, _ = E.segment([T0 + t for t in ts], [300 + power(t) for t in ts])
    assert len(found) == 1, found
    f = E.features(found[0]["prof"], 12)
    assert abs(found[0]["end"] - (T0 + 1500)) < 30 and f["P"] == 100, (found, f)
    assert f["cyc"] == 2 and f["on"] < 1, f


def test_isolated_spike_and_independent_load():
    def power(t):
        return 1000 if 600 <= t < 615 else 100 if 900 <= t < 1500 else 0
    ts, ps = samples(power)
    found, _ = E.segment(ts, ps)
    assert len(found) == 2 and found[0]["end"] == T0 + 615, found
    assert E.features(found[0]["prof"], 12)["P"] == 1000
    assert found[1]["start"] == T0 + 900 and found[1]["end"] == T0 + 1500
    assert E.features(found[1]["prof"], 12)["P"] == 100


def test_low_plateau_too_short_or_unstable():
    for power in (
        lambda t: 1000 if 600 <= t < 615 else 100 if 615 <= t < 660 else 0,
        lambda t: 1000 if 600 <= t < 615 else (80 if (t // 15) % 2 else 150) if 615 <= t < 900 else 0,
    ):
        ts, ps = samples(power)
        found, _ = E.segment(ts, ps)
        assert len(found) == 1 and found[0]["end"] == T0 + 615, found


def test_long_pause_ends_event_without_inventing_restart():
    def power(t):
        if 600 <= t < 615:
            return 1000
        if 615 <= t < 900 or 1125 <= t < 1500:
            return 100
        return 0
    ts, ps = samples(power)
    found, opened = E.segment(ts, ps)
    assert opened is None and len(found) == 2 and found[0]["end"] == T0 + 900, found
    assert found[1]["start"] == T0 + 1125 and found[1]["end"] == T0 + 1500, found


def test_measured_socket_is_not_reattributed():
    ts, ps = samples(low_load)
    subs = [p - 300 for p in ps]
    found, opened = E.segment(ts, E.realign(ts, ps, subs))
    assert not found and opened is None, (found, opened)


def test_overlapping_appliance_and_live():
    def power(t):
        return low_load(t) + (1500 if 900 <= t < 1080 else 0)
    ts, ps = samples(power)
    found, _ = E.segment(ts, ps)
    assert len(found) == 1, found
    prof = found[0]["prof"]
    parts = E.split_session(prof)
    assert len(parts) == 2, parts
    (a, low), (b, high) = parts
    assert a == 0 and b == 20 and len(high) == 12, (a, b, len(high))
    assert E.features(low, 12)["P"] == 100 and E.features(high, 12)["P"] == 1500
    for k, value in enumerate(prof):
        assert value == low[k] + (high[k - b] if b <= k < b + len(high) else 0)
    live = E.live_parts(prof[:26])
    assert sorted(x["h"] for x in live if x["running"]) == [100, 1500], live
    saved = make()._parts(found[0])
    assert len(saved) == 2 and saved[0]["f"]["spike"] == 10, saved


def test_cut_does_not_count_missing_time():
    ts, ps = samples(low_load)
    rows = [(t, p) for t, p in zip(ts, ps) if not T0 + 1000 <= t < T0 + 1750]
    found, _ = E.segment(*map(list, zip(*rows)))
    assert len(found) == 1 and found[0]["end"] <= T0 + 1020, found


def test_sparse_reports_confirm_plateau_before_stop():
    ts = [T0 + t for t in (0, 590, 600, 615, 1200, 1500, 1665, 1800)]
    ps = [300, 300, 1300, 400, 400, 300, 300, 300]
    found, _ = E.segment(ts, ps)
    assert len(found) == 1 and found[0]["end"] == T0 + 1500, found


def test_split_preserves_noisy_energy():
    prof = [1000] + [100, 105, 95, 105, 100, 95, 105] + [1605] * 12 + [105] * 10
    parts = E.split_session(prof)
    assert len(parts) == 2, parts
    assert sum(sum(p) for _, p in parts) == sum(prof)


def test_coordinator_live_and_persistence():
    ts, ps = samples(low_load)
    co = make()
    real_time = C.time.time
    try:
        for start, end in ((0, 900), (900, 2100)):
            C.time.time = lambda end=end: T0 + end
            co.store.add_samples([(t, p, 0) for t, p in zip(ts, ps) if T0 + start <= t <= T0 + end])
            if start == 0:
                co.processed_until = ts[0]
            co._process()
            if start == 0:
                assert len(co.running_parts) == 1 and co.running_parts[0]["p"] == 100, co.running_parts
                part = co.running_parts[0]
                part["hint_group"] = "known-low"
                co.groups["known-low"] = {"name": "Test"}
                co.cents["known-low"] = {"P": 100, "D": 900, "shape": "stable"}
                co._auto_track()
                assert not co.tracks
                del co.groups["known-low"]
                del co.cents["known-low"]
                co._action({"action": "label_now", "name": "Test", "at": part["start"], "p": part["p"]})
                assert not co.tracks and co.pending, (co.tracks, co.pending)
        assert len(co.evs) == 1 and co.evs[0].f["P"] == 100 and co.evs[0].f["D"] == 900, co.evs
        assert co.groups[co.evs[0].gid]["name"] == "Test" and not co.pending
        co._process()
        assert len(co.evs) == 1, co.evs
    finally:
        C.time.time = real_time


if __name__ == "__main__":
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_"):
            test()
            print("ok", name)
