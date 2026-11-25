"""Vérifie le réglage de langue et les traductions des formulaires."""
import asyncio
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(__file__))
from ha_stub import C, FakeEntry, make, stub  # noqa: E402


class Marker:
    def __init__(self, key, **kwargs):
        self.key = key
        self.kwargs = kwargs


stub("voluptuous", Required=Marker, Optional=Marker, Schema=lambda x: x)


class ConfigFlow:
    def __init_subclass__(cls, **kwargs):
        pass


class OptionsFlow:
    def async_create_entry(self, **kwargs):
        return kwargs

    def async_show_form(self, **kwargs):
        return kwargs


sys.modules["homeassistant"].config_entries = stub(
    "homeassistant.config_entries", ConfigFlow=ConfigFlow, OptionsFlow=OptionsFlow)
selector = types.SimpleNamespace()
for name in ("EntitySelector", "EntitySelectorConfig", "NumberSelector", "NumberSelectorConfig",
             "SelectSelector", "SelectSelectorConfig", "TextSelector"):
    setattr(selector, name, lambda *args, **kwargs: (args, kwargs))
selector.NumberSelectorMode = types.SimpleNamespace(BOX="box")
sys.modules["homeassistant.helpers"].selector = selector
from empreinte import config_flow as F  # noqa: E402
from empreinte.text import APPLIANCE_NAMES, display_appliance, display_text  # noqa: E402


def test_schema_and_save_preserves_shared_plugs():
    schema = F._options_schema({"language": "it", "measured": ["sensor.plug"]})
    language = next(k for k in schema if k.key == "language")
    assert language.kwargs["default"] == "it"
    values = schema[language][0][0][1]["options"]
    assert [v["value"] for v in values] == ["fr", "en", "it"]
    default = next(k for k in F._options_schema({}) if k.key == "language")
    assert default.kwargs["default"] == "fr"
    flow = F.EmpreinteOptions()
    plugs = [{"entity": "sensor.plug", "names": ["Washer"]}]
    flow.config_entry = types.SimpleNamespace(options={"shared_plugs": plugs})
    result = asyncio.run(flow.async_step_reglages({"language": "en", "measured": ["sensor.other"]}))
    assert result["data"] == {"language": "en", "measured": ["sensor.other"], "shared_plugs": plugs}
    flow.config_entry.options = result["data"]
    result = asyncio.run(flow.async_step_prises({"shared_plug": None, "shared_names": "", "shared_remove": []}))
    assert result["data"]["language"] == "en" and result["data"]["shared_plugs"] == plugs


def test_payload_and_fallback():
    co = make()
    assert co.state_payload()["status"]["language"] == "fr"
    entry = types.SimpleNamespace(data=FakeEntry.data, options={**FakeEntry.options, "language": "it"})
    assert C.Coordinator(types.SimpleNamespace(), entry).language == "it"
    entry.options["language"] = "invalid"
    assert C.Coordinator(types.SimpleNamespace(), entry).language == "fr"


def test_translation_keys():
    folder = os.path.join(os.path.dirname(__file__), "..", "custom_components", "empreinte")
    def keys(node, prefix=""):
        if not isinstance(node, dict):
            return {prefix}
        return set().union(*(keys(value, f"{prefix}.{key}") for key, value in node.items()))
    with open(os.path.join(folder, "strings.json"), encoding="utf-8") as f:
        expected = keys(json.load(f))
    for language in ("fr", "en", "it"):
        with open(os.path.join(folder, "translations", language + ".json"), encoding="utf-8") as f:
            got = keys(json.load(f))
        assert got == expected, (language, expected - got, got - expected)


