"""« En marche » pour chaque appareil reconnu."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .const import DOMAIN
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util

from .entity import ApplianceEntity, slug
from .text import display_appliance, display_text


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN]["coord"]
    coord.add_entities["binary_sensor"] = async_add_entities
    coord.ensure_entities()


class RunningSensor(ApplianceEntity, BinarySensorEntity):
    _label = "en marche"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coord, gid):
        super().__init__(coord, gid, "binary_sensor")

    @property
    def is_on(self):
        return self.coord.live_for(self.gid) is not None


class SharedRunning(BinarySensorEntity):
    """En marche, pour un appareil d'une prise partagée (dès qu'on sait lequel des appareils tourne)."""
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "en marche"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coord, plug, name):
        self.coord, self.plug, self.app = coord, plug, name
        self._attr_unique_id = f"{DOMAIN}_sh_{slug(plug)}_{slug(name)}_marche"
        self.entity_id = f"binary_sensor.empreinte_prise_{slug(name)}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, "sh:" + coord.shared.key(plug, name))}, name=display_appliance(coord, name),
                                            manufacturer="Empreinte", model="Prise partagée")

    @property
    def name(self):
        return display_text(self.coord, self._attr_name)

    @property
    def is_on(self):
        return self.coord.shared.running(self.plug, self.app) is not None

    @property
    def extra_state_attributes(self):
        o = self.coord.shared.running(self.plug, self.app)
        if not o:
            return {}
        kwh, price = (o.get("wh") or 0) / 1000, self.coord.ranking.get("prix")
        loc = dt_util.as_local(dt_util.utc_from_timestamp(o["start"]))
        return {"certitude": round(o["conf"] * 100), "a_confirmer": not o.get("sure"), "debut": f"{loc.hour} h {loc.minute:02d}",
                "kwh": round(kwh, 2), "eur": round(kwh * price, 2) if price else None}
