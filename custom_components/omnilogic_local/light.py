from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pyomnilogic_local.types import (
    ColorLogicBrightness,
    ColorLogicLightType,
    ColorLogicPowerState,
    ColorLogicShow,
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.exceptions import HomeAssistantError

from .types.entity_index import EntityIndexColorLogicLight

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .utils import get_entities_of_hass_type

_LOGGER = logging.getLogger(__name__)


# These were shamelessly borrowed from the lutron_caseta integration
def to_omni_level(level: int) -> int:
    """Convert the given Home Assistant light level (0-255) to OmniLogic (0-4)."""
    return int(round((level * 4) / 255))


def to_hass_level(level: ColorLogicBrightness) -> int:
    """Convert the given OmniLogic (0-4) light level to Home Assistant (0-255)."""
    return int(int(level.value * 255) // 4)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the light platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_lights = get_entities_of_hass_type(coordinator.data, "light")

    entities = []
    for system_id, light in all_lights.items():
        _LOGGER.debug(
            "Configuring light with ID: %s, Name: %s",
            light.msp_config.system_id,
            light.msp_config.name,
        )
        match light.msp_config.type:
            case ColorLogicLightType.UCL | ColorLogicLightType.TWO_FIVE:
                entities.append(OmniLogicLightEntity(coordinator=coordinator, context=system_id))
            case _:
                _LOGGER.warning(
                    "Your system has an unsupported light, this light may not function properly, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                )

    async_add_entities(entities)


class OmniLogicLightEntity(OmniLogicEntity[EntityIndexColorLogicLight], LightEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_effect_list = list(ColorLogicShow.__members__)
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    @property
    def is_on(self) -> bool | None:
        return self.data.telemetry.state not in [
            ColorLogicPowerState.OFF,
            ColorLogicPowerState.POWERING_OFF,
            ColorLogicPowerState.COOLDOWN,
        ]

    @property
    def brightness(self) -> int | None:
        return to_hass_level(self.data.telemetry.brightness)

    @property
    def effect(self) -> str | None:
        try:
            return self.data.telemetry.show.name
        except ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        return super().extra_state_attributes | {
            "omnilogic_state": self.data.telemetry.state.pretty(),
            "speed": self.data.telemetry.speed.pretty(),
        }

    # The "Any" below here isn't great, we should create a type for this later
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on.

        Example method how to request data updates.
        """

        # If the light is in either of these states, it will refuse to turn on, so we raise an error to the UI to let the user know
        if self.data.telemetry.state in [ColorLogicPowerState.POWERING_OFF, ColorLogicPowerState.COOLDOWN]:
            raise HomeAssistantError("Light must finish powering off before it can power back on.")
        _LOGGER.debug("turning on light ID: %s", self.system_id)
        was_off = self.is_on is False

        # If a light go's from off to on, HASS sends kwargs of {'effect':''}, we don't want that
        if kwargs.get(ATTR_EFFECT) == "":
            kwargs.pop(ATTR_EFFECT)

        if kwargs:
            params = {
                "show": ColorLogicShow[kwargs.get(ATTR_EFFECT, self.effect)],
                "speed": self.data.telemetry.speed,
                "brightness": ColorLogicBrightness(to_omni_level(kwargs.get(ATTR_BRIGHTNESS, self.brightness))),
            }
            await self.coordinator.omni_api.async_set_light_show(self.bow_id, self.system_id, **params)
        else:
            await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, True)

        # Set a few parameters so that we can assume the upcoming state
        updated_data = {}
        if was_off:
            updated_data.update({"state": ColorLogicPowerState.FIFTEEN_SECONDS_WHITE})
        if kwargs:
            updated_data.update(
                {
                    "brightness": params["brightness"],
                    "show": params["show"],
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
            self.set_telemetry({"state": ColorLogicPowerState.POWERING_OFF})
