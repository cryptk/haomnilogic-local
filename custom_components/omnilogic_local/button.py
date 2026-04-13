from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.event import async_call_later
from pyomnilogic_local import Backyard, Filter, Pump
from pyomnilogic_local.omnitypes import FilterSpeedPresets, FilterType, PumpSpeedPresets, PumpType

from .const import DOMAIN, KEY_COORDINATOR, UPDATE_DELAY_SECONDS
from .entity import OmniLogicEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""
    coordinator: OmniLogicCoordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities: list[ButtonEntity] = []

    for _, _, pump in coordinator.omni.all_pumps.items():
        if pump.equip_type == PumpType.VARIABLE_SPEED:
            for pumpSpeed in PumpSpeedPresets:
                entities.append(OmniLogicPumpButtonEntity(coordinator=coordinator, equipment=pump, speed=pumpSpeed))

    for _, _, filt in coordinator.omni.all_filters.items():
        if filt.equip_type == FilterType.VARIABLE_SPEED:
            for filterSpeed in FilterSpeedPresets:
                entities.append(OmniLogicFilterButtonEntity(coordinator=coordinator, equipment=filt, speed=filterSpeed))

    entities.append(OmniLogicIdleButtonEntity(coordinator=coordinator, equipment=coordinator.omni.backyard))

    async_add_entities(entities)


PumpTypeT = TypeVar("PumpTypeT", bound=Pump | Filter)
SpeedPresetT = TypeVar("SpeedPresetT", bound=PumpSpeedPresets | FilterSpeedPresets)


class OmniLogicSpeedPresetButtonEntity(OmniLogicEntity[PumpTypeT], ButtonEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: PumpTypeT, speed: FilterSpeedPresets | PumpSpeedPresets) -> None:
        super().__init__(coordinator, equipment)
        self.speed = speed

    @property
    def icon(self) -> str:
        match self.speed:
            case PumpSpeedPresets.LOW | FilterSpeedPresets.LOW:
                return "mdi:speedometer-slow"
            case PumpSpeedPresets.MEDIUM | FilterSpeedPresets.MEDIUM:
                return "mdi:speedometer-medium"
            case PumpSpeedPresets.HIGH | FilterSpeedPresets.HIGH:
                return "mdi:speedometer"

    @property
    def name(self) -> str:
        return f"{self.equipment.name} {self.speed.name.capitalize()} Speed"

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        match self.speed:
            case PumpSpeedPresets.LOW | FilterSpeedPresets.LOW:
                return {"speed": self.equipment.low_speed}
            case PumpSpeedPresets.MEDIUM | FilterSpeedPresets.MEDIUM:
                return {"speed": self.equipment.medium_speed}
            case PumpSpeedPresets.HIGH | FilterSpeedPresets.HIGH:
                return {"speed": self.equipment.high_speed}


class OmniLogicPumpButtonEntity(OmniLogicSpeedPresetButtonEntity[Pump]):
    speed: PumpSpeedPresets

    async def async_press(self) -> None:
        await self.equipment.run_preset_speed(self.speed)
        async_call_later(self.hass, UPDATE_DELAY_SECONDS, self._schedule_refresh_callback)


class OmniLogicFilterButtonEntity(OmniLogicSpeedPresetButtonEntity[Filter]):
    speed: FilterSpeedPresets

    async def async_press(self) -> None:
        await self.equipment.run_preset_speed(self.speed)
        async_call_later(self.hass, UPDATE_DELAY_SECONDS, self._schedule_refresh_callback)


class OmniLogicIdleButtonEntity(OmniLogicEntity[Backyard], ButtonEntity):
    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Backyard) -> None:
        super().__init__(coordinator, equipment)

    @property
    def name(self) -> str:
        return "Restore Idle"

    async def async_press(self) -> None:
        await self.coordinator.omni._api.async_restore_idle_state()
        async_call_later(self.hass, UPDATE_DELAY_SECONDS, self._schedule_refresh_callback)
