from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricPotential, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import StateType

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR
from .types import OmniLogicEntity
from .utils import get_entities_of_type

_LOGGER = logging.getLogger(__name__)

# There is a SENSOR_FLOW as well, but I don't have one to test with
SUPPORTED_SENSOR_TYPES = ["SENSOR_AIR_TEMP", "SENSOR_WATER_TEMP", "SENSOR_SOLAR_TEMP"]


def find_sensor_heater_systemid(data: dict, sensor_system_id: int) -> int:
    heaters = get_entities_of_type(data, "water_heater")
    # _LOGGER.debug(heaters)
    for system_id, heater in heaters.items():
        if not "Sensor-System-Id" in heater["omni_config"]:
            continue
        if int(heater["omni_config"].get("Sensor-System-Id")) != sensor_system_id:
            continue
        return system_id


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_sensors = get_entities_of_type(coordinator.data, "sensor")

    entities = []
    for system_id, sensor in all_sensors.items():
        _LOGGER.debug(
            "Configuring sensor with ID: %s, Name: %s",
            sensor["metadata"]["system_id"],
            sensor["metadata"]["name"],
        )
        entities.append(
            OmniLogicSensorEntity(coordinator=coordinator, context=system_id)
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

    def __init__(self, coordinator, context) -> None:
        """Pass coordinator to CoordinatorEntity."""
        sensor_data = coordinator.data[context]
        # _LOGGER.debug("sensor_data: %s", sensor_data)
        super().__init__(
            coordinator,
            context=context,
            name=sensor_data["metadata"]["name"],
            system_id=sensor_data["metadata"]["system_id"],
            bow_id=sensor_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.omni_type = sensor_data["metadata"]["omni_type"]
        self.model = sensor_data["omni_config"]["Type"]
        self.units = sensor_data["omni_config"]["Units"]
        self.heater_system_id = find_sensor_heater_systemid(
            coordinator.data, sensor_data["metadata"]["system_id"]
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # sensor_data = self.coordinator.data[self.context]
        self.async_write_ha_state()

    @property
    def device_class(self) -> SensorDeviceClass | None:
        match self.model:
            case "SENSOR_AIR_TEMP" | "SENSOR_WATER_TEMP" | "SENSOR_SOLAR_TEMP":
                return SensorDeviceClass.TEMPERATURE
            case "SENSOR_FLOW":
                # There does not appear to be an available device class for flow rate
                # https://developers.home-assistant.io/docs/core/entity/sensor#available-device-classes
                return None
            case _:
                return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        match self.units:
            case "UNITS_FAHRENHEIT":
                return UnitOfTemperature.FAHRENHEIT
            case "UNITS_CELCIUS":
                return UnitOfTemperature.CELSIUS
            case "UNITS_PPM":
                return "ppm"
            case "UNITS_GRAMS_PER_LITER":
                return "g/L"
            case "UNITS_MILLIVOLTS":
                return UnitOfElectricPotential.MILLIVOLT
            case "UNITS_NO_UNITS":
                return None

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        match self.model:
            case "SENSOR_AIR_TEMP":
                return self.coordinator.data[BACKYARD_SYSTEM_ID]["omni_telemetry"][
                    "@airTemp"
                ]
            case "SENSOR_WATER_TEMP":
                telem_temp = self.coordinator.data[self.bow_id]["omni_telemetry"][
                    "@waterTemp"
                ]
                return telem_temp if int(telem_temp) != -1 else None
            case "SENSOR_SOLAR_TEMP":
                return self.coordinator.data[self.heater_system_id]["omni_telemetry"][
                    "@temp"
                ]
