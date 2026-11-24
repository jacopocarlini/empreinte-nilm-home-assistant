"""Configurable sensitivity must affect segmentation, live detection and reanalysis."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(__file__))
from ha_stub import C, E, FakeEntry, make  # noqa: E402

T0 = 1_800_000_000


def samples(delta):
    times = [T0 + t for t in range(0, 1801, 15)]
    return times, [300 + (delta if T0 + 600 <= t < T0 + 1200 else 0) for t in times]


def test_threshold_and_low_power_event():
    ts, ps = samples(50)
    assert not E.segment(ts, ps)[0]
    events, opened = E.segment(ts, ps, 50)
    assert opened is None and len(events) == 1
    event = events[0]
    assert (event["start"], event["end"]) == (T0 + 600, T0 + 1200)
    assert E.features(event["prof"], 12)["P"] == 50
    assert E.live_parts(event["prof"][:10], 50)[0]["h"] == 50
    assert not E.segment(*samples(49), 50)[0]


def test_live_and_overlapping_load():
    live = C.Live(50)
    cents = {"lamp": {"P": 50, "cyc": 0}}
    for t, power in [(0, 300), (15, 350), (75, 350)]:
        live.feed(t, power, cents)
    assert "lamp" in live.running
    live.feed(90, 300, cents)
    assert live.running["lamp"]["off_since"] == 90
    live.feed(255, 300, cents)
    assert "lamp" not in live.running
    parts = E.split_session([1000] * 8 + [1050] * 8 + [1000] * 8, 50, 50)
    assert len(parts) == 2, parts
    assert sorted(max(profile) for _, profile in parts) == [50, 1000]


def test_extract_and_preserve_low_power_load():
    profile = [50] * 8 + [1050] * 8 + [50] * 8
    result = E.extract_component(profile, 8, 1000, 50, 50)
    assert result is not None
    _, part, rest = result
    assert max(part) == 1000
    assert rest == [50] * len(profile)
    assert E.clean_rest(rest, min_level=50 * E.OFF_W / E.ON_W) == rest


def test_realign_measured_plug_at_low_power():
    ts = [T0 + i * 15 for i in range(8)]
    mains = [300, 300, 350, 350, 350, 300, 300, 300]
    plug = [0, 0, 0, 50, 50, 50, 0, 0]
    assert E.realign(ts, mains, plug, 50) == [300] * len(ts)


def test_threshold_change_reanalyses_stored_samples():
    co = make()
    ts, ps = samples(50)
    co.store.add_samples([(t, p, 0) for t, p in zip(ts, ps)])
    co.processed_until = ts[0]
    old_time = C.time.time
    C.time.time = lambda: ts[-1]
    try:
        co._process()
        assert not co.evs
        entry = types.SimpleNamespace(data=FakeEntry.data, options={**FakeEntry.options, "detection_w": 50}, entry_id="test")
        new = C.Coordinator(co.hass, entry)
        new.store = co.store
        new._load()
        assert new.store.get_meta("detection_w") == 50
        new._process()
        assert len(new.evs) == 1 and new.evs[0].f["P"] == 50
        assert new.state_payload()["status"]["detection_w"] == 50
    finally:
        C.time.time = old_time


if __name__ == "__main__":
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_"):
            test()
            print("ok", name)
