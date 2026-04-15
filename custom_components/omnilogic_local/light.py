from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_EFFECT, LightEntity
from homeassistant.components.light.const import ColorMode, LightEntityFeature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.util.color import brightness_to_value, value_to_brightness
from pyomnilogic_local import ColorLogicLight, OmniEquipmentNotInitializedError
from pyomnilogic_local.omnitypes import ColorLogicBrightness, ColorLogicLightType, ColorLogicPowerState

from .coordinator import OmniLogicCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR, UPDATE_DELAY_SECONDS
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
    def available(self) -> bool:
        # The library shows lights as non-ready when they are in certain states (like powering off)
        # but we can still query them for their state, so we report them as available
        return self.equipment._omni.backyard.is_ready

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
            return self.equipment.show.pretty()
        except ValueError:
            return None

    @property
    def effect_list(self) -> list[str] | None:
        if self.equipment.effects is None:
            return None
        return sorted([effect.pretty() for effect in self.equipment.effects])

    @property
    def _extra_state_attributes(self) -> dict[str, int | str]:
        return {
            "omni_state": self.equipment.state.pretty(),
            "omni_speed": self.equipment.speed.pretty(),
            "omni_brightness": self.equipment.brightness,
        }

    # The "Any" below here isn't great, we should create a type for this later
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on.

        Example method how to request data updates.
        """
        _LOGGER.debug("turning on light ID: %s, %s", self.system_id, kwargs)
        if not self.equipment.is_ready:
            raise HomeAssistantError("Light is in state %s and cannot be turned on yet, try again later." % self.equipment.state.pretty())

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

        _LOGGER.debug("Setting light show to %s, speed %s, brightness %s", request_show.pretty(), self.equipment.speed, request_brightness)

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

        async_call_later(self.hass, UPDATE_DELAY_SECONDS, self._schedule_refresh_callback)

    # The "Any" below here isn't great, we should create a type for this later
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off.

        Example method how to request data updates.
        """
        if not self.equipment.is_ready:
            raise HomeAssistantError("Light is in state %s and cannot be turned off yet, try again later." % self.equipment.state.pretty())
        await self.equipment.turn_off()

        async_call_later(self.hass, UPDATE_DELAY_SECONDS, self._schedule_refresh_callback)
