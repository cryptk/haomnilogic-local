from __future__ import annotations

import logging
from math import floor
from typing import TYPE_CHECKING, Any, TypeVar, cast

from pyomnilogic_local.omnitypes import (
    BodyOfWaterType,
    ChlorinatorDispenserType,
    ChlorinatorOperatingMode,
    FilterState,
    FilterType,
    HeaterType,
    OmniType,
    PumpState,
    PumpType,
)

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfTemperature

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .types.entity_index import EntityIndexBodyOfWater, EntityIndexChlorinator, EntityIndexFilter, EntityIndexHeater, EntityIndexPump
from .utils import get_entities_of_hass_type, get_entities_of_omni_types

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    filters_and_pumps = get_entities_of_omni_types(coordinator.data, [OmniType.FILTER, OmniType.PUMP])

    entities = []
    for system_id, pump in filters_and_pumps.items():
        _LOGGER.debug(
            "Configuring number for pump with ID: %s, Name: %s",
            pump.msp_config.system_id,
            pump.msp_config.name,
        )
        match pump.msp_config.type:
            case PumpType.VARIABLE_SPEED:
                entities.append(OmniLogicPumpNumberEntity(coordinator=coordinator, context=system_id))
            case FilterType.VARIABLE_SPEED:
                entities.append(OmniLogicFilterNumberEntity(coordinator=coordinator, context=system_id))

    all_heaters = get_entities_of_hass_type(coordinator.data, "water_heater")
    solar_heaters = {
        system_id: data
        for system_id, data in all_heaters.items()
        if data.msp_config.omni_type == OmniType.HEATER_EQUIP and data.msp_config.heater_type is HeaterType.SOLAR
    }

    if solar_heaters:
        virt_heaters = {system_id: data for system_id, data in all_heaters.items() if data.msp_config.omni_type == OmniType.VIRT_HEATER}

        for system_id, vheater in virt_heaters.items():
            if vheater.msp_config.solar_set_point is not None:
                _LOGGER.debug(
                    "Configuring number solar set point for heater with ID: %s, Name: %s",
                    vheater.msp_config.system_id,
                    vheater.msp_config.name,
                )
                entities.append(OmniLogicSolarSetPointNumberEntity(coordinator=coordinator, context=system_id))

    all_chlorinators = get_entities_of_omni_types(coordinator.data, [OmniType.CHLORINATOR])

    for system_id, chlor in all_chlorinators.items():
        chlorinator = cast(EntityIndexChlorinator, chlor)
        match chlorinator.msp_config.dispenser_type:
            case ChlorinatorDispenserType.SALT:
                match chlorinator.telemetry.operating_mode:
                    case ChlorinatorOperatingMode.TIMED:
                        _LOGGER.debug(
                            "Configuring number for chlorinator with ID: %s, Name: %s",
                            chlorinator.msp_config.system_id,
                            chlorinator.msp_config.name,
                        )
                        entities.append(OmniLogicChlorinatorTimedPercentNumberEntity(coordinator=coordinator, context=system_id))
                    case ChlorinatorOperatingMode.ORP:
                        _LOGGER.warning(
                            "Chlorinator ORP control is not supported yet, "
                            "please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                        )
            case ChlorinatorDispenserType.LIQUID:
                # Working in issue #116 on this support
                pass
            case _:
                _LOGGER.warning(
                    "Your system has an unsupported chlorinator, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                )

    async_add_entities(entities)


T = TypeVar("T", EntityIndexPump, EntityIndexFilter)


class OmniLogicVSPNumberEntity(OmniLogicEntity[T], NumberEntity):
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


class OmniLogicPumpNumberEntity(OmniLogicVSPNumberEntity[EntityIndexPump]):
    """An entity representing a number platform for an OmniLogic Pump."""

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self.native_unit_of_measurement == "RPM":
            new_speed_pct = round(value / self.native_max_value * 100)
        else:
            new_speed_pct = int(value)

        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, new_speed_pct)

        self.set_telemetry({"state": PumpState.ON, "speed": new_speed_pct})


class OmniLogicFilterNumberEntity(OmniLogicVSPNumberEntity[EntityIndexFilter]):
    """An OmniLogicFilterNumberEntity is a special case of an OmniLogicPumpNumberEntity."""

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self.native_unit_of_measurement == "RPM":
            new_speed_pct = round(value / self.native_max_value * 100)
        else:
            new_speed_pct = int(value)

        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, new_speed_pct)

        self.set_telemetry({"state": FilterState.ON, "speed": new_speed_pct})


class OmniLogicSolarSetPointNumberEntity(OmniLogicEntity[EntityIndexHeater], NumberEntity):
    """An OmniLogicFilterNumberEntity is a special case of an OmniLogicPumpNumberEntity."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_name = "Solar Set Point"
    _attr_mode = "box"

    @property
    def native_max_value(self) -> float:
        return self.data.msp_config.max_temp

    @property
    def native_min_value(self) -> float:
        return self.data.msp_config.min_temp

    @property
    def native_value(self) -> float | None:
        return self.data.msp_config.solar_set_point

    @property
    def native_unit_of_measurement(self) -> str | None:
        return str(UnitOfTemperature.CELSIUS) if self.get_system_config().units == "Metric" else str(UnitOfTemperature.FAHRENHEIT)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.omni_api.async_set_solar_heater(
            self.bow_id,
            self.system_id,
            int(value),
            unit=self.native_unit_of_measurement,
        )
        self.set_config({"solar_set_point": int(value)})


class OmniLogicChlorinatorTimedPercentNumberEntity(OmniLogicEntity[EntityIndexChlorinator], NumberEntity):
    """An OmniLogicFilterNumberEntity is a special case of an OmniLogicPumpNumberEntity."""

    _attr_name = "Chlorinator Timed Percent"
    _attr_native_max_value = 100
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float | None:
        return self.data.telemetry.timed_percent

    async def async_set_native_value(self, value: float) -> None:
        bow = cast(EntityIndexBodyOfWater, self.coordinator.data[self.bow_id])

        # The bow_type parameter doesn't seem to matter to the omni_api, it works just leaving it always 0
        # we are going to set it correctly though just in case
        bow_type: int = 0
        match bow.msp_config.type:
            case BodyOfWaterType.POOL:
                bow_type = 0
            case BodyOfWaterType.SPA:
                bow_type = 1

        await self.coordinator.omni_api.async_set_chlorinator_params(
            pool_id=self.bow_id,
            equipment_id=self.system_id,
            timed_percent=int(value),
            cell_type=int(self.data.msp_config.cell_type),
            op_mode=self.data.telemetry.operating_mode,
            sc_timeout=self.data.msp_config.superchlor_timeout,
            orp_timeout=self.data.msp_config.orp_timeout,
            bow_type=bow_type,
        )
        self.set_telemetry({"timed_percent": int(value)})
