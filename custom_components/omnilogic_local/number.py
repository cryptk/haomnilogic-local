from __future__ import annotations

import logging
from math import floor
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from homeassistant.components.number import NumberEntity

from .const import DOMAIN, KEY_COORDINATOR, OMNI_TYPES_PUMP, OmniModel
from .entity import OmniLogicEntity
from .types.entity_index import EntityDataFilterT, EntityDataPumpT
from .utils import get_entities_of_omni_types, get_omni_model

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
        pump_type = get_omni_model(pump)
        # pump_type = pump["config"]["Filter_Type"] if pump["metadata"]["omni_type"] == OmniTypes.FILTER else pump["config"]["Type"]

        _LOGGER.debug(
            "Configuring number for pump with ID: %s, Name: %s",
            pump["metadata"]["system_id"],
            pump["metadata"]["name"],
        )
        match pump_type:
            case OmniModel.VARIABLE_SPEED_PUMP:
                entities.append(OmniLogicPumpNumberEntity(coordinator=coordinator, context=system_id))
            case OmniModel.VARIABLE_SPEED_FILTER:
                entities.append(OmniLogicFilterNumberEntity(coordinator=coordinator, context=system_id))

    async_add_entities(entities)


T = TypeVar("T", EntityDataPumpT, EntityDataFilterT)


class OmniLogicNumberEntity(OmniLogicEntity[T], NumberEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_key_speed: Literal["@pumpSpeed", "@filterSpeed"]
    telem_key_state: Literal["@pumpState", "@filterState"]

    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        """Pass coordinator to CoordinatorEntity."""
        # number_data = coordinator.data[context]
        # name = number_data["metadata"]["name"] if name is None else name
        super().__init__(coordinator, context)

    @property
    def max_rpm(self) -> int:
        return self.data["config"]["Max_Pump_RPM"]

    @property
    def min_rpm(self) -> int:
        return self.data["config"]["Min_Pump_RPM"]

    @property
    def max_pct(self) -> int:
        return self.data["config"]["Max_Pump_Speed"]

    @property
    def min_pct(self) -> int:
        return self.data["config"]["Min_Pump_Speed"]

    @property
    def current_rpm(self) -> int:
        raise NotImplementedError

    @property
    def current_pct(self) -> int:
        raise NotImplementedError

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.get_system_config()["Msp_Vsp_Speed_Format"]

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
            "max_rpm": self.data["config"]["Max_Pump_RPM"],
            "min_rpm": self.data["config"]["Min_Pump_RPM"],
            "max_percent": self.data["config"]["Max_Pump_Speed"],
            "min_percent": self.data["config"]["Min_Pump_RPM"],
            "current_rpm": self.current_rpm,
            "current_percent": self.current_pct,
        }

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self.native_unit_of_measurement == "RPM":
            new_speed_pct = round(value / self.native_max_value * 100)
        else:
            new_speed_pct = int(value)

        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, new_speed_pct)

        self.set_telemetry({self.telem_key_state: 1, self.telem_key_speed: new_speed_pct})


class OmniLogicPumpNumberEntity(OmniLogicNumberEntity[EntityDataPumpT]):
    """An entity representing a number platform for an OmniLogic Pump."""

    telem_key_speed: Literal["@pumpSpeed"] = "@pumpSpeed"
    telem_key_state: Literal["@pumpState"] = "@pumpState"

    @property
    def name(self) -> Any:
        return f"{super().name} Speed"

    @property
    def current_rpm(self) -> int:
        return floor(int(self.native_max_value) / 100 * self.data["telemetry"]["@pumpSpeed"])

    @property
    def current_pct(self) -> int:
        return self.data["telemetry"]["@lastSpeed"]


class OmniLogicFilterNumberEntity(OmniLogicNumberEntity[EntityDataFilterT]):
    """An OmniLogicFilterNumberEntity is a special case of an OmniLogicPumpNumberEntity."""

    telem_key_speed: Literal["@filterSpeed"] = "@filterSpeed"
    telem_key_state: Literal["@filterState"] = "@filterState"

    @property
    def name(self) -> Any:
        return f"{super().name} Speed"

    @property
    def current_rpm(self) -> int:
        return floor(self.native_max_value / 100 * float(self.data["telemetry"]["@filterSpeed"]))

    @property
    def current_pct(self) -> int:
        return self.data["telemetry"]["@filterSpeed"]
