from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from pyomnilogic_local import CSAD, Chlorinator
from pyomnilogic_local.omnitypes import ChlorinatorOperatingMode

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
