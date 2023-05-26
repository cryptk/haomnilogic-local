from __future__ import annotations

import logging
from math import floor
from typing import TYPE_CHECKING, Any, TypeVar

from pyomnilogic_local.types import FilterState, PumpState

from homeassistant.components.number import NumberEntity

from .const import DOMAIN, KEY_COORDINATOR, OMNI_TYPES_PUMP, OmniModel
from .entity import OmniLogicEntity
from .types.entity_index import EntityIndexFilter, EntityIndexPump
from .utils import get_entities_of_omni_types

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_pumps = get_entities_of_omni_types(coordinator.data, OMNI_TYPES_PUMP)

    entities = []
    for system_id, pump in all_pumps.items():

        _LOGGER.debug(
            "Configuring number for pump with ID: %s, Name: %s",
            pump.msp_config.system_id,
            pump.msp_config.name,
        )
        match pump.msp_config.type:
            case OmniModel.VARIABLE_SPEED_PUMP:
                entities.append(OmniLogicPumpNumberEntity(coordinator=coordinator, context=system_id))
            case OmniModel.VARIABLE_SPEED_FILTER:
                entities.append(OmniLogicFilterNumberEntity(coordinator=coordinator, context=system_id))

    async_add_entities(entities)


T = TypeVar("T", EntityIndexPump, EntityIndexFilter)


class OmniLogicNumberEntity(OmniLogicEntity[T], NumberEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_icon: str = "mdi:gauge"

    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context)

    @property
    def name(self) -> Any:
        return f"{super().name} Speed"

    @property
    def max_rpm(self) -> int:
        return self.data.msp_config.max_rpm

    @property
    def min_rpm(self) -> int:
        return self.data.msp_config.min_rpm

    @property
    def max_pct(self) -> int:
        return self.data.msp_config.max_percent

    @property
    def min_pct(self) -> int:
        return self.data.msp_config.min_percent

    @property
    def current_rpm(self) -> int:
        return floor(int(self.native_max_value) / 100 * self.data.telemetry.speed)

    @property
    def current_pct(self) -> int:
        return self.data.telemetry.speed

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.get_system_config().vsp_speed_format

    @property
    def native_max_value(self) -> float:
        if self.native_unit_of_measurement == "RPM":
            return self.max_rpm
        return self.max_pct

    @property
    def native_min_value(self) -> float:
        if self.native_unit_of_measurement == "RPM":
            return self.min_rpm
        return self.min_pct

    @property
    def native_value(self) -> int:
        # Even though the omnilogic stores whether you want RPM or Percent, it always returns
        # the filter speed as a percent value.  We convert it here to what your preference is.
        if self.native_unit_of_measurement == "RPM":
            return self.current_rpm
        return self.current_pct

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        return super().extra_state_attributes | {
            "max_rpm": self.data.msp_config.max_rpm,
            "min_rpm": self.data.msp_config.min_rpm,
            "max_percent": self.data.msp_config.max_percent,
            "min_percent": self.data.msp_config.min_percent,
            "current_rpm": self.current_rpm,
            "current_percent": self.current_pct,
        }

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        raise NotImplementedError


class OmniLogicPumpNumberEntity(OmniLogicNumberEntity[EntityIndexPump]):
    """An entity representing a number platform for an OmniLogic Pump."""

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self.native_unit_of_measurement == "RPM":
            new_speed_pct = round(value / self.native_max_value * 100)
        else:
            new_speed_pct = int(value)

        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, new_speed_pct)

        self.set_telemetry({"state": PumpState.ON, "speed": new_speed_pct})


class OmniLogicFilterNumberEntity(OmniLogicNumberEntity[EntityIndexFilter]):
    """An OmniLogicFilterNumberEntity is a special case of an OmniLogicPumpNumberEntity."""

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self.native_unit_of_measurement == "RPM":
            new_speed_pct = round(value / self.native_max_value * 100)
        else:
            new_speed_pct = int(value)

        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, new_speed_pct)

        self.set_telemetry({"state": FilterState.ON, "speed": new_speed_pct})
