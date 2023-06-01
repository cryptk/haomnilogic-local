from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from pyomnilogic_local.models.telemetry import TelemetryBoW
from pyomnilogic_local.types import BackyardState, HeaterState, OmniType, SensorType

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .types.entity_index import (
    EntityIndexBackyard,
    EntityIndexHeaterEquip,
    EntityIndexSensor,
)
from .utils import get_entities_of_hass_type, get_entities_of_omni_types

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities = []

    # Create a binary sensor entity indicating if we are in Service Mode
    _LOGGER.debug("Configuring service mode sensor with ID: %s", BACKYARD_SYSTEM_ID)
    entities.append(OmniLogicServiceModeBinarySensorEntity(coordinator=coordinator, context=BACKYARD_SYSTEM_ID))

    # Create binary sensor entities for each piece of Heater-Equipment
    heater_equipments = get_entities_of_omni_types(coordinator.data, [OmniType.HEATER_EQUIP])
    for system_id, equipment in heater_equipments.items():
        _LOGGER.debug(
            "Configuring heater equipment sensor with ID: %s, Name: %s",
            system_id,
            equipment.msp_config.name,
        )
        entities.append(
            OmniLogicHeaterEquipBinarySensorEntity(
                coordinator=coordinator,
                context=system_id,
            )
        )

    # Create a binary sensor entity for all appropriate sensors
    all_sensors = get_entities_of_hass_type(coordinator.data, "sensor")
    for system_id, sensor in all_sensors.items():
        match sensor.msp_config.type:
            case SensorType.AIR_TEMP | SensorType.WATER_TEMP | SensorType.SOLAR_TEMP:
                # These sensor types are implemented as sensors, not binary sensors
                pass
            case SensorType.FLOW:
                # It looks like a flow sensor likely populates either a 1 or a 0 on the BoW to indicate if water is flowing or not
                # If a BoW does not have a Flow Sensor, it appears that the flow attribute is 255
                # Need to confirm the assumption that the values are only 1 or 0 if there is a flow sensor and 255 if there is no flow
                # sensor before we implement this
                _LOGGER.debug(
                    "Configuring flow sensor with ID: %s, Name: %s",
                    system_id,
                    sensor.msp_config.name,
                )
                entities.append(
                    OmniLogicFlowBinarySensorEntity(
                        coordinator=coordinator,
                        context=system_id,
                    )
                )
            case SensorType.EXT_INPUT:
                # As far as I can tell, "external input" sensors are not exposed in the telemetry,
                # they are only used for things like equipment interlocks
                pass
            case _:
                _LOGGER.warning(
                    "Your system has an unsupported sensor, please raise an issue: https://github.com/cryptk/haomnilogic-local/issues"
                )

    async_add_entities(entities)


class OmniLogicServiceModeBinarySensorEntity(OmniLogicEntity[EntityIndexBackyard], BinarySensorEntity):
    _attr_name = "Service Mode"

    @property
    def available(self) -> bool:
        # This is one of the few things we can pull from the telemetry even if we are in service mode
        return True

    @property
    def is_on(self) -> bool:
        return self.data.telemetry.state in [BackyardState.SERVICE_MODE, BackyardState.CONFIG_MODE, BackyardState.TIMED_SERVICE_MODE]


class OmniLogicHeaterEquipBinarySensorEntity(OmniLogicEntity[EntityIndexHeaterEquip], BinarySensorEntity):
    """Expose a binary state via a sensor based on telemetry data."""

    device_class = BinarySensorDeviceClass.HEAT

    @property
    def icon(self) -> str | None:
        return "mdi:water-boiler" if self.is_on else "mdi:water-boiler-off"

    @property
    def name(self) -> str:
        return f"{self.data.msp_config.name} Status"

    @property
    def is_on(self) -> bool:
        return self.data.telemetry.state is HeaterState.ON


class OmniLogicFlowBinarySensorEntity(OmniLogicEntity[EntityIndexSensor], BinarySensorEntity):
    """Expose a binary state via a sensor based on telemetry data."""

    @property
    def icon(self) -> str | None:
        return "mdi:water-check" if self.is_on else "mdi:water-remove"

    @property
    def name(self) -> str:
        return f"{self.data.msp_config.name} Status"

    @property
    def is_on(self) -> bool:
        my_bow_telem = cast(TelemetryBoW, self.get_telemetry_by_systemid(self.data.msp_config.bow_id))
        return my_bow_telem.flow == 1
