from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import logging
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, cast

from pyomnilogic_local.types import (
    ChlorinatorDispenserType,
    CSADType,
    FilterState,
    HeaterType,
    OmniType,
    SensorType,
    SensorUnits,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.helpers.typing import StateType

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .types.entity_index import (
    EntityIndexBackyard,
    EntityIndexBodyOfWater,
    EntityIndexChlorinator,
    EntityIndexCSAD,
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
                    "Configuring sensor for air temperature with ID: %s, Name: %s",
                    sensor.msp_config.system_id,
                    sensor.msp_config.name,
                )
                entities.append(OmniLogicAirTemperatureSensorEntity(coordinator=coordinator, context=system_id))
            case SensorType.WATER_TEMP:
                _LOGGER.debug(
                    "Configuring sensor for water temperature with ID: %s, Name: %s",
                    sensor.msp_config.system_id,
                    sensor.msp_config.name,
                )
                entities.append(OmniLogicWaterTemperatureSensorEntity(coordinator=coordinator, context=system_id))
            case SensorType.SOLAR_TEMP:
                # Reference https://github.com/cryptk/haomnilogic-local/issues/60 for why we do this
                # If a BoW has more than one solar temperature sensor, we need to only configure the sensors that are associated with actual
                # solar heaters.
                # We start by finding the solar heater that this sensor is associated with
                omni_entities = get_entities_of_omni_types(coordinator.data, [OmniType.HEATER_EQUIP])
                sensed_system_id = [
                    k
                    for k, v in omni_entities.items()
                    if v.msp_config.heater_type is HeaterType.SOLAR and v.msp_config.sensor_id == sensor.msp_config.system_id
                ]
                # Then we decide what to do based on how many solar heaters we find
                match len(sensed_system_id):
                    case 0:
                        _LOGGER.warning("Unable to locate a solar heater for sensor id: %s", sensor.msp_config.system_id)
                    case 1:
                        entities.append(
                            OmniLogicSolarTemperatureSensorEntity(
                                coordinator=coordinator, context=system_id, sensed_system_id=sensed_system_id[0]
                            )
                        )
                    case _:
                        _LOGGER.warning("Found multiple heaters for sensor id: %s", sensor.msp_config.system_id)
            case SensorType.FLOW:
                # This sensor type is implemented as a binary sensor, not a sensor
                pass
            case SensorType.EXT_INPUT:
                # As far as I can tell, "external input" sensors are not exposed in the telemetry,
                # they are only used for things like equipment interlocks
                pass
            case _:
                _LOGGER.warning(
                    "Your system has an unsupported sensor. ID: %s, Name: %s, Type: %s. Please raise an issue: https://github.com/cryptk/haomnilogic-local/issues",
                    sensor.msp_config.system_id,
                    sensor.msp_config.name,
                    sensor.msp_config.type,
                )

    # Create energy sensors for filters/pumps suitable for inclusion in the energy dashboard
    all_pumps = get_entities_of_omni_types(coordinator.data, [OmniType.FILTER])
    for system_id, pump in all_pumps.items():
        match pump.msp_config.omni_type:
            case OmniType.FILTER:
                _LOGGER.debug(
                    "Configuring sensor for filter energy with ID: %s, Name: %s",
                    pump.msp_config.system_id,
                    pump.msp_config.name,
                )
                entities.append(OmniLogicFilterEnergySensorEntity(coordinator=coordinator, context=system_id))

    all_chlorinators = get_entities_of_omni_types(coordinator.data, [OmniType.CHLORINATOR])
    for system_id, chlorinator in all_chlorinators.items():
        match cast(EntityIndexChlorinator, chlorinator).msp_config.dispenser_type:
            case ChlorinatorDispenserType.SALT:
                _LOGGER.debug(
                    "Configuring sensor for chlorinator salt level with ID: %s, Name: %s",
                    chlorinator.msp_config.system_id,
                    chlorinator.msp_config.name,
                )
                entities.append(
                    OmniLogicChlorinatorSaltLevelSensorEntity(coordinator=coordinator, context=system_id, sensor_type="average")
                )
                entities.append(
                    OmniLogicChlorinatorSaltLevelSensorEntity(coordinator=coordinator, context=system_id, sensor_type="instant")
                )
            case _:
                _LOGGER.warning(
                    "Your system has an unsupported chlorinator, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                )

    all_csads = get_entities_of_omni_types(coordinator.data, [OmniType.CSAD])
    for system_id, csad in all_csads.items():
        match cast(EntityIndexCSAD, csad).msp_config.type:
            case CSADType.ACID:
                _LOGGER.debug(
                    "Configuring sensor for CSAD ACID with ID: %s, Name: %s",
                    csad.msp_config.system_id,
                    csad.msp_config.name,
                )
                entities.append(OmniLogicCSADAcidEntity(coordinator=coordinator, context=system_id))
            case _:
                _LOGGER.warning(
                    "Your system has an unsupported CSAD unit, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                )

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
    _attr_state_class = SensorStateClass.MEASUREMENT
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
    def __init__(self, coordinator: OmniLogicCoordinator, context: int, sensed_system_id: int) -> None:
        super().__init__(coordinator, context, OmniType.HEATER_EQUIP)
        self._sensed_system_id = sensed_system_id

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_data.telemetry.temp
        return temp if temp not in [-1, 255, 65535] else None


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


class OmniLogicChlorinatorSaltLevelSensorEntity(OmniLogicEntity[EntityIndexChlorinator], SensorEntity):
    _attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _sensor_type: Literal["average", "instant"]

    def __init__(self, coordinator: OmniLogicCoordinator, context: int, sensor_type: Literal["average", "instant"]) -> None:
        super().__init__(coordinator, context)
        self._sensor_type = sensor_type

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        match self._sensor_type:
            case "average":
                return self.data.telemetry.avg_salt_level
            case "instant":
                return self.data.telemetry.instant_salt_level

    @property
    def name(self) -> Any:
        return f"{self.data.msp_config.name} {self._sensor_type.capitalize()} Salt Level"


class OmniLogicCSADAcidEntity(OmniLogicEntity[EntityIndexCSAD], SensorEntity):
    _attr_device_class = SensorDeviceClass.PH
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        super().__init__(coordinator, context)

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.data.telemetry.ph + self.data.msp_config.calibration_value

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        return super().extra_state_attributes | {
            "orp": self.data.telemetry.orp,
            "mode": self.data.telemetry.mode,
            "target_value": self.data.msp_config.target_value,
            "ph_value_raw": self.data.telemetry.ph,
            "calibration_value": self.data.msp_config.calibration_value,
            "ph_low_alarm_value": self.data.msp_config.ph_low_alarm_value,
            "ph_high_alarm_value": self.data.msp_config.ph_high_alarm_value,
        }
