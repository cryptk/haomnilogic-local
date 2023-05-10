from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, STATE_ON, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, KEY_COORDINATOR
from .types import OmniLogicEntity
from .utils import get_entities_of_type

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the water heater platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_heaters = get_entities_of_type(coordinator.data, "water_heater")

    virtual_heater = {
        system_id: data
        for system_id, data in all_heaters.items()
        if data["metadata"]["omni_type"] == "Heater"
    }
    heater_equipment_ids = [
        system_id
        for system_id, data in all_heaters.items()
        if data["metadata"]["omni_type"] == "Heater-Equipment"
    ]
    # _LOGGER.debug("Virtual Heater found")
    # _LOGGER.debug(virtual_heater)

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

    def __init__(
        self, coordinator, context: int, heater_equipment_ids: list[int]
    ) -> None:
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
        self._attr_temperature_unit = (
            UnitOfTemperature.CELSIUS
            if self.coordinator.msp_config["MSPConfig"]["System"]["Units"] == "Metric"
            else UnitOfTemperature.FAHRENHEIT
        )
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE
            | WaterHeaterEntityFeature.OPERATION_MODE
        )
        self._attr_min_temp = int(
            water_heater_data["omni_config"]["Min-Settable-Water-Temp"]
        )
        self._attr_max_temp = int(
            water_heater_data["omni_config"]["Max-Settable-Water-Temp"]
        )
        self._attr_target_temperature = int(
            water_heater_data["omni_config"]["Current-Set-Point"]
        )
        current_temp = int(
            coordinator.data[water_heater_data["metadata"]["bow_id"]]["omni_telemetry"][
                "@waterTemp"
            ]
        )
        self._attr_current_temperature = current_temp if current_temp != -1 else None
        self._attr_operation_list = [STATE_ON, STATE_OFF]
        self._attr_current_operation = (
            STATE_ON
            if int(water_heater_data["omni_telemetry"]["@enable"]) == 1
            else STATE_OFF
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        water_heater_data = self.coordinator.data[self.context]
        self._attr_temperature_unit = (
            UnitOfTemperature.CELSIUS
            if self.coordinator.msp_config["MSPConfig"]["System"]["Units"] == "Metric"
            else UnitOfTemperature.FAHRENHEIT
        )
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE
            | WaterHeaterEntityFeature.OPERATION_MODE
        )
        self._attr_min_temp = int(
            water_heater_data["omni_config"]["Min-Settable-Water-Temp"]
        )
        self._attr_max_temp = int(
            water_heater_data["omni_config"]["Max-Settable-Water-Temp"]
        )
        self._attr_target_temperature = int(
            water_heater_data["omni_config"]["Current-Set-Point"]
        )
        current_temp = int(
            self.coordinator.data[water_heater_data["metadata"]["bow_id"]][
                "omni_telemetry"
            ]["@waterTemp"]
        )
        self._attr_current_temperature = current_temp if current_temp != -1 else None
        self._attr_operation_list = [STATE_ON, STATE_OFF]
        self._attr_current_operation = (
            STATE_ON
            if int(water_heater_data["omni_telemetry"]["@enable"]) == 1
            else STATE_OFF
        )
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any):
        await self.coordinator.omni_api.async_set_heater(
            self.bow_id,
            self.system_id,
            int(kwargs[ATTR_TEMPERATURE]),
            unit=self._attr_temperature_unit,
        )
        self._attr_target_temperature = int(kwargs[ATTR_TEMPERATURE])
        self.push_assumed_state()

    async def async_set_operation_mode(self, operation_mode):
        await self.coordinator.omni_api.async_set_heater_enable(
            self.bow_id, self.system_id, operation_mode != STATE_OFF
        )
        self._attr_current_operation = operation_mode
        self.push_assumed_state()

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        extra_state_attributes = super().extra_state_attributes
        for system_id in self.heater_equipment_ids:
            heater_equipment = self.coordinator.data[system_id]
            prefix = f"omni_heater_{heater_equipment['metadata']['name'].lower()}"
            extra_state_attributes = extra_state_attributes | {
                f"{prefix}_enabled": heater_equipment["omni_config"]["Enabled"],
                f"{prefix}_system_id": heater_equipment["metadata"]["system_id"],
                f"{prefix}_bow_id": heater_equipment["metadata"]["bow_id"],
                f"{prefix}_supports_cooling": heater_equipment["omni_config"][
                    "SupportsCooling"
                ],
                f"{prefix}_state": STATE_ON
                if int(heater_equipment["omni_telemetry"]["@heaterState"]) == 1
                else STATE_OFF,
                f"{prefix}_sensor_temp": heater_equipment["omni_telemetry"]["@temp"],
            }
        return extra_state_attributes
