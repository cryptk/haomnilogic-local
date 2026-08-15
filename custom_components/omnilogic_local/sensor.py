from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, cast

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfRatio, UnitOfTemperature
from pyomnilogic_local import CSAD, Backyard, Bow, Chlorinator, Filter, HeaterEquipment, Sensor
from pyomnilogic_local.omnitypes import ChlorinatorDispenserType, CSADMode, FilterState, HeaterType, SensorType

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .typing import OmniLogicEquipment

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class OmniLogicSensorEntityDescription(SensorEntityDescription):
    """Describes an OmniLogic binary sensor entity"""

    extra_state_attributes_fn: Callable[[OmniLogicEquipment], dict[str, Any]] = field(default_factory=lambda: lambda _: {})
    value_fn: Callable[[OmniLogicEquipment], bool | float | int | str | None]


FILTER_SENSORS: tuple[OmniLogicSensorEntityDescription, ...] = (
    OmniLogicSensorEntityDescription(
        key="filter_power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda equipment: (
            equipment.power
            if isinstance(equipment, Filter)
            and equipment.state
            in [
                FilterState.ON,
                FilterState.PRIMING,
                FilterState.HEATER_EXTEND,
                FilterState.CSAD_EXTEND,
                FilterState.FORCE_PRIMING,
                FilterState.SUPERCHLORINATE,
            ]
            else 0
        ),
    ),
)

CHLORINATOR_SALT_SENSORS: tuple[OmniLogicSensorEntityDescription, ...] = (
    OmniLogicSensorEntityDescription(
        key="chlorinator_salt_level_average",
        name="Average Salt Level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        value_fn=lambda equipment: equipment.avg_salt_level if isinstance(equipment, Chlorinator) else None,
    ),
    OmniLogicSensorEntityDescription(
        key="chlorinator_salt_level_instant",
        name="Instant Salt Level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        value_fn=lambda equipment: equipment.instant_salt_level if isinstance(equipment, Chlorinator) else None,
    ),
)

CSAD_SENSORS: tuple[OmniLogicSensorEntityDescription, ...] = (
    OmniLogicSensorEntityDescription(
        key="csad_ph",
        name="pH",
        device_class=SensorDeviceClass.PH,
        state_class=SensorStateClass.MEASUREMENT,
        extra_state_attributes_fn=lambda equipment: (
            {
                "omni_target_value": equipment.ph_target_level,
                "omni_value_raw": equipment.ph_current_value_raw,
                "omni_calibration_value": equipment.ph_calibration_value,
                "omni_low_alarm_value": equipment.ph_low_alarm_level,
                "omni_high_alarm_value": equipment.ph_high_alarm_level,
            }
            if isinstance(equipment, CSAD)
            else {}
        ),
        value_fn=lambda equipment: equipment.ph_current_value if isinstance(equipment, CSAD) else None,
    ),
    OmniLogicSensorEntityDescription(
        key="csad_orp",
        name="ORP",
        state_class=SensorStateClass.MEASUREMENT,
        extra_state_attributes_fn=lambda equipment: (
            {
                "omni_target_value": equipment.orp_target_level,
                "omni_runtime_level": equipment.orp_runtime_level,
                "omni_low_alarm_value": equipment.orp_low_alarm_level,
                "omni_high_alarm_value": equipment.orp_high_alarm_level,
            }
            if isinstance(equipment, CSAD)
            else {}
        ),
        value_fn=lambda equipment: equipment.orp_current_level if isinstance(equipment, CSAD) else None,
    ),
    OmniLogicSensorEntityDescription(
        key="csad_mode",
        name="Mode",
        device_class=SensorDeviceClass.ENUM,
        options=[str(mode) for mode in CSADMode],
        value_fn=lambda equipment: str(equipment.mode) if isinstance(equipment, CSAD) else None,
    ),
)


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
                if sensor.bow_id not in [None, -1]:  # https://github.com/cryptk/haomnilogic-local/issues/238
                    entities.append(OmniLogicWaterTemperatureSensorEntity(coordinator=coordinator, sensor=sensor))
                else:
                    _LOGGER.warning("Water temperature sensor %s does not have a bow_id, skipping", sensor.name)
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
        entities.extend(
            OmniLogicSensorEntity[Filter](
                coordinator=coordinator,
                equipment=filt,
                entity_description=description,
            )
            for description in FILTER_SENSORS
        )

    # Create salt level sensors for chlorinators
    for _, _, chlorinator in coordinator.omni.all_chlorinators.items():
        match chlorinator.dispenser_type:
            case ChlorinatorDispenserType.SALT:
                entities.extend(
                    OmniLogicSensorEntity[Chlorinator](
                        coordinator=coordinator,
                        equipment=chlorinator,
                        entity_description=description,
                    )
                    for description in CHLORINATOR_SALT_SENSORS
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
        entities.extend(
            OmniLogicSensorEntity[CSAD](
                coordinator=coordinator,
                equipment=csad,
                entity_description=description,
            )
            for description in CSAD_SENSORS
        )

    async_add_entities(entities)


type SensedEquipment = Backyard | Bow | HeaterEquipment


class OmniLogicTemperatureSensorEntity[SensedEquipment](OmniLogicEntity[Sensor], SensorEntity):
    """Sensor entity for temperature readings from pool equipment.

    Temperature sensors don't have their own telemetry - the readings come from the parent
    equipment (Backyard for air temp, Bow for water temp, HeaterEquipment for solar temp).

    The sensed_equipment value is passed in via the subclasses.
    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    sensed_id: int

    def __init__(self, coordinator: OmniLogicCoordinator, sensor: Sensor) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, sensor)

    @property
    def sensed_equipment(self) -> SensedEquipment:
        return cast(SensedEquipment, self.coordinator.omni.get_equipment_by_id(self.sensed_id))

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

    sensed_id = BACKYARD_SYSTEM_ID

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
        self.sensed_id = sensor.bow_id

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_equipment.water_temp
        return temp if temp not in [-1, 255, 65535] else None


class OmniLogicSolarTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[HeaterEquipment]):
    """Sensor entity for solar heater temperature readings."""

    def __init__(self, coordinator: OmniLogicCoordinator, sensor: Sensor, heater_equipment: HeaterEquipment) -> None:
        super().__init__(coordinator, sensor)
        if heater_equipment.system_id is None:
            msg = f"Solar heater {heater_equipment.name} does not have a system_id"
            raise ValueError(msg)
        self.sensed_id = heater_equipment.system_id

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_equipment.current_temp
        # There are some cases where the Omnilogic returns invalid temperature readings
        return temp if temp not in [-1, 255, 65535] else None


class OmniLogicSensorEntity[EquipmentType: OmniLogicEquipment](OmniLogicEntity[EquipmentType], SensorEntity):
    entity_description: OmniLogicSensorEntityDescription

    def __init__(
        self,
        coordinator: OmniLogicCoordinator,
        equipment: EquipmentType,
        entity_description: OmniLogicSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, equipment)
        self.entity_description = entity_description
        self._attr_name = f"{equipment.name} {entity_description.name}" if hasattr(entity_description, "name") else None

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.extra_state_attributes_fn(self.equipment)

    @property
    def native_value(self) -> bool | float | int | str | None:
        return self.entity_description.value_fn(self.equipment)
