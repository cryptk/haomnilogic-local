from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import logging
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.typing import StateType

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR, OmniModel, OmniType
from .entity import OmniLogicEntity
from .errors import OmniLogicError
from .types.entity_index import (
    EntityDataBackyardT,
    EntityDataBodyOfWaterT,
    EntityDataHeaterEquipT,
    EntityDataSensorT,
)
from .utils import get_entities_of_hass_type, get_entities_of_omni_types, get_omni_model

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator
    from .types.entity_index import EntityIndexT

_LOGGER = logging.getLogger(__name__)


def find_sensed_systemid(data: EntityIndexT, sensor_system_id: int, omni_type: OmniType) -> int | None:
    omni_entities = get_entities_of_omni_types(data, [omni_type])
    # _LOGGER.debug(sensor_system_id)
    # _LOGGER.debug(omni_entities)
    # _LOGGER.debug([v['config']['Sensor_System_Id'] for k, v in heater_equip.items()])
    # _LOGGER.debug([k for k, v in heater_equip.items() if v["config"]["Sensor_System_Id"] == sensor_system_id])
    found = [k for k, v in omni_entities.items() if v["config"]["Sensor_System_Id"] == sensor_system_id]
    match len(found):
        case 0:
            raise OmniLogicError("Unable to locate a heater for sensor id: %s" % sensor_system_id)
        case 1:
            return found[0]
        case _:
            raise OmniLogicError("Found multiple heaters for sensor id: %s" % sensor_system_id)
    # return found[0]
    # for system_id, heater in heater_equip.items():
    #     if heater["config"].get("Sensor_System_Id") == sensor_system_id:
    #         return system_id
    # raise OmniLogicError("Unable to locate ")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    # Create a sensor entity for all temperature sensors
    all_sensors = get_entities_of_hass_type(coordinator.data, "sensor")
    entities = []
    for system_id, sensor in all_sensors.items():
        _LOGGER.debug(
            "Configuring sensor with ID: %s, Name: %s",
            sensor["metadata"]["system_id"],
            sensor["metadata"]["name"],
        )
        match get_omni_model(sensor):
            case OmniModel.SENSOR_AIR:
                entities.append(OmniLogicAirTemperatureSensorEntity(coordinator=coordinator, context=system_id))
            case OmniModel.SENSOR_WATER:
                entities.append(OmniLogicWaterTemperatureSensorEntity(coordinator=coordinator, context=system_id))
            case OmniModel.SENSOR_SOLAR:
                entities.append(OmniLogicSolarTemperatureSensorEntity(coordinator=coordinator, context=system_id))
            case _:
                _LOGGER.error(
                    "Your system has an unsupported sensor, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                )
        # if sensor["config"]["Type"] in [OmniModel.SENSOR_AIR, OmniModel.SENSOR_WATER, OmniModel.SENSOR_SOLAR]:
        #     _LOGGER.debug(
        #         "Configuring temperature sensor with ID: %s, Name: %s",
        #         sensor["metadata"]["system_id"],
        #         sensor["metadata"]["name"],
        #     )
        #     entities.append(OmniLogicTemperatureSensorEntity(coordinator=coordinator, context=system_id))

    async_add_entities(entities)


# class OmniLogicSensorEntity(OmniLogicEntity[], SensorEntity):
#     """An entity using CoordinatorEntity.

#     The CoordinatorEntity class provides:
#       should_poll
#       async_update
#       async_added_to_hass
#       available

#     """

#     _attr_state_class = SensorStateClass.MEASUREMENT

#     def __init__(self, coordinator, context, name: str = None) -> None:
#         """Pass coordinator to CoordinatorEntity."""
#         sensor_data = coordinator.data[context]
#         super().__init__(
#             coordinator,
#             context,
#             name=name if name is not None else sensor_data["metadata"]["name"],
#             system_id=sensor_data["metadata"]["system_id"],
#             bow_id=sensor_data["metadata"]["bow_id"],
#             extra_attributes=None,
#         )
#         self.omni_type = sensor_data["metadata"]["omni_type"]
#         self.model = sensor_data["config"].get("Type")

T = TypeVar("T", EntityDataBackyardT, EntityDataBodyOfWaterT, EntityDataHeaterEquipT)


class OmniLogicTemperatureSensorEntity(OmniLogicEntity[EntityDataSensorT], SensorEntity, Generic[T]):
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
        match self.data["config"]["Units"]:
            case "UNITS_FAHRENHEIT":
                return UnitOfTemperature.FAHRENHEIT  # type: ignore[no-any-return]
            case "UNITS_CELCIUS":
                return UnitOfTemperature.CELSIUS
            case _:
                return None

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        raise NotImplementedError


class OmniLogicAirTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[EntityDataBackyardT]):
    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        super().__init__(coordinator, context, OmniType.BACKYARD)
        self._sensed_system_id = BACKYARD_SYSTEM_ID

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_data["telemetry"]["@airTemp"]
        return temp if temp not in [-1, 255, 65535] else None


class OmniLogicWaterTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[EntityDataBodyOfWaterT]):
    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        super().__init__(coordinator, context, OmniType.BOW)
        self._sensed_system_id = self.bow_id

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_data["telemetry"]["@waterTemp"]
        return temp if temp not in [-1, 255, 65535] else None


class OmniLogicSolarTemperatureSensorEntity(OmniLogicTemperatureSensorEntity[EntityDataHeaterEquipT]):
    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        super().__init__(coordinator, context, OmniType.HEATER_EQUIP)

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        temp = self.sensed_data["telemetry"]["@temp"]
        return temp if temp not in [-1, 255, 65535] else None

    @property
    def sensed_system_id(self) -> int:
        omni_entities = get_entities_of_omni_types(self.coordinator.data, [self.sensed_type])
        found = [k for k, v in omni_entities.items() if v["config"]["Sensor_System_Id"] == self.system_id]
        match len(found):
            case 0:
                raise OmniLogicError("Unable to locate a heater for sensor id: %s" % self.system_id)
            case 1:
                return found[0]
            case _:
                raise OmniLogicError("Found multiple heaters for sensor id: %s" % self.system_id)
