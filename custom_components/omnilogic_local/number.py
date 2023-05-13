from __future__ import annotations

from collections.abc import Mapping
import logging
from math import floor
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, KEY_COORDINATOR, OmniModels
from .types import OmniLogicEntity
from .utils import get_entities_of_omni_type, get_omni_model

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_filters = get_entities_of_omni_type(coordinator.data, "Filter")

    entities = []
    for system_id, filter_pump in all_filters.items():
        if filter_pump["omni_config"]["Filter-Type"] == "FMT_VARIABLE_SPEED_PUMP":
            _LOGGER.debug(
                "Configuring number for filter with ID: %s, Name: %s",
                filter_pump["metadata"]["system_id"],
                filter_pump["metadata"]["name"],
            )
            entities.append(
                OmniLogicNumberEntity(coordinator=coordinator, context=system_id)
            )

    async_add_entities(entities)


def get_name(base_name: str, omni_type: str) -> str:
    match omni_type:
        case "Filter":
            return f"{base_name} Speed"
        case _:
            return base_name


def get_system_id(system_id: str, omni_type: str) -> str:
    match omni_type:
        case "Filter":
            return f"{system_id}_number_speed"
        case _:
            return f"{system_id}_number"


class OmniLogicNumberEntity(OmniLogicEntity, NumberEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context) -> None:
        """Pass coordinator to CoordinatorEntity."""
        number_data = coordinator.data[context]
        name = get_name(
            number_data["metadata"]["name"], number_data["metadata"]["omni_type"]
        )
        system_id = get_system_id(
            number_data["metadata"]["system_id"], number_data["metadata"]["omni_type"]
        )
        super().__init__(
            coordinator,
            context=context,
            name=name,
            system_id=system_id,
            bow_id=number_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.data_system_id = number_data["metadata"]["system_id"]
        self.model = get_omni_model(number_data)
        self.omni_type = number_data["metadata"]["omni_type"]
        self._attr_native_unit_of_measurement = self.coordinator.msp_config[
            "MSPConfig"
        ]["System"].get("Msp-Vsp-Speed-Format")

    @property
    def native_max_value(self) -> float:
        if self.model == OmniModels.VARIABLE_SPEED_PUMP:
            if self._attr_native_unit_of_measurement == "RPM":
                return int(self.get_config(self.data_system_id)["Max-Pump-RPM"])
            return int(self.get_config(self.data_system_id)["Max-Pump-Speed"])
        return None

    @property
    def native_min_value(self) -> float:
        if self.model == OmniModels.VARIABLE_SPEED_PUMP:
            if self._attr_native_unit_of_measurement == "RPM":
                return int(self.get_config(self.data_system_id)["Min-Pump-RPM"])
            return int(self.get_config(self.data_system_id)["Min-Pump-Speed"])
        return None

    @property
    def native_value(self) -> float:
        if self.model == OmniModels.VARIABLE_SPEED_PUMP:
            # Even though the omnilogic stores whether you want RPM or Percent, it always returns
            # the filter speed as a percent value.  We convert it here to what your preference is.
            if self._attr_native_unit_of_measurement == "RPM":
                return floor(
                    self.native_max_value
                    / 100
                    * int(self.get_telemetry(self.data_system_id)["@filterSpeed"])
                )
            return int(self.get_telemetry(self.data_system_id)["@filterSpeed"])
        return None

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        extra_state_attributes = {}
        match self.model:
            case OmniModels.VARIABLE_SPEED_PUMP:
                extra_state_attributes = {
                    "max_rpm": self.get_config(self.data_system_id)["Max-Pump-RPM"],
                    "min_rpm": self.get_config(self.data_system_id)["Min-Pump-RPM"],
                    "max_percent": self.get_config(self.data_system_id)[
                        "Max-Pump-Speed"
                    ],
                    "min_percent": self.get_config(self.data_system_id)["Min-Pump-RPM"],
                    "current_rpm": floor(
                        self.native_max_value
                        / 100
                        * int(self.get_telemetry(self.data_system_id)["@filterSpeed"])
                    ),
                    "current_percent": self.get_telemetry(self.data_system_id)[
                        "@filterSpeed"
                    ],
                }
        return super().extra_state_attributes | extra_state_attributes

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self.model == OmniModels.VARIABLE_SPEED_PUMP:
            if self._attr_native_unit_of_measurement == "RPM":
                new_speed_pct = round(value / self.native_max_value * 100)
            else:
                new_speed_pct = int(value)
        await self.coordinator.omni_api.async_set_equipment(
            self.bow_id, self.data_system_id, new_speed_pct
        )

        self.set_telemetry(
            {"@filterState": "1", "@filterSpeed": new_speed_pct},
            system_id=self.data_system_id,
        )
