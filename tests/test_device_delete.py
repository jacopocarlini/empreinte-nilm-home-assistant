"""Deleting a recognised appliance removes its HA entries but preserves unassigned uses."""
import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.dirname(__file__))
from ha_stub import C, E, FakeEntry, make, stub  # noqa: E402


def fixture(status="valide"):
    co = make()
    group = co._new_group()
    group.update(name="Lamp", status=status, energy_dash=True)
    profile = [500] * 8
    features = E.features(profile, 12)
    eid = co.store.add_event(1800000000, 1800000120, 300, profile, features)
    ev = E.Ev(eid, features, gid=group["id"], pinned=True)
    co.evs.append(ev)
    co.rows[eid] = {"start": 1800000000, "end": 1800000120, "base": 300, "prof": profile}
    co._recompute()
    co._save()
    return co, group["id"], ev


def test_delete_preserves_uses_and_cancels_recreation():
    co, gid, ev = fixture()
    co.pending = [{"name": "Lamp", "t": 1}, {"name": "Other", "t": 2}]
    co.tracks = [{"name": "Lamp", "id": "t1"}, {"name": "Other", "id": "t2"}]
    co.hints = {ev.id: "Lamp"}
    co.doubts = {ev.id}
    ev.excluded.add(gid)
    co._action({"action": "delete", "gid": gid})
    assert gid not in co.groups and gid not in co.cents
    assert co.store.events()[0]["id"] == ev.id
    assert ev.gid is None and ev.pinned and not ev.probable
    assert gid not in ev.excluded and not co.hints and not co.doubts
    assert [p["name"] for p in co.pending] == ["Other"]
    assert [t["name"] for t in co.tracks] == ["Other"]
    co._cluster()
    assert ev.gid is None and not co.groups
    restarted = C.Coordinator(co.hass, FakeEntry())
    restarted.store = co.store
    restarted._load()
    assert gid not in restarted.groups
    assert restarted.evs[0].gid is None and restarted.evs[0].pinned
    assert [t["name"] for t in restarted.tracks] == ["Other"]
    co._action({"action": "undo"})
    assert co.groups[gid]["name"] == "Lamp" and ev.gid == gid
    assert len(co.tracks) == 2 and len(co.pending) == 2
    assert co.hints == {ev.id: "Lamp"} and co.doubts == {ev.id}


async def test_delete_removes_loaded_and_disabled_registry_entries():
    original_er = C.er.async_get
    original_entries = getattr(C.er, "async_entries_for_config_entry", None)
    original_dr, original_devices = C.dr.async_get, C.dr.async_entries_for_config_entry
    try:
        for status in ("valide", "nomme"):
            co, gid, ev = fixture(status)
            removed_entities, removed_devices = [], []
            entries = [
                types.SimpleNamespace(entity_id="sensor.lamp_energy", unique_id=f"empreinte_{gid}_energie"),
                types.SimpleNamespace(entity_id="sensor.lamp_disabled", unique_id=f"empreinte_{gid}_puissance"),
                types.SimpleNamespace(entity_id="sensor.other", unique_id=f"empreinte_{gid}0_energie"),
            ]
            reg = types.SimpleNamespace(async_get=lambda eid: next((e for e in entries if e.entity_id == eid), None),
                                        async_remove=removed_entities.append)
            C.er.async_get = lambda hass: reg
            C.er.async_entries_for_config_entry = lambda registry, entry_id: entries
            C.dr.async_get = lambda hass: types.SimpleNamespace(async_remove_device=removed_devices.append)
            device = types.SimpleNamespace(id="device-lamp", identifiers={("empreinte", gid)})
            C.dr.async_entries_for_config_entry = lambda registry, entry_id: [device]
            co.entities = {gid: [types.SimpleNamespace(entity_id="sensor.lamp_energy")]} if status == "valide" else {}
            async def executor(func, *args):
                return func(*args)
            preferences = {"device_consumption": [{"stat_consumption": "sensor.empreinte_lamp_energie"},
                                                   {"stat_consumption": "sensor.other_energy"}]}
            async def update(values):
                preferences.update(values)
            async def manager(hass):
                return types.SimpleNamespace(data=preferences, async_update=update)
            stub("homeassistant.components.energy")
            stub("homeassistant.components.energy.data", async_get_manager=manager)
            co.hass.async_add_executor_job = executor
            co.add_entities["sensor"] = lambda entities: None
            co.ensure_entities = lambda: None
            co.push_entities = lambda: None
            await co.async_action({"action": "delete", "gid": gid})
            assert sorted(removed_entities) == ["sensor.lamp_disabled", "sensor.lamp_energy"]
            assert removed_devices == ["device-lamp"]
            assert ev.gid is None and gid not in co.entities
            assert preferences["device_consumption"] == [{"stat_consumption": "sensor.other_energy"}]
    finally:
        C.er.async_get = original_er
        if original_entries is None:
            del C.er.async_entries_for_config_entry
        else:
            C.er.async_entries_for_config_entry = original_entries
        C.dr.async_get, C.dr.async_entries_for_config_entry = original_dr, original_devices


async def main():
    test_delete_preserves_uses_and_cancels_recreation()
    await test_delete_removes_loaded_and_disabled_registry_entries()
    print("ok device deletion")


if __name__ == "__main__":
    asyncio.run(main())
