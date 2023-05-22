from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

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
from homeassistant.exceptions import HomeAssistantError

from .types.entity_index import EntityDataColorLogicLightT

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from .coordinator import OmniLogicCoordinator

from .const import DOMAIN, KEY_COORDINATOR, OmniModel
from .entity import OmniLogicEntity
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
def to_omni_level(level: int) -> int:
    """Convert the given Home Assistant light level (0-255) to OmniLogic (0-4)."""
    return int(round((level * 4) / 255))


def to_hass_level(level: int) -> int:
    """Convert the given OmniLogic (0-4) light level to Home Assistant (0-255)."""
    return int((level * 255) // 4)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
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
        entities.append(OmniLogicLightEntity(coordinator=coordinator, context=system_id))

    async_add_entities(entities)


class OmniLogicLightEntity(OmniLogicEntity[EntityDataColorLogicLightT], LightEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_effect_list = list(ColorLogicShow.__members__)
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_supported_color_modes = [ColorMode.BRIGHTNESS]

    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=context)
        try:
            self.model = OmniModel(self.data["config"]["Type"])
        except ValueError:
            _LOGGER.error(
                "Your light is not currently supported, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
            )

    @property
    def omni_light_state(self) -> str:
        return COLOR_LOGIC_POWER_STATES[self.data["telemetry"]["@lightState"]]

    @property
    def speed(self) -> int:
        return self.data["telemetry"]["@speed"]

    @property
    def is_on(self) -> bool | None:
        return self.omni_light_state not in [
            "off",
            "powering_off",
            "cooldown",
        ]

    @property
    def brightness(self) -> int | None:
        return to_hass_level(self.data["telemetry"]["@brightness"])

    @property
    def effect(self) -> str | None:
        try:
            return ColorLogicShow(self.data["telemetry"]["@currentShow"]).name  # type: ignore[no-any-return]
        except ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        return super().extra_state_attributes | {
            "omnilogic_state": self.omni_light_state,
            "speed": self.speed,
        }

    # The "Any" below here isn't great, we should create a type for this later
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on.

        Example method how to request data updates.
        """

        # If the light is in either of these states, it will refuse to turn on, so we raise an error to the UI to let the user know
        if self.omni_light_state in ["powering_off", "cooldown"]:
            raise HomeAssistantError("Light must finish powering off before it can power back on.")
        _LOGGER.debug("turning on light ID: %s", self.system_id)
        was_off = self.is_on is False

        # If a light go's from off to on, HASS sends kwargs of {'effect':''}, we don't want that
        if kwargs.get(ATTR_EFFECT) == "":
            kwargs.pop(ATTR_EFFECT)

        if kwargs:
            # params = {}
            params = {
                "show": ColorLogicShow[kwargs.get(ATTR_EFFECT, self.effect)],
                "speed": ColorLogicSpeed(self.speed),
                "brightness": ColorLogicBrightness(to_omni_level(kwargs.get(ATTR_BRIGHTNESS, self.brightness))),
            }
            await self.coordinator.omni_api.async_set_light_show(self.bow_id, self.system_id, **params)
        else:
            await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, True)

        # Set a few parameters so that we can assume the upcoming state
        updated_data = {}
        if was_off:
            updated_data.update({"@lightState": 4})
        if kwargs:
            updated_data.update(
                {
                    "@brightness": params["brightness"].value,
                    "@currentShow": ColorLogicShow[kwargs.get(ATTR_EFFECT, self.effect)].value,
                }
            )
        self.set_telemetry(updated_data)

    # The "Any" below here isn't great, we should create a type for this later
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off.

        Example method how to request data updates.
        """

        _LOGGER.debug("turning off light ID: %s", self.system_id)
        was_on = self.is_on is True
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, False)

        if was_on:
            self.set_telemetry({"@lightState": 1})
