from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, cast

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, STATE_ON, UnitOfTemperature

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .types.entity_index import EntityDataHeaterEquipT, EntityDataHeaterT
from .types.telemetry import TelemetryBodyOfWaterT
from .utils import get_entities_of_hass_type

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the water heater platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_heaters = get_entities_of_hass_type(coordinator.data, "water_heater")

    virtual_heater = {system_id: data for system_id, data in all_heaters.items() if data["metadata"]["omni_type"] == "Heater"}
    heater_equipment_ids = [system_id for system_id, data in all_heaters.items() if data["metadata"]["omni_type"] == "Heater_Equipment"]

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


class OmniLogicWaterHeaterEntity(OmniLogicEntity[EntityDataHeaterT], WaterHeaterEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_supported_features = WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE
    _attr_operation_list = [STATE_ON, STATE_OFF]

    def __init__(self, coordinator: OmniLogicCoordinator, context: int, heater_equipment_ids: list[int]) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(
            coordinator,
            context=context,
        )
        self.heater_equipment_ids = heater_equipment_ids

    @property
    def temperature_unit(self) -> str:
        return (
            str(UnitOfTemperature.CELSIUS)
            if self.coordinator.msp_config["MSPConfig"]["System"]["Units"] == "Metric"
            else str(UnitOfTemperature.FAHRENHEIT)
        )

    @property
    def min_temp(self) -> float:
        return self.data["config"]["Min_Settable_Water_Temp"]

    @property
    def max_temp(self) -> float:
        return self.data["config"]["Max_Settable_Water_Temp"]

    @property
    def target_temperature(self) -> float | None:
        return self.data["config"]["Current_Set_Point"]

    @property
    def current_temperature(self) -> float | None:
        current_temp = cast(TelemetryBodyOfWaterT, self.get_telemetry_by_systemid(self.bow_id))["@waterTemp"]
        return current_temp if current_temp != -1 else None

    @property
    def current_operation(self) -> str:
        return str(STATE_ON) if self.data["telemetry"]["@enable"] == 1 else str(STATE_OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        await self.coordinator.omni_api.async_set_heater(
            self.bow_id,
            self.system_id,
            int(kwargs[ATTR_TEMPERATURE]),
            unit=self.temperature_unit,
        )
        self.set_config({"Current_Set_Point": kwargs[ATTR_TEMPERATURE]})

    async def async_set_operation_mode(self, operation_mode: Literal["on", "off"]) -> None:
        match operation_mode:
            case "on":
                await self.coordinator.omni_api.async_set_heater_enable(self.bow_id, self.system_id, True)
                self.set_telemetry({"@enable": 1})
            case "off":
                await self.coordinator.omni_api.async_set_heater_enable(self.bow_id, self.system_id, False)
                self.set_telemetry({"@enable": 0})

    @property
    def extra_state_attributes(self) -> dict[str, str | int]:
        extra_state_attributes = super().extra_state_attributes
        for system_id in self.heater_equipment_ids:
            heater_equipment = cast(EntityDataHeaterEquipT, self.coordinator.data[system_id])
            prefix = f"omni_heater_{heater_equipment['metadata']['name'].lower()}"
            extra_state_attributes = extra_state_attributes | {
                f"{prefix}_enabled": heater_equipment["config"]["Enabled"],
                f"{prefix}_system_id": system_id,
                f"{prefix}_bow_id": heater_equipment["metadata"]["bow_id"],
                f"{prefix}_supports_cooling": heater_equipment["config"].get("SupportsCooling", "no"),
                f"{prefix}_state": STATE_ON if heater_equipment["telemetry"]["@heaterState"] == 1 else STATE_OFF,
                f"{prefix}_sensor_temp": heater_equipment["telemetry"]["@temp"],
            }
        return extra_state_attributes
