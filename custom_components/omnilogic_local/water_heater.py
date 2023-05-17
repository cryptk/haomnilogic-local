from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, STATE_ON, UnitOfTemperature
from homeassistant.core import HomeAssistant

from .const import DOMAIN, KEY_COORDINATOR
from .types import OmniLogicEntity
from .utils import get_entities_of_hass_type

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the water heater platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_heaters = get_entities_of_hass_type(coordinator.data, "water_heater")

    virtual_heater = {system_id: data for system_id, data in all_heaters.items() if data["metadata"]["omni_type"] == "Heater"}
    heater_equipment_ids = [system_id for system_id, data in all_heaters.items() if data["metadata"]["omni_type"] == "Heater-Equipment"]

    entities = []
    for system_id, switch in virtual_heater.items():
        _LOGGER.debug(
            "Configuring water heater with ID: %s, Name: %s",
            switch["metadata"]["system_id"],
            switch["metadata"]["name"],
        )
        entities.append(
            OmniLogicWaterHeaterEntity(
                coordinator=coordinator,
                context=system_id,
                heater_equipment_ids=heater_equipment_ids,
            )
        )

    async_add_entities(entities)


class OmniLogicWaterHeaterEntity(OmniLogicEntity, WaterHeaterEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context: int, heater_equipment_ids: list[int]) -> None:
        """Pass coordinator to CoordinatorEntity."""
        water_heater_data = coordinator.data[context]
        super().__init__(
            coordinator,
            context=context,
            name=water_heater_data["metadata"]["name"],
            system_id=water_heater_data["metadata"]["system_id"],
            bow_id=water_heater_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.omni_type = water_heater_data["metadata"]["omni_type"]
        self.heater_equipment_ids = heater_equipment_ids
        self._attr_supported_features = WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE

        self._attr_operation_list = [STATE_ON, STATE_OFF]
        self._attr_current_operation = STATE_ON if water_heater_data["omni_telemetry"]["@enable"] == 1 else STATE_OFF

    @property
    def temperature_unit(self) -> str:
        return (
            UnitOfTemperature.CELSIUS
            if self.coordinator.msp_config["MSPConfig"]["System"]["Units"] == "Metric"
            else UnitOfTemperature.FAHRENHEIT
        )

    @property
    def min_temp(self) -> float:
        return self.get_config()["Min_Settable_Water_Temp"]

    @property
    def max_temp(self) -> float:
        return self.get_config()["Max_Settable_Water_Temp"]

    @property
    def target_temperature(self) -> float | None:
        return self.get_config()["Current_Set_Point"]

    @property
    def current_temperature(self) -> float | None:
        current_temp = self.get_telemetry(self.bow_id)["@waterTemp"]
        return current_temp if current_temp != -1 else None

    @property
    def current_operation(self) -> str | None:
        return STATE_ON if self.get_telemetry()["@enable"] == 1 else STATE_OFF

    async def async_set_temperature(self, **kwargs: Any):
        await self.coordinator.omni_api.async_set_heater(
            self.bow_id,
            self.system_id,
            int(kwargs[ATTR_TEMPERATURE]),
            unit=self.temperature_unit,
        )
        self.set_config({"Current_Set_Point": kwargs[ATTR_TEMPERATURE]})

    async def async_set_operation_mode(self, operation_mode):
        match operation_mode:
            case "on":
                await self.coordinator.omni_api.async_set_heater_enable(self.bow_id, self.system_id, True)
                self.set_telemetry({"@enable": 1})
            case "off":
                await self.coordinator.omni_api.async_set_heater_enable(self.bow_id, self.system_id, False)
                self.set_telemetry({"@enable": 0})

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        extra_state_attributes = super().extra_state_attributes
        for system_id in self.heater_equipment_ids:
            heater_equipment = self.coordinator.data[system_id]
            prefix = f"omni_heater_{heater_equipment['metadata']['name'].lower()}"
            extra_state_attributes = extra_state_attributes | {
                f"{prefix}_enabled": self.get_config(system_id)["Enabled"],
                f"{prefix}_system_id": system_id,
                f"{prefix}_bow_id": heater_equipment["metadata"]["bow_id"],
                f"{prefix}_supports_cooling": self.get_config(system_id).get("SupportsCooling", "no"),
                f"{prefix}_state": STATE_ON if self.get_telemetry(system_id)["@heaterState"] == 1 else STATE_OFF,
                f"{prefix}_sensor_temp": self.get_telemetry(system_id)["@temp"],
            }
        return extra_state_attributes
