"""The panel settings command preserves unrelated integration options."""
import asyncio
import importlib.util
import os
import sys
import types

sys.path.insert(0, os.path.dirname(__file__))
from ha_stub import C, stub  # noqa: E402

identity = lambda f: f
stub("voluptuous", Required=lambda value: value, Optional=lambda value: value,
     All=lambda *args: args, Any=lambda *args: args, In=lambda value: value,
     Range=lambda **kwargs: kwargs, Coerce=lambda value: value)
websocket = types.SimpleNamespace(websocket_command=lambda schema: identity,
                                  require_admin=identity, async_response=identity)
stub("homeassistant.components", frontend=types.SimpleNamespace(), panel_custom=types.SimpleNamespace(),
     websocket_api=websocket)
stub("homeassistant.components.http", StaticPathConfig=object)
stub("homeassistant.config_entries", ConfigEntry=object)
spec = importlib.util.spec_from_file_location("empreinte.integration", os.path.join(
    os.path.dirname(__file__), "..", "custom_components", "empreinte", "__init__.py"))
module = importlib.util.module_from_spec(spec)
module.__package__ = "empreinte"
spec.loader.exec_module(module)


def test_settings_command():
    entry = types.SimpleNamespace(options={"measured": ["sensor.plug"], "shared_plugs": [{"entity": "sensor.p"}]})
    updates = []
    def update(selected, *, options):
        assert selected is entry
        updates.append(options)
    hass = types.SimpleNamespace(data={"empreinte": {"coord": types.SimpleNamespace(entry=entry)}},
                                 config_entries=types.SimpleNamespace(async_update_entry=update))
    result = []
    conn = types.SimpleNamespace(send_result=lambda *args: result.append(args))
    asyncio.run(module.ws_settings(hass, conn, {"id": 8, "language": "it", "detection_w": 50}))
    assert updates == [{"measured": ["sensor.plug"], "shared_plugs": [{"entity": "sensor.p"}],
                        "language": "it", "detection_w": 50}]
    assert result == [(8,)]


if __name__ == "__main__":
    test_settings_command()
    print("ok test_settings_command")
