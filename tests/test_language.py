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


if __name__ == "__main__":
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_"):
            test()
            print("ok", name)
