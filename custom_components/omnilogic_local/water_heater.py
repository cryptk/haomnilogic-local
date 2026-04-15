from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.water_heater import WaterHeaterEntity, WaterHeaterEntityFeature
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, STATE_ON, UnitOfTemperature
from pyomnilogic_local import Heater

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the water heater platform."""
    coordinator: OmniLogicCoordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities: list[WaterHeaterEntity] = []

    for _, _, heater in coordinator.omni.all_heaters.items():
        entities.append(OmniLogicWaterHeaterEntity(coordinator=coordinator, equipment=heater))

    async_add_entities(entities)


class OmniLogicWaterHeaterEntity(OmniLogicEntity[Heater], WaterHeaterEntity):
    """Water heater entity for heater control."""

    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE | WaterHeaterEntityFeature.ON_OFF
    )
    _attr_operation_list = [STATE_ON, STATE_OFF]
    _attr_name = "Heater"

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Heater) -> None:
        """Initialize the water heater entity."""
        super().__init__(coordinator, equipment)

    @property
    def temperature_unit(self) -> str:
        # Heaters always return their values in Fahrenheit, no matter what units the system is set to
        # https://github.com/cryptk/haomnilogic-local/issues/96
        return UnitOfTemperature.FAHRENHEIT

    @property
    def min_temp(self) -> float:
        return self.equipment.min_temp

    @property
    def max_temp(self) -> float:
        return self.equipment.max_temp

    @property
    def target_temperature(self) -> float | None:
        return self.equipment.current_set_point

    @property
    def current_temperature(self) -> float | None:
        # Get the body of water to retrieve the current water temperature
        if self.equipment.bow_id is None:
            return None
        bow = self.coordinator.omni.all_bows.get(self.equipment.bow_id)
        if bow is None:
            return None
        current_temp = bow.water_temp
        return current_temp if current_temp != -1 else None

    @property
    def current_operation(self) -> str:
        return str(STATE_ON) if self.equipment.is_on else str(STATE_OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        await self.equipment.set_temperature(int(kwargs[ATTR_TEMPERATURE]))
        self.schedule_delayed_update()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set operation mode."""
        match operation_mode:
            case "on":
                await self.equipment.turn_on()
            case "off":
                await self.equipment.turn_off()
        self.schedule_delayed_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_set_operation_mode("on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_operation_mode("off")

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        extra_state_attributes: dict[str, Any] = {
            "omni_solar_set_point": self.equipment.solar_set_point,
            "omni_why_on": self.equipment.why_on,
        }
        for _, system_id, heater_equip in self.equipment.heater_equipment.items():
            name = heater_equip.name or "unknown"
            prefix = f"omni_heater_equip_{name}_"
            extra_state_attributes |= {
                f"{prefix}_enabled": heater_equip.enabled,
                f"{prefix}_system_id": system_id,
                f"{prefix}_bow_id": heater_equip.bow_id,
                f"{prefix}_state": str(heater_equip.state),
                f"{prefix}_current_temp": heater_equip.current_temp,
            }
        return extra_state_attributes
