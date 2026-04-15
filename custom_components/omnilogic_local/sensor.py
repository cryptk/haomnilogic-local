from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION, UnitOfPower, UnitOfTemperature
from pyomnilogic_local import CSAD, Backyard, Bow, Chlorinator, Filter, HeaterEquipment, Sensor
from pyomnilogic_local.omnitypes import ChlorinatorDispenserType, CSADType, FilterState, HeaterType, SensorType

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the sensor platform."""
    coordinator: OmniLogicCoordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities: list[SensorEntity] = []

    # Create sensor entities for all temperature sensors
    for _, _, sensor in coordinator.omni.all_sensors.items():
        match sensor.equip_type:
            case SensorType.AIR_TEMP:
                entities.append(OmniLogicAirTemperatureSensorEntity(coordinator=coordinator, sensor=sensor))
            case SensorType.WATER_TEMP:
                entities.append(OmniLogicWaterTemperatureSensorEntity(coordinator=coordinator, sensor=sensor))
            case SensorType.SOLAR_TEMP:
                # Reference https://github.com/cryptk/haomnilogic-local/issues/60 for why we do this
                # If a BoW has more than one solar temperature sensor, we need to only configure the sensors that are associated with actual
                # solar heaters.
                # We start by finding the solar heater that this sensor is associated with
                solar_heaters = [
                    heater_equip
                    for _, _, heater_equip in coordinator.omni.all_heater_equipment.items()
                    if heater_equip.heater_type == HeaterType.SOLAR and heater_equip.sensor_id == sensor.system_id
                ]
                # Then we decide what to do based on how many solar heaters we find
                match len(solar_heaters):
                    case 0:
                        _LOGGER.warning("Unable to locate a solar heater for sensor id: %s", sensor.system_id)
                    case 1:
                        entities.append(
                            OmniLogicSolarTemperatureSensorEntity(coordinator=coordinator, sensor=sensor, heater_equipment=solar_heaters[0])
                        )
                    case _:
                        _LOGGER.warning("Found multiple heaters for sensor id: %s", sensor.system_id)
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
                    sensor.system_id,
                    sensor.name,
                    sensor.equip_type,
                )

    # Create energy sensors for filters suitable for inclusion in the energy dashboard
    for _, _, filt in coordinator.omni.all_filters.items():
        entities.append(OmniLogicFilterEnergySensorEntity(coordinator=coordinator, equipment=filt))

    # Create salt level sensors for chlorinators
    for _, _, chlorinator in coordinator.omni.all_chlorinators.items():
        match chlorinator.dispenser_type:
            case ChlorinatorDispenserType.SALT:
                entities.append(
                    OmniLogicChlorinatorSaltLevelSensorEntity(coordinator=coordinator, equipment=chlorinator, sensor_type="average")
                )
                entities.append(
                    OmniLogicChlorinatorSaltLevelSensorEntity(coordinator=coordinator, equipment=chlorinator, sensor_type="instant")
                )
            case ChlorinatorDispenserType.LIQUID:
                # It looks like there are no liquid sensors exposed in the telemetry
                pass
            case _:
                _LOGGER.warning(
                    "Your system has an unsupported chlorinator, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                )

    # Create pH and ORP sensors for CSAD systems
    for _, _, csad in coordinator.omni.all_csads.items():
        match csad.equip_type:
            case CSADType.ACID | CSADType.CO2:
                entities.append(OmniLogicCSADAcidPhEntity(coordinator=coordinator, equipment=csad))
                entities.append(OmniLogicCSADAcidORPEntity(coordinator=coordinator, equipment=csad))

    async_add_entities(entities)


SensedEquipmentT = TypeVar("SensedEquipmentT", bound=Backyard | Bow | HeaterEquipment)


class OmniLogicTemperatureSensorEntity(OmniLogicEntity[Sensor], SensorEntity, Generic[SensedEquipmentT]):
    """Sensor entity for temperature readings from pool equipment.

    Temperature sensors don't have their own telemetry - the readings come from the parent
    equipment (Backyard for air temp, Bow for water temp, HeaterEquipment for solar temp).

    The sensed_equipment value is passed in via the subclasses.
    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    sensed_equipment: SensedEquipmentT

    def __init__(self, coordinator: OmniLogicCoordinator, sensor: Sensor) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, sensor)

    @property
    def native_unit_of_measurement(self) -> str | None:
        # The Omnilogic system always operates in Fahrenheit internally, so that's our native unit
        # Home Assistant will handle unit conversion based on user preferences
        return str(UnitOfTemperature.FAHRENHEIT)

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        raise NotImplementedError


class OmniLogicAirTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[Backyard]):
    """Sensor entity for air temperature readings."""

    def __init__(self, coordinator: OmniLogicCoordinator, sensor: Sensor) -> None:
        super().__init__(coordinator, sensor)
        self.sensed_equipment = coordinator.omni.backyard

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_equipment.air_temp
        return temp if temp not in [-1, 255, 65535] else None


class OmniLogicWaterTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[Bow]):
    """Sensor entity for body of water temperature readings."""

    def __init__(self, coordinator: OmniLogicCoordinator, sensor: Sensor) -> None:
        super().__init__(coordinator, sensor)
        # Get the bow that this sensor belongs to
        if sensor.bow_id is None:
            msg = f"Sensor {sensor.name} does not have a bow_id"
            raise ValueError(msg)
        self.sensed_equipment = coordinator.omni.backyard.bow[sensor.bow_id]

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_equipment.water_temp
        return temp if temp not in [-1, 255, 65535] else None


class OmniLogicSolarTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[HeaterEquipment]):
    """Sensor entity for solar heater temperature readings."""

    def __init__(self, coordinator: OmniLogicCoordinator, sensor: Sensor, heater_equipment: HeaterEquipment) -> None:
        super().__init__(coordinator, sensor)
        self.sensed_equipment = heater_equipment

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_equipment.current_temp
        # There are some cases where the Omnilogic returns invalid temperature readings
        return temp if temp not in [-1, 255, 65535] else None


class OmniLogicFilterEnergySensorEntity(OmniLogicEntity[Filter], SensorEntity):
    """Sensor entity for filter power consumption."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return (
            self.equipment.power
            if self.equipment.state
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
        return f"{self.equipment.name} Power"


class OmniLogicChlorinatorSaltLevelSensorEntity(OmniLogicEntity[Chlorinator], SensorEntity):
    """Sensor entity for chlorinator salt level readings."""

    _attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _sensor_type: Literal["average", "instant"]

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Chlorinator, sensor_type: Literal["average", "instant"]) -> None:
        super().__init__(coordinator, equipment)
        self._sensor_type = sensor_type

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        match self._sensor_type:
            case "average":
                return self.equipment.avg_salt_level
            case "instant":
                return self.equipment.instant_salt_level

    @property
    def name(self) -> Any:
        return f"{self.equipment.name} {self._sensor_type.capitalize()} Salt Level"


class OmniLogicCSADAcidPhEntity(OmniLogicEntity[CSAD], SensorEntity):
    """Sensor entity for CSAD acid pH level readings."""

    _attr_device_class = SensorDeviceClass.PH
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.equipment.current_ph + self.equipment.calibration_value

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return {
            "omni_orp": self.equipment.current_orp,
            "omni_mode": str(self.equipment.mode),
            "omni_target_value": self.equipment.target_ph,
            "omni_ph_value_raw": self.equipment.current_ph,
            "omni_calibration_value": self.equipment.calibration_value,
            "omni_ph_low_alarm_value": self.equipment.ph_low_alarm,
            "omni_ph_high_alarm_value": self.equipment.ph_high_alarm,
        }


class OmniLogicCSADAcidORPEntity(OmniLogicEntity[CSAD], SensorEntity):
    """Sensor entity for CSAD ORP level readings."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "ORP"

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.equipment.current_orp

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return {
            "omni_target_level": self.equipment.orp_target_level,
            "omni_runtime_level": self.equipment.orp_runtime_level,
            "omni_low_alarm_level": self.equipment.orp_low_alarm_level,
            "omni_high_alarm_level": self.equipment.orp_high_alarm_level,
            "omni_forced_on_time": self.equipment.orp_forced_on_time,
            "omni_forced_enabled": self.equipment.orp_forced_enabled,
        }
