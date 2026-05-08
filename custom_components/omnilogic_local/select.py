from __future__ import annotations

import logging
from math import floor
from typing import TYPE_CHECKING, Any

from homeassistant.components.select import SelectEntity
from pyomnilogic_local import CSAD, Chlorinator, Filter, Pump
from pyomnilogic_local.omnitypes import (
    ChlorinatorOperatingMode,
    FilterSpeedPresets,
    FilterState,
    FilterType,
    PumpSpeedPresets,
    PumpState,
    PumpType,
)

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the number platform."""
    coordinator: OmniLogicCoordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities: list[SelectEntity] = []

    # If we have a Chlorinator ...
    for _, _, chlorinator in coordinator.omni.all_chlorinators.items():
        # ... and we have a CSAD on the same BoW ...
        if chlorinator.bow_id is not None and coordinator.omni.backyard.bow[chlorinator.bow_id].csad is not None:
            # ... then we can support the ORP set point
            csad = coordinator.omni.backyard.bow[chlorinator.bow_id].csad
            if csad is not None:
                entities.append(OmniLogicChlorinatorOpModeSelectEntity(coordinator=coordinator, equipment=chlorinator, csad=csad))

    for _, _, pump in coordinator.omni.all_pumps.items():
        if pump.equip_type == PumpType.DUAL_SPEED:
            entities.append(OmniLogicPumpSpeedSelectEntity(coordinator=coordinator, equipment=pump))

    for _, _, filt in coordinator.omni.all_filters.items():
        if filt.equip_type == FilterType.DUAL_SPEED:
            entities.append(OmniLogicFilterSpeedSelectEntity(coordinator=coordinator, equipment=filt))

    async_add_entities(entities)


class OmniLogicChlorinatorOpModeSelectEntity(OmniLogicEntity[Chlorinator], SelectEntity):
    """Number entity for CSAD pH control."""

    _attr_name = "Chlorinator Operating Mode"
    _attr_options = [str(mode) for mode in (ChlorinatorOperatingMode.TIMED, ChlorinatorOperatingMode.ORP_AUTO)]

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Chlorinator, csad: CSAD):
        super().__init__(coordinator, equipment)
        self._csad = csad

    @property
    def current_option(self) -> str:
        return str(self.equipment.operating_mode)

    async def async_select_option(self, option: str) -> None:
        case = ChlorinatorOperatingMode.from_str(option)
        match case:
            case ChlorinatorOperatingMode.TIMED:
                await self.equipment.set_op_mode(ChlorinatorOperatingMode.TIMED)
            case ChlorinatorOperatingMode.ORP_AUTO:
                await self.equipment.set_op_mode(ChlorinatorOperatingMode.ORP_AUTO)


type PumpTypes = Pump | Filter


class OmniLogicDualSpeedSelectEntity[PT: PumpTypes](OmniLogicEntity[PT], SelectEntity):
    """Number entity for variable speed pump or filter speed control."""

    _attr_icon: str = "mdi:gauge"

    @property
    def name(self) -> str:
        return f"{super().name} Speed"

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return {
            "omni_max_rpm": self.equipment.max_rpm,
            "omni_min_rpm": self.equipment.min_rpm,
            "omni_max_percent": self.equipment.max_percent,
            "omni_min_percent": self.equipment.min_percent,
            "omni_current_rpm": floor(self.equipment.max_rpm / 100 * self.equipment.speed),
            "omni_current_percent": self.equipment.speed,
        }


class OmniLogicPumpSpeedSelectEntity(OmniLogicDualSpeedSelectEntity[Pump]):
    """Number entity for variable speed pump speed control."""

    _attr_options = [str(mode) for mode in (PumpState.OFF, PumpSpeedPresets.LOW, PumpSpeedPresets.HIGH)]

    @property
    def current_option(self) -> str:
        match self.equipment.speed:
            case 0:
                return str(PumpState.OFF)
            case 50:
                return str(PumpSpeedPresets.LOW)
            case 100:
                return str(PumpSpeedPresets.HIGH)
            case _:
                return "Unknown"

    async def async_select_option(self, option: str) -> None:
        """Update the current value."""
        if option == "Off":
            await self.equipment.turn_off()
        else:
            requested_speed = PumpSpeedPresets.from_str(option)
            await self.equipment.set_dual_speed(requested_speed)
        self.coordinator.do_next_refresh_after()


class OmniLogicFilterSpeedSelectEntity(OmniLogicDualSpeedSelectEntity[Filter]):
    """Number entity for variable speed filter speed control."""

    _attr_options = [str(mode) for mode in (FilterState.OFF, FilterSpeedPresets.LOW, FilterSpeedPresets.HIGH)]

    @property
    def current_option(self) -> str:
        match self.equipment.speed:
            case 0:
                return str(FilterState.OFF)
            case 50:
                return str(FilterSpeedPresets.LOW)
            case 100:
                return str(FilterSpeedPresets.HIGH)
            case _:
                return "Unknown"

    async def async_select_option(self, option: str) -> None:
        """Update the current value."""
        if option == "Off":
            await self.equipment.turn_off()
        else:
            requested_speed = FilterSpeedPresets.from_str(option)
            await self.equipment.set_dual_speed(requested_speed)
        self.coordinator.do_next_refresh_after()
