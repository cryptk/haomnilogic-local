from __future__ import annotations

import logging
from math import floor
from typing import TYPE_CHECKING, Any, TypeVar

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from pyomnilogic_local import Chlorinator, Filter, Heater, Pump
from pyomnilogic_local.omnitypes import (
    ChlorinatorDispenserType,
    ChlorinatorOperatingMode,
    FilterType,
    HeaterType,
    PumpType,
)

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the number platform."""
    coordinator: OmniLogicCoordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities: list[NumberEntity] = []

    # Add variable speed pump entities
    for _, _, pump in coordinator.omni.all_pumps.items():
        if pump.equip_type == PumpType.VARIABLE_SPEED:
            entities.append(OmniLogicPumpNumberEntity(coordinator=coordinator, equipment=pump))

    # Add variable speed filter entities
    for _, _, filt in coordinator.omni.all_filters.items():
        if filt.equip_type == FilterType.VARIABLE_SPEED:
            entities.append(OmniLogicFilterNumberEntity(coordinator=coordinator, equipment=filt))

    # Add solar set point entity for heaters with solar
    for _, _, heater in coordinator.omni.all_heaters.items():
        # Check if this heater has any solar equipment
        has_solar = any(equip.heater_type == HeaterType.SOLAR for equip in heater.heater_equipment.values())
        if has_solar and heater.solar_set_point is not None and heater.solar_set_point > 0:
            entities.append(OmniLogicSolarSetPointNumberEntity(coordinator=coordinator, equipment=heater))

    # Add chlorinator timed percent entities
    for _, _, chlorinator in coordinator.omni.all_chlorinators.items():
        match chlorinator.dispenser_type:
            case ChlorinatorDispenserType.SALT:
                match chlorinator.operating_mode:
                    case ChlorinatorOperatingMode.TIMED:
                        entities.append(OmniLogicChlorinatorTimedPercentNumberEntity(coordinator=coordinator, equipment=chlorinator))
                    case ChlorinatorOperatingMode.ORP_AUTO | ChlorinatorOperatingMode.ORP_TIMED_RW:
                        _LOGGER.warning(
                            "Chlorinator ORP control is not supported yet, "
                            "please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                        )
            case ChlorinatorDispenserType.LIQUID:
                # Working in issue #116 on this support
                pass
            case ChlorinatorDispenserType.TABLET:
                pass
            case _:
                _LOGGER.warning(
                    "Your system has an unsupported chlorinator, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                )

    async_add_entities(entities)


PumpTypeT = TypeVar("PumpTypeT", bound=Pump | Filter)


class OmniLogicVSPNumberEntity(OmniLogicEntity[PumpTypeT], NumberEntity):
    """Number entity for variable speed pump or filter speed control."""

    _attr_icon: str = "mdi:gauge"

    @property
    def name(self) -> Any:
        return f"{super().name} Speed"

    @property
    def max_rpm(self) -> int:
        return self.equipment.max_rpm

    @property
    def min_rpm(self) -> int:
        return self.equipment.min_rpm

    @property
    def max_pct(self) -> int:
        return self.equipment.max_percent

    @property
    def min_pct(self) -> int:
        return self.equipment.min_percent

    @property
    def current_rpm(self) -> int:
        return floor(self.equipment.max_rpm / 100 * self.equipment.speed)

    @property
    def current_pct(self) -> int:
        return self.equipment.speed

    @property
    def native_unit_of_measurement(self) -> str | None:
        return PERCENTAGE

    @property
    def native_max_value(self) -> float:
        return self.max_pct

    @property
    def native_min_value(self) -> float:
        return self.min_pct

    @property
    def native_value(self) -> int:
        return self.current_pct

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return {
            "omni_max_rpm": self.max_rpm,
            "omni_min_rpm": self.min_rpm,
            "omni_max_percent": self.max_pct,
            "omni_min_percent": self.min_pct,
            "omni_current_rpm": self.current_rpm,
            "omni_current_percent": self.current_pct,
        }

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.equipment.set_speed(int(value))
        self.schedule_delayed_update()


class OmniLogicPumpNumberEntity(OmniLogicVSPNumberEntity[Pump]):
    """Number entity for variable speed pump speed control."""


class OmniLogicFilterNumberEntity(OmniLogicVSPNumberEntity[Filter]):
    """Number entity for variable speed filter speed control."""


class OmniLogicSolarSetPointNumberEntity(OmniLogicEntity[Heater], NumberEntity):
    """Number entity for solar heater set point control."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_name = "Solar Set Point"
    _attr_mode = NumberMode.BOX

    @property
    def native_max_value(self) -> float:
        return self.equipment.max_temp

    @property
    def native_min_value(self) -> float:
        return self.equipment.min_temp

    @property
    def native_value(self) -> float | None:
        return self.equipment.solar_set_point

    @property
    def native_unit_of_measurement(self) -> str | None:
        # The Omnilogic operates in Fahrenheit, so that's our native unit
        # Home Assistant will handle unit conversion based on user preferences
        return str(UnitOfTemperature.FAHRENHEIT)

    async def async_set_native_value(self, value: float) -> None:
        await self.equipment.set_solar_temperature(int(value))
        self.schedule_delayed_update()


class OmniLogicChlorinatorTimedPercentNumberEntity(OmniLogicEntity[Chlorinator], NumberEntity):
    """Number entity for chlorinator timed percent control."""

    _attr_name = "Chlorinator Timed Percent"
    _attr_native_max_value = 100
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float | None:
        return self.equipment.timed_percent_telemetry

    async def async_set_native_value(self, value: float) -> None:
        await self.equipment.set_timed_percent(int(value))
        self.schedule_delayed_update()
