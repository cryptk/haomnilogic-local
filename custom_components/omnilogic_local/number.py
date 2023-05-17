from __future__ import annotations

from collections.abc import Mapping
import logging
from math import floor
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    KEY_COORDINATOR,
    OMNI_DEVICE_TYPES_PUMP,
    OmniModels,
    OmniTypes,
)
from .types import OmniLogicEntity
from .utils import get_entities_of_omni_types, get_omni_model

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_pumps = get_entities_of_omni_types(coordinator.data, OMNI_DEVICE_TYPES_PUMP)

    entities = []
    for system_id, pump in all_pumps.items():
        pump_type = pump["omni_config"]["Filter-Type"] if pump["metadata"]["omni_type"] == OmniTypes.FILTER else pump["omni_config"]["Type"]

        _LOGGER.debug(
            "Configuring number for pump with ID: %s, Name: %s",
            pump["metadata"]["system_id"],
            pump["metadata"]["name"],
        )
        match pump_type:
            case OmniModels.VARIABLE_SPEED_PUMP:
                entities.append(OmniLogicPumpNumberEntity(coordinator=coordinator, context=system_id))
            case OmniModels.VARIABLE_SPEED_FILTER:
                entities.append(OmniLogicFilterNumberEntity(coordinator=coordinator, context=system_id))

    async_add_entities(entities)


class OmniLogicNumberEntity(OmniLogicEntity, NumberEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context, name=None) -> None:
        """Pass coordinator to CoordinatorEntity."""
        number_data = coordinator.data[context]
        name = number_data["metadata"]["name"] if name is None else name
        super().__init__(
            coordinator,
            context=context,
            name=name,
            system_id=context,
            bow_id=number_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.model = get_omni_model(number_data)
        self.omni_type = number_data["metadata"]["omni_type"]
        self._attr_native_unit_of_measurement = self.coordinator.msp_config["MSPConfig"]["System"].get("Msp-Vsp-Speed-Format")


class OmniLogicPumpNumberEntity(OmniLogicNumberEntity):
    """An entity representing a number platform for an OmniLogic Pump."""

    def __init__(self, coordinator, context) -> None:
        number_data = coordinator.data[context]
        super().__init__(coordinator, context, name=f'{number_data["metadata"]["name"]} Speed')
        self.telem_key_speed = "@pumpSpeed"
        self.telem_key_state = "@pumpState"

    @property
    def native_max_value(self) -> float:
        if self._attr_native_unit_of_measurement == "RPM":
            return int(self.get_config(self.system_id)["Max-Pump-RPM"])
        return int(self.get_config(self.system_id)["Max-Pump-Speed"])

    @property
    def native_min_value(self) -> float:
        if self._attr_native_unit_of_measurement == "RPM":
            return int(self.get_config(self.system_id)["Min-Pump-RPM"])
        return int(self.get_config(self.system_id)["Min-Pump-Speed"])

    @property
    def native_value(self) -> float:
        # Even though the omnilogic stores whether you want RPM or Percent, it always returns
        # the filter speed as a percent value.  We convert it here to what your preference is.
        if self._attr_native_unit_of_measurement == "RPM":
            return floor(self.native_max_value / 100 * int(self.get_telemetry(self.system_id)[self.telem_key_speed]))
        return int(self.get_telemetry(self.system_id)[self.telem_key_speed])

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return super().extra_state_attributes | {
            "max_rpm": self.get_config(self.system_id)["Max-Pump-RPM"],
            "min_rpm": self.get_config(self.system_id)["Min-Pump-RPM"],
            "max_percent": self.get_config(self.system_id)["Max-Pump-Speed"],
            "min_percent": self.get_config(self.system_id)["Min-Pump-RPM"],
            "current_rpm": floor(self.native_max_value / 100 * int(self.get_telemetry(self.system_id)[self.telem_key_speed])),
            "current_percent": self.get_telemetry(self.system_id)[self.telem_key_speed],
        }

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self._attr_native_unit_of_measurement == "RPM":
            new_speed_pct = round(value / self.native_max_value * 100)
        else:
            new_speed_pct = int(value)

        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, new_speed_pct)

        self.set_telemetry(
            {self.telem_key_state: "1", self.telem_key_speed: new_speed_pct},
            system_id=self.system_id,
        )


class OmniLogicFilterNumberEntity(OmniLogicPumpNumberEntity):
    """An OmniLogicFilterNumberEntity is a special case of an OmniLogicPumpNumberEntity."""

    def __init__(self, coordinator, context) -> None:
        super().__init__(coordinator, context)
        self.telem_key_speed = "@filterSpeed"
        self.telem_key_state = "@filterState"
