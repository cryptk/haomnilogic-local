from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR
from .types import OmniLogicEntity
from .utils import get_entities_of_hass_type

_LOGGER = logging.getLogger(__name__)

# There is a SENSOR_FLOW as well, but I don't have one to test with
SENSOR_TYPES_TEMPERATURE = ["SENSOR_AIR_TEMP", "SENSOR_WATER_TEMP", "SENSOR_SOLAR_TEMP"]


def find_sensor_heater_systemid(data: dict, sensor_system_id: int) -> int:
    heaters = get_entities_of_hass_type(data, "water_heater")
    for system_id, heater in heaters.items():
        if not "Sensor-System-Id" in heater["omni_config"]:
            continue
        if int(heater["omni_config"].get("Sensor-System-Id")) != sensor_system_id:
            continue
        return system_id


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    # Create a sensor entity for all temperature sensors
    all_sensors = get_entities_of_hass_type(coordinator.data, "sensor")
    entities = []
    for system_id, sensor in all_sensors.items():
        if sensor["omni_config"]["Type"] in SENSOR_TYPES_TEMPERATURE:
            _LOGGER.debug(
                "Configuring temperature sensor with ID: %s, Name: %s",
                sensor["metadata"]["system_id"],
                sensor["metadata"]["name"],
            )
            entities.append(
                OmniLogicTemperatureSensorEntity(
                    coordinator=coordinator, context=system_id
                )
            )

    async_add_entities(entities)


class OmniLogicSensorEntity(OmniLogicEntity, SensorEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, context, name: str = None) -> None:
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


class OmniLogicTemperatureSensorEntity(OmniLogicSensorEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context, name: str = None) -> None:
        """Pass coordinator to CoordinatorEntity."""
        sensor_data = coordinator.data[context]
        super().__init__(coordinator, context)
        self.units = self.get_config()["Units"]
        self.heater_system_id = find_sensor_heater_systemid(
            coordinator.data, sensor_data["metadata"]["system_id"]
        )
        self._attr_device_class = SensorDeviceClass.TEMPERATURE

    @property
    def native_unit_of_measurement(self) -> str | None:
        match self.units:
            case "UNITS_FAHRENHEIT":
                return UnitOfTemperature.FAHRENHEIT
            case "UNITS_CELCIUS":
                return UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        telem_temp: int = None
        match self.model:
            case "SENSOR_AIR_TEMP":
                telem_temp = self.get_telemetry(BACKYARD_SYSTEM_ID)["@airTemp"]
            case "SENSOR_WATER_TEMP":
                telem_temp = self.get_telemetry(self.bow_id)["@waterTemp"]
            case "SENSOR_SOLAR_TEMP":
                telem_temp = self.get_telemetry(self.heater_system_id)["@temp"]
        # Sometimes the Omni returns junk values for the temperatures, for example, when it first comes out of service mode
        return telem_temp if int(telem_temp) not in [-1, 255, 65535] else None
