from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import logging
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from pyomnilogic_local.types import FilterState, OmniType, SensorType, SensorUnits

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower, UnitOfTemperature
from homeassistant.helpers.typing import StateType

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .errors import OmniLogicError
from .types.entity_index import (
    EntityIndexBackyard,
    EntityIndexBodyOfWater,
    EntityIndexFilter,
    EntityIndexHeaterEquip,
    EntityIndexSensor,
)
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

    # Create a sensor entity for all temperature sensors
    all_sensors = get_entities_of_hass_type(coordinator.data, "sensor")
    entities = []
    for system_id, sensor in all_sensors.items():
        match sensor.msp_config.type:
            case SensorType.AIR_TEMP:
                _LOGGER.debug(
                    "Configuring air temperature sensor with ID: %s, Name: %s",
                    sensor.msp_config.system_id,
                    sensor.msp_config.name,
                )
                entities.append(OmniLogicAirTemperatureSensorEntity(coordinator=coordinator, context=system_id))
            case SensorType.WATER_TEMP:
                _LOGGER.debug(
                    "Configuring water temperature sensor with ID: %s, Name: %s",
                    sensor.msp_config.system_id,
                    sensor.msp_config.name,
                )
                entities.append(OmniLogicWaterTemperatureSensorEntity(coordinator=coordinator, context=system_id))
            case SensorType.SOLAR_TEMP:
                _LOGGER.debug(
                    "Configuring solar temperature sensor with ID: %s, Name: %s",
                    sensor.msp_config.system_id,
                    sensor.msp_config.name,
                )
                entities.append(OmniLogicSolarTemperatureSensorEntity(coordinator=coordinator, context=system_id))
            case SensorType.FLOW:
                # This sensor type is implemented as a binary sensor, not a sensor
                pass
            case SensorType.EXT_INPUT:
                # As far as I can tell, "external input" sensors are not exposed in the telemetry,
                # they are only used for things like equipment interlocks
                pass
            case _:
                _LOGGER.warning(
                    "Your system has an unsupported sensor, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                )

    # Create energy sensors for filters/pumps suitable for inclusion in the energy dashboard
    all_pumps = get_entities_of_omni_types(coordinator.data, [OmniType.FILTER])
    for system_id, pump in all_pumps.items():
        match pump.msp_config.omni_type:
            case OmniType.FILTER:
                _LOGGER.debug(
                    "Configuring energy sensor for filter with ID: %s, Name: %s",
                    pump.msp_config.system_id,
                    pump.msp_config.name,
                )
                entities.append(OmniLogicFilterEnergySensorEntity(coordinator=coordinator, context=system_id))

    async_add_entities(entities)


T = TypeVar("T", EntityIndexBackyard, EntityIndexBodyOfWater, EntityIndexHeaterEquip)


class OmniLogicTemperatureSensorEntity(OmniLogicEntity[EntityIndexSensor], SensorEntity, Generic[T]):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _sensed_system_id: int | None = None

    def __init__(self, coordinator: OmniLogicCoordinator, context: int, sensed_type: OmniType) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context)
        self.sensed_type = sensed_type

    @property
    def sensed_data(self) -> T:
        return cast(T, self.coordinator.data[self.sensed_system_id])

    @property
    def sensed_system_id(self) -> int:
        if self._sensed_system_id is not None:
            return self._sensed_system_id
        raise NotImplementedError

    @property
    def native_unit_of_measurement(self) -> str | None:
        match self.data.msp_config.units:
            case SensorUnits.FAHRENHEIT:
                return UnitOfTemperature.FAHRENHEIT
            case SensorUnits.CELSIUS:
                return UnitOfTemperature.CELSIUS
            case _:
                return None

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        raise NotImplementedError


class OmniLogicAirTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[EntityIndexBackyard]):
    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        super().__init__(coordinator, context, OmniType.BACKYARD)
        self._sensed_system_id = BACKYARD_SYSTEM_ID

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_data.telemetry.air_temp
        return temp if temp not in [-1, 255, 65535] else None


class OmniLogicWaterTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[EntityIndexBodyOfWater]):
    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        super().__init__(coordinator, context, OmniType.BOW)
        self._sensed_system_id = self.bow_id

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_data.telemetry.water_temp
        return temp if temp not in [-1, 255, 65535] else None


class OmniLogicSolarTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[EntityIndexHeaterEquip]):
    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        super().__init__(coordinator, context, OmniType.HEATER_EQUIP)

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_data.telemetry.temp
        return temp if temp not in [-1, 255, 65535] else None

    @property
    def sensed_system_id(self) -> int:
        omni_entities = get_entities_of_omni_types(self.coordinator.data, [self.sensed_type])
        found = [k for k, v in omni_entities.items() if v.msp_config.sensor_id == self.system_id]
        match len(found):
            case 0:
                raise OmniLogicError("Unable to locate a heater for sensor id: %s" % self.system_id)
            case 1:
                return found[0]
            case _:
                raise OmniLogicError("Found multiple heaters for sensor id: %s" % self.system_id)


class OmniLogicFilterEnergySensorEntity(OmniLogicEntity[EntityIndexFilter], SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return (
            self.data.telemetry.power
            if self.data.telemetry.state
            in [
                FilterState.ON,
                FilterState.PRIMING,
                FilterState.HEATER_EXTEND,
                FilterState.CSAD_EXTEND,
                FilterState.FILTER_FORCE_PRIMING,
                FilterState.FILTER_SUPERCHLORINATE,
            ]
            else 0
        )

    @property
    def name(self) -> Any:
        return f"{self.data.msp_config.name} Power"
