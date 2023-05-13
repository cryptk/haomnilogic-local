from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from pyomnilogic_local.types import (
    ColorLogicBrightness,
    ColorLogicShow,
    ColorLogicSpeed,
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN, KEY_COORDINATOR
from .types import OmniLogicEntity
from .utils import get_entities_of_hass_type

_LOGGER = logging.getLogger(__name__)

COLOR_LOGIC_POWER_STATES = {
    0: "off",
    1: "powering_off",
    2: "unknown",
    3: "changing_show",
    4: "fifteen_seconds_of_white",
    5: "unknown",
    6: "on",
    7: "cooldown",
}


# These were shamelessly borrowed from the lutron_caseta integration
def to_omni_level(level):
    """Convert the given Home Assistant light level (0-255) to OmniLogic (0-4)."""
    return int(round((int(level) * 4) / 255))


def to_hass_level(level):
    """Convert the given OmniLogic (0-4) light level to Home Assistant (0-255)."""
    return int((int(level) * 255) // 4)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the light platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_lights = get_entities_of_hass_type(coordinator.data, "light")

    entities = []
    for system_id, light in all_lights.items():
        _LOGGER.debug(
            "Configuring light with ID: %s, Name: %s",
            light["metadata"]["system_id"],
            light["metadata"]["name"],
        )
        entities.append(
            OmniLogicLightEntity(coordinator=coordinator, context=system_id)
        )

    async_add_entities(entities)


class OmniLogicLightEntity(OmniLogicEntity, LightEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_effect_list = list(ColorLogicShow.__members__)
    # _attr_effect = None
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_supported_color_modes = [ColorMode.BRIGHTNESS]
    # _attr_color_mode = None

    def __init__(self, coordinator, context) -> None:
        """Pass coordinator to CoordinatorEntity."""
        light_data = coordinator.data[context]
        super().__init__(
            coordinator,
            context=context,
            name=light_data["metadata"]["name"],
            system_id=light_data["metadata"]["system_id"],
            bow_id=light_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.model = light_data["omni_config"]["Type"]

    @property
    def omni_light_state(self):
        return COLOR_LOGIC_POWER_STATES[int(self.get_telemetry()["@lightState"])]

    @property
    def speed(self):
        return int(self.get_telemetry()["@speed"])

    @property
    def is_on(self) -> bool | None:
        return self.omni_light_state not in [
            "off",
            "powering_off",
            "cooldown",
        ]

    @property
    def brightness(self) -> int | None:
        return to_hass_level(self.get_telemetry()["@brightness"])

    @property
    def effect(self) -> str | None:
        return ColorLogicShow(int(self.get_telemetry()["@currentShow"])).name

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return super().extra_state_attributes | {
            "omnilogic_state": self.omni_light_state,
            "model": self.model,
            "speed": self.speed,
        }

    async def async_turn_on(self, **kwargs):
        """Turn the light on.

        Example method how to request data updates.
        """

        # TODO: We should ensure the light is not in "powering_off" or "cooldown" before turning it on
        _LOGGER.debug("turning on light ID: %s", self.system_id)
        was_off = self.is_on is False

        # If a light go's from off to on, HASS sends kwargs of {'effect':''}, we don't want that
        if kwargs.get(ATTR_EFFECT) == "":
            kwargs.pop(ATTR_EFFECT)

        if kwargs:
            params = {}
            params = {
                "show": ColorLogicShow[kwargs.get(ATTR_EFFECT, self.effect)],
                "speed": ColorLogicSpeed(self.speed),
                "brightness": ColorLogicBrightness(
                    to_omni_level(kwargs.get(ATTR_BRIGHTNESS, self.brightness))
                ),
            }
            await self.coordinator.omni_api.async_set_light_show(
                self.bow_id, self.system_id, **params
            )
        else:
            await self.coordinator.omni_api.async_set_equipment(
                self.bow_id, self.system_id, True
            )

        # Set a few parameters so that we can assume the upcoming state
        updated_data = {}
        if was_off:
            updated_data.update({"@lightState": "4"})
        if kwargs:
            updated_data.update(
                {
                    "@brightness": params["brightness"].value,
                    "@currentShow": ColorLogicShow[
                        kwargs.get(ATTR_EFFECT, self.effect)
                    ].value,
                }
            )
        self.set_telemetry(updated_data)

    async def async_turn_off(self, **kwargs):
        """Turn the light off.

        Example method how to request data updates.
        """

        _LOGGER.debug("turning off light ID: %s", self.system_id)
        was_on = self.is_on is True
        await self.coordinator.omni_api.async_set_equipment(
            self.bow_id, self.system_id, False
        )

        if was_on:
            self.set_telemetry({"@lightState": "1"})
