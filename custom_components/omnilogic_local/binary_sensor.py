from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR, OmniType
from .entity import OmniLogicEntity
from .types.entity_index import EntityDataBackyardT, EntityDataHeaterEquipT
from .utils import get_entities_of_omni_types

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities = []

    # Create a sensor entity indicating if we are in Service Mode
    _LOGGER.debug("Configuring service mode sensor with ID: %s", BACKYARD_SYSTEM_ID)
    entities.append(OmniLogicServiceModeBinarySensorEntity(coordinator=coordinator, context=BACKYARD_SYSTEM_ID))

    # Create sensor entities for each piece of Heater-Equipment
    heater_equipments = get_entities_of_omni_types(coordinator.data, [OmniType.HEATER_EQUIP])
    for system_id, equipment in heater_equipments.items():
        _LOGGER.debug(
            "Configuring heater equipment sensor with ID: %s, Name: %s",
            system_id,
            equipment["metadata"]["name"],
        )
        entities.append(
            OmniLogicHeaterEquipBinarySensorEntity(
                coordinator=coordinator,
                context=system_id,
            )
        )

    async_add_entities(entities)


class OmniLogicServiceModeBinarySensorEntity(OmniLogicEntity[EntityDataBackyardT], BinarySensorEntity):
    _attr_name = "Service Mode"

    @property
    def available(self) -> bool:
        # This is one of the few things we can pull from the telemetry even if we are in service mode
        return True

    @property
    def is_on(self) -> bool:
        return self.data["telemetry"]["@state"] == 2


class OmniLogicHeaterEquipBinarySensorEntity(OmniLogicEntity[EntityDataHeaterEquipT], BinarySensorEntity):
    """Expose a binary state via a sensor based on telemetry data."""

    device_class = BinarySensorDeviceClass.HEAT

    @property
    def name(self) -> str:
        return f'{self.data["metadata"]["name"]} Status'

    @property
    def is_on(self) -> bool:
        return self.data["telemetry"]["@heaterState"] == 1
