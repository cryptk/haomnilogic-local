from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar

from homeassistant.components.button import ButtonEntity
from pyomnilogic_local import Backyard, Filter, Pump
from pyomnilogic_local.omnitypes import FilterSpeedPresets, FilterType, PumpSpeedPresets, PumpType

from .const import DOMAIN, KEY_COORDINATOR
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
    """Button entity for triggering a pump or filter speed preset."""

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
            case _:
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
            case _:
                return {"speed": None}


class OmniLogicPumpButtonEntity(OmniLogicSpeedPresetButtonEntity[Pump]):
    """Button entity for triggering a pump speed preset."""

    speed: PumpSpeedPresets

    async def async_press(self) -> None:
        await self.equipment.run_preset_speed(self.speed)
        self.schedule_delayed_update()


class OmniLogicFilterButtonEntity(OmniLogicSpeedPresetButtonEntity[Filter]):
    """Button entity for triggering a filter speed preset."""

    speed: FilterSpeedPresets

    async def async_press(self) -> None:
        await self.equipment.run_preset_speed(self.speed)
        self.schedule_delayed_update()


class OmniLogicIdleButtonEntity(OmniLogicEntity[Backyard], ButtonEntity):
    """Button entity for restoring the system to idle state."""

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Backyard) -> None:
        super().__init__(coordinator, equipment)

    @property
    def name(self) -> str:
        return "Restore Idle"

    async def async_press(self) -> None:
        await self.coordinator.omni._api.async_restore_idle_state()
        self.schedule_delayed_update()
