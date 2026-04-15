from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_EFFECT, LightEntity
from homeassistant.components.light.const import ColorMode, LightEntityFeature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.color import brightness_to_value, value_to_brightness
from pyomnilogic_local import ColorLogicLight, OmniEquipmentNotInitializedError
from pyomnilogic_local.omnitypes import ColorLogicBrightness, ColorLogicLightType, ColorLogicPowerState

from .coordinator import OmniLogicCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity

_LOGGER = logging.getLogger(__name__)

BRIGHTNESS_SCALE = (0, 4)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the light platform."""
    coordinator: OmniLogicCoordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities: list[LightEntity] = []

    all_lights = coordinator.omni.all_lights
    for _, _, light in all_lights.items():
        entities.append(OmniLogicLightEntity(coordinator=coordinator, equipment=light))

    async_add_entities(entities)


class OmniLogicLightEntity(OmniLogicEntity[ColorLogicLight], LightEntity):
    """Light entity for ColorLogic lights."""

    _attr_supported_features = LightEntityFeature.EFFECT

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        match self.equipment.equip_type:
            case ColorLogicLightType.SAM | ColorLogicLightType.TWO_FIVE | ColorLogicLightType.UCL:
                return {ColorMode.BRIGHTNESS}
            case _:
                return {ColorMode.ONOFF}

    @property
    def color_mode(self) -> ColorMode | None:
        match self.equipment.equip_type:
            case ColorLogicLightType.SAM | ColorLogicLightType.TWO_FIVE | ColorLogicLightType.UCL:
                return ColorMode.BRIGHTNESS
            case _:
                return ColorMode.ONOFF

    @property
    def is_on(self) -> bool | None:
        return self.equipment.state not in [
            ColorLogicPowerState.OFF,
            ColorLogicPowerState.POWERING_OFF,
            ColorLogicPowerState.COOLDOWN,
        ]

    @property
    def brightness(self) -> int:
        return value_to_brightness(BRIGHTNESS_SCALE, self.equipment.brightness.value)

    @property
    def effect(self) -> str | None:
        try:
            return str(self.equipment.show)
        except ValueError:
            return None

    @property
    def effect_list(self) -> list[str] | None:
        if self.equipment.effects is None:
            return None
        return sorted([str(effect) for effect in self.equipment.effects])

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return {
            "omni_state": str(self.equipment.state),
            "omni_speed": str(self.equipment.speed),
            "omni_brightness": self.equipment.brightness,
        }

    # The "Any" below here isn't great, we should create a type for this later
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on.

        Example method how to request data updates.
        """
        _LOGGER.debug("turning on light ID: %s, %s", self.system_id, kwargs)
        if not self.equipment.is_ready:
            raise HomeAssistantError("Light is in state %s and cannot be turned on yet, try again later." % str(self.equipment.state))

        # Map requested effect to omni show
        requested_effect = kwargs.get(ATTR_EFFECT, None)
        if requested_effect is not None and self.equipment.effects is not None:
            # We need to reformat the show name to match the enum keys
            request_show = self.equipment.effects[requested_effect.upper().replace(" ", "_")]
        else:
            request_show = self.equipment.show
        _LOGGER.debug("Requested effect: %s, resolved to show: %s", requested_effect, request_show)

        # Map requested brightness to omni brightness
        requested_brightness = kwargs.get(ATTR_BRIGHTNESS, None)
        if requested_brightness is not None:
            request_brightness = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, requested_brightness))
        else:
            request_brightness = self.equipment.brightness
        _LOGGER.debug(
            "Requested brightness: %s, resolved to omni brightness: %s - %s",
            requested_brightness,
            request_brightness,
            ColorLogicBrightness(request_brightness),
        )

        _LOGGER.debug("Setting light show to %s, speed %s, brightness %s", str(request_show), self.equipment.speed, request_brightness)

        try:
            await self.equipment.set_show(
                show=request_show,
                # The Home Assistant API has no concept of speed for a light, so we just use the current speed setting
                # There is a number entity to control it though
                speed=self.equipment.speed,
                brightness=ColorLogicBrightness(request_brightness),
            )
        except OmniEquipmentNotInitializedError as exc:
            raise HomeAssistantError("Light is not yet initialized, try again later.") from exc
        self.schedule_delayed_update()

    # The "Any" below here isn't great, we should create a type for this later
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off.

        Example method how to request data updates.
        """
        if not self.equipment.is_ready:
            raise HomeAssistantError("Light is in state %s and cannot be turned off yet, try again later." % str(self.equipment.state))
        await self.equipment.turn_off()
        self.schedule_delayed_update()