def test_display_labels_preserve_user_names():
    coord = types.SimpleNamespace(language="it")
    assert display_text(coord, "puissance") == "potenza"
    assert display_text(coord, "énergie") == "energia"
    assert display_text(coord, "Lavatrice personale") == "Lavatrice personale"
    coord.language = "en"
    assert display_text(coord, "en marche") == "running"
    assert display_text(coord, "Non identifié") == "Unidentified"
    coord.language = "fr"
    assert display_text(coord, "Non identifié") == "Non identifié"
    assert display_appliance(coord, "Lave-linge") == "Lave-linge"
    coord.language = "it"
    assert display_appliance(coord, "Lave-linge") == "Lavatrice"
    assert display_appliance(coord, "Lavatrice personale") == "Lavatrice personale"
    coord.language = "en"
    assert display_appliance(coord, "Lave-vaisselle") == "Dishwasher"
    assert {v[0] for v in C.engine.KINDS.values()} <= set(APPLIANCE_NAMES)
    co = make()
    co.pending = [{"at": 1000, "p": 1000, "name": "Lave-linge", "maybe": True, "t": 1001}]
    assert co._pending_for(1000, 1000) == {
        "name": "peut-être Lave-linge", "raw_name": "Lave-linge", "maybe": True, "t": 1001}


def test_sensor_names_keep_identifiers():
    class Entity:
        pass

    class SensorEntity(Entity):
        pass

    class BinarySensorEntity(Entity):
        pass

    class ButtonEntity(Entity):
        pass

    stub("homeassistant.helpers.entity", Entity=Entity)
    sys.modules["homeassistant.helpers.device_registry"].DeviceInfo = lambda **kwargs: kwargs
    stub("homeassistant.components.sensor", SensorEntity=SensorEntity,
         SensorDeviceClass=types.SimpleNamespace(POWER="power", ENERGY="energy", MONETARY="money"),
         SensorStateClass=types.SimpleNamespace(MEASUREMENT="measurement", TOTAL="total", TOTAL_INCREASING="total_increasing"))
    stub("homeassistant.components.binary_sensor", BinarySensorEntity=BinarySensorEntity,
         BinarySensorDeviceClass=types.SimpleNamespace(RUNNING="running"))
    stub("homeassistant.components.button", ButtonEntity=ButtonEntity)
    stub("homeassistant.const", UnitOfEnergy=types.SimpleNamespace(KILO_WATT_HOUR="kWh"),
         UnitOfPower=types.SimpleNamespace(WATT="W"))
    from empreinte.sensor import PowerSensor, RestEnergy, LineCost, SharedEnergy
    from empreinte.binary_sensor import RunningSensor, SharedRunning
    from empreinte.button import RankingReset

    coord = types.SimpleNamespace(
        language="it", groups={"g1": {"name": "Lavatrice personale"}},
        lines={"names": {"sensor.pc": "Mon PC"}},
        shared=types.SimpleNamespace(key=lambda plug, name: plug + name),
    )
    power = PowerSensor(coord, "g1")
    running = RunningSensor(coord, "g1")
    rest = RestEnergy(coord)
    line = LineCost(coord, "sensor.pc", "Mon PC")
    shared = SharedEnergy(coord, "sensor.plug", "Lavatrice personale")
    shared_running = SharedRunning(coord, "sensor.plug", "Lavatrice personale")
    button = RankingReset(coord)
    assert power.name == "Lavatrice personale potenza"
    assert running.name == "Lavatrice personale in funzione"
    assert rest.name == "Non identificato"
    assert line.name == "Mon PC costo"
    assert shared.name == "energia" and shared_running.name == "in funzione"
    assert button.name == "Azzera classifica"
    ids = [(x.entity_id, x._attr_unique_id) for x in (power, running, rest, line, shared, shared_running, button)]
    coord.language = "en"
    assert power.name == "Lavatrice personale power" and rest.name == "Unidentified"
    assert line.name == "Mon PC cost" and shared.name == "energy" and shared_running.name == "running"
    assert ids == [(x.entity_id, x._attr_unique_id) for x in (power, running, rest, line, shared, shared_running, button)]
    coord.groups["g1"]["name"] = "Lave-linge"
    assert power.name == "Washing machine power"
    coord.language = "it"
    assert power.name == "Lavatrice potenza"
    assert ids == [(x.entity_id, x._attr_unique_id) for x in (power, running, rest, line, shared, shared_running, button)]
    assert coord.groups["g1"]["name"] == "Lave-linge"
    builtin = PowerSensor(coord, "g1")
    assert builtin._attr_device_info["name"] == "Lavatrice"
    assert builtin.entity_id == "sensor.empreinte_lave_linge_puissance"


if __name__ == "__main__":
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_"):
            test()
            print("ok", name)
