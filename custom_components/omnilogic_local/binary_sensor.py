from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR
from .types import OmniLogicEntity
from .utils import get_entities_of_omni_types

_LOGGER = logging.getLogger(__name__)

# There is a SENSOR_FLOW as well, but I don't have one to test with
SENSOR_TYPES_TEMPERATURE = ["SENSOR_AIR_TEMP", "SENSOR_WATER_TEMP", "SENSOR_SOLAR_TEMP"]


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities = []

    # Create a sensor entity indicating if we are in Service Mode
    _LOGGER.debug("Configuring service mode sensor with ID: %s", BACKYARD_SYSTEM_ID)
    entities.append(OmniLogicServiceModeBinarySensorEntity(coordinator=coordinator, context=BACKYARD_SYSTEM_ID))

    # Create sensor entities for each piece of Heater-Equipment
    heater_equipments = get_entities_of_omni_types(coordinator.data, ["Heater-Equipment"])
    for system_id, equipment in heater_equipments.items():
        _LOGGER.debug(
            "Configuring heater equipment sensor with ID: %s, Name: %s",
            system_id,
            equipment["metadata"]["name"],
        )
        entities.append(
            OmniLogicTelemetryBinarySensorEntity(
                coordinator=coordinator,
                context=system_id,
                name=f'{equipment["metadata"]["name"]} Status',
                telem_key="@heaterState",
                device_class=BinarySensorDeviceClass.HEAT,
            )
        )

    async_add_entities(entities)


class OmniLogicBinarySensorEntity(OmniLogicEntity, BinarySensorEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context, name: str | None = None) -> None:
        """Pass coordinator to CoordinatorEntity."""
        sensor_data = coordinator.data[context]
        super().__init__(
            coordinator,
            context,
            name=name if name is not None else sensor_data["metadata"]["name"],
            system_id=sensor_data["metadata"]["system_id"],
            bow_id=sensor_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.omni_type = sensor_data["metadata"]["omni_type"]
        self.model = sensor_data["omni_config"].get("Type")


class OmniLogicServiceModeBinarySensorEntity(OmniLogicBinarySensorEntity):
    def __init__(self, coordinator, context) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context, name="Service Mode")

    @property
    def available(self) -> bool:
        # This is one of the few things we can pull from the telemetry even if we are in service mode
        return True

    @property
    def is_on(self) -> bool | None:
        return self.get_telemetry()["@state"] == 2


class OmniLogicTelemetryBinarySensorEntity(OmniLogicBinarySensorEntity):
    """Expose a binary state via a sensor based on telemetry data."""

    def __init__(
        self,
        coordinator,
        context,
        name: str,
        telem_key: str,
        true_value=1,
        device_class: BinarySensorDeviceClass = None,
    ) -> None:
        super().__init__(
            coordinator,
            context,
            name=name,
        )
        self.telem_key = telem_key
        self.true_value = true_value
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        return self.get_telemetry()[self.telem_key] == self.true_value
