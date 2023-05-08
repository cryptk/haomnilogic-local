from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pyomnilogic_local.omnilogicTypes import (ColorLogicBrightness,
                                              ColorLogicShow, ColorLogicSpeed)

from homeassistant.components.light import (ATTR_BRIGHTNESS, ATTR_EFFECT,
                                            ColorMode, LightEntity,
                                            LightEntityFeature)
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, KEY_COORDINATOR
from .types import OmniLogicEntity
from .utils import get_entities_of_type

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

    all_lights = get_entities_of_type(coordinator.data, "light")

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

    _attr_effect_list = None
    _attr_effect = None
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_supported_color_modes = [ColorMode.BRIGHTNESS]
    _attr_color_mode = None
    _attr_brightness = None

    def __init__(self, coordinator, context) -> None:
        """Pass coordinator to CoordinatorEntity."""
        light_data = coordinator.data[context]
        # _LOGGER.debug(light_data)
        super().__init__(
            coordinator,
            context=context,
            name=light_data["metadata"]["name"],
            system_id=light_data["metadata"]["system_id"],
            bow_id=light_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.model = light_data["omni_config"]["Type"]
        self.omni_light_state = COLOR_LOGIC_POWER_STATES[
            int(light_data["omni_telemetry"]["@lightState"])
        ]
        self.speed = int(light_data["omni_telemetry"]["@speed"])

        self._attr_is_on = self.omni_light_state not in [
            "off",
            "powering_off",
            "cooldown",
        ]
        self._attr_brightness = to_hass_level(
            light_data["omni_telemetry"]["@brightness"]
        )

        self._attr_effect_list = list(ColorLogicShow.__members__)
        self._attr_effect = ColorLogicShow(
            int(light_data["omni_telemetry"]["@currentShow"])
        ).name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        light_data = self.coordinator.data[self.context]
        self.omni_light_state = COLOR_LOGIC_POWER_STATES[
            int(light_data["omni_telemetry"]["@lightState"])
        ]
        self.speed = int(light_data["omni_telemetry"]["@speed"])
        self._attr_is_on = self.omni_light_state not in [
            "off",
            "powering_off",
            "cooldown",
        ]
        self._attr_effect = ColorLogicShow(
            int(light_data["omni_telemetry"]["@currentShow"])
        ).name
        self._attr_brightness = to_hass_level(
            light_data["omni_telemetry"]["@brightness"]
        )
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return {
            "omnilogic_state": self.omni_light_state,
            "model": self.model,
            "speed": self.speed,
        }

    async def async_turn_on(self, **kwargs):
        """Turn the light on.

        Example method how to request data updates.
        """

        _LOGGER.debug("Turning on the light: %s", kwargs)
        was_off = self.is_on is False
        params = {}
        params = {
            "show": ColorLogicShow[kwargs.get(ATTR_EFFECT, self._attr_effect)],
            "speed": ColorLogicSpeed(self.speed),
            "brightness": ColorLogicBrightness(
                to_omni_level(kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness))
            ),
        }
        await self.coordinator.omni_api.asyncSetLightShow(
            self.bow_id, self.system_id, **params
        )

        # Set a few parameters so that we can assume the upcoming state
        if was_off:
            self.omni_light_state = "fifteen_seconds_of_white"
            self._attr_is_on = True
            self._attr_brightness = to_hass_level(params["brightness"].value)
            self._attr_effect = params["show"]
            # TODO: This function calls a protected member _schedule_refresh, we should figure
            # out how to use self.coordinator.async_set_updated_data() instead
            self.push_assumed_state()

    async def async_turn_off(self, **kwargs):
        """Turn the light off.

        Example method how to request data updates.
        """

        _LOGGER.debug("Turning off the light")
        await self.coordinator.omni_api.asyncSetEquipment(
            self.bow_id, self.system_id, False
        )

        # Set a few parameters so that we can assume the upcoming state
        self.omni_light_state = "powering_off"
        self._attr_is_on = False
        # TODO: This function calls a protected member _schedule_refresh, we should figure
        # out how to use self.coordinator.async_set_updated_data() instead
        self.push_assumed_state()
