from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar, cast

from pyomnilogic_local.models.telemetry import TelemetryFilter
from pyomnilogic_local.omnitypes import (
    BodyOfWaterType,
    FilterState,
    FilterValvePosition,
    OmniType,
    PumpState,
    RelayFunction,
    RelayState,
    RelayType,
    ValveActuatorState,
)

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .types.entity_index import (
    EntityIndexBodyOfWater,
    EntityIndexChlorinator,
    EntityIndexFilter,
    EntityIndexPump,
    EntityIndexRelay,
    EntityIndexValveActuator,
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

    entities = []
    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    all_switches = get_entities_of_hass_type(coordinator.data, "switch")

    for system_id, switch in all_switches.items():
        match switch.msp_config.omni_type:
            case OmniType.RELAY:
                _LOGGER.debug(
                    "Configuring switch for relay with ID: %s, Name: %s",
                    switch.msp_config.system_id,
                    switch.msp_config.name,
                )
                match switch.msp_config.type:
                    case RelayType.VALVE_ACTUATOR:
                        entities.append(OmniLogicRelayValveActuatorSwitchEntity(coordinator=coordinator, context=system_id))
                    case RelayType.HIGH_VOLTAGE:
                        entities.append(OmniLogicRelayHighVoltageSwitchEntity(coordinator=coordinator, context=system_id))
            case OmniType.FILTER:
                _LOGGER.debug(
                    "Configuring switch for filter with ID: %s, Name: %s",
                    switch.msp_config.system_id,
                    switch.msp_config.name,
                )
                entities.append(OmniLogicFilterSwitchEntity(coordinator=coordinator, context=system_id))
            case OmniType.PUMP:
                _LOGGER.debug(
                    "Configuring switch for pump with ID: %s, Name: %s",
                    switch.msp_config.system_id,
                    switch.msp_config.name,
                )
                entities.append(OmniLogicPumpSwitchEntity(coordinator=coordinator, context=system_id))
            case OmniType.CHLORINATOR:
                _LOGGER.debug(
                    "Configuring switch for chlorinator with ID: %s, Name: %s",
                    switch.msp_config.system_id,
                    switch.msp_config.name,
                )
                entities.append(OmniLogicChlorinatorSwitchEntity(coordinator=coordinator, context=system_id))

    # Add switches for spillover into pools if supported
    all_bows = get_entities_of_omni_types(coordinator.data, [OmniType.BOW])
    for system_id, bow in all_bows.items():
        match bow.msp_config.type:
            case BodyOfWaterType.POOL:
                if bow.msp_config.supports_spillover == "yes":
                    _LOGGER.debug(
                        "Configuring switch for spillover with ID: %s, Name: %s",
                        bow.msp_config.system_id,
                        bow.msp_config.name,
                    )
                    entities.append(OmniLogicSpilloverSwitchEntity(coordinator=coordinator, context=system_id))

    async_add_entities(entities)


T = TypeVar("T", EntityIndexRelay, EntityIndexFilter, EntityIndexPump, EntityIndexValveActuator)


class OmniLogicSwitchEntity(OmniLogicEntity[T], SwitchEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_value_state: ValveActuatorState | RelayState | PumpState | FilterState

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on switch ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, True)
        self.set_telemetry({"state": self.telem_value_state.ON})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off switch ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, False)
        self.set_telemetry({"state": self.telem_value_state.OFF})

    @property
    def is_on(self) -> bool | None:
        return self.data.telemetry.state == self.telem_value_state.ON


class OmniLogicRelayValveActuatorSwitchEntity(OmniLogicSwitchEntity[EntityIndexValveActuator]):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_value_state = ValveActuatorState

    @property
    def icon(self) -> str | None:
        match self.data.msp_config.function:
            case RelayFunction.WATERFALL:
                return "mdi:waterfall"
            case RelayFunction.FOUNTAIN:
                return "mdi:fountain"
            case RelayFunction.WATER_FEATURE:
                return "mdi:fountain"
            case RelayFunction.WATER_SLIDE:
                return "mdi:slide"
            case RelayFunction.LAMINARS:
                return "mdi:light"
            case RelayFunction.LIGHT:
                return "mdi:light"
            case RelayFunction.BACKYARD_LIGHT:
                return "mdi:light"
            case _:
                return "mdi:valve-open" if self.is_on else "mdi:valve-closed"

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        return super().extra_state_attributes | {
            "why_on": self.data.telemetry.why_on,
        }


class OmniLogicRelayHighVoltageSwitchEntity(OmniLogicSwitchEntity[EntityIndexRelay]):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_value_state = RelayState

    @property
    def icon(self) -> str | None:
        return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"


class OmniLogicPumpSwitchEntity(OmniLogicSwitchEntity[EntityIndexPump]):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_value_state = PumpState

    @property
    def icon(self) -> str | None:
        return "mdi:pump" if self.is_on else "mdi:pump-off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on pump ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, self.data.telemetry.last_speed)
        self.set_telemetry({"state": PumpState.ON})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off pump ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, False)
        self.set_telemetry({"state": PumpState.OFF, "speed": 0})


class OmniLogicFilterSwitchEntity(OmniLogicSwitchEntity[EntityIndexFilter]):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_value_state = FilterState

    @property
    def icon(self) -> str | None:
        return "mdi:pump" if self.is_on else "mdi:pump-off"

    @property
    def is_on(self) -> bool | None:
        return self.data.telemetry.state in [
            FilterState.ON,
            FilterState.PRIMING,
            FilterState.HEATER_EXTEND,
            FilterState.CSAD_EXTEND,
            FilterState.FILTER_FORCE_PRIMING,
            FilterState.FILTER_SUPERCHLORINATE,
        ]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on filter ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, self.data.telemetry.last_speed)
        self.set_telemetry({"state": FilterState.PRIMING})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off filter ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, False)
        self.set_telemetry({"state": FilterState.OFF, "speed": 0})

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        return super().extra_state_attributes | {
            "filter_state": self.data.telemetry.state.pretty(),
            "why_on": self.data.telemetry.why_on.pretty(),
        }


class OmniLogicChlorinatorSwitchEntity(OmniLogicEntity[EntityIndexChlorinator], SwitchEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_value_state = RelayState

    @property
    def icon(self) -> str | None:
        return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"

    @property
    def is_on(self) -> bool | None:
        return self.data.telemetry.enable is True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on chlorinator ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_chlorinator_enable(self.bow_id, True)
        self.set_telemetry({"enable": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off chlorinator ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_chlorinator_enable(self.bow_id, False)
        self.set_telemetry({"enable": False})


class OmniLogicSpilloverSwitchEntity(OmniLogicEntity[EntityIndexBodyOfWater], SwitchEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_name = "Spillover"

    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        super().__init__(coordinator, context)
        # This is all a little gross, and it means that we can only support one filter system per BoW, but I believe that is a limitation of
        # the Omni system anyway.  They can have multiple pumps, but only one "filter"
        all_filters = get_entities_of_omni_types(coordinator.data, [OmniType.FILTER])
        bow_filter = {
            system_id: bow_filter for (system_id, bow_filter) in all_filters.items() if bow_filter.msp_config.bow_id == self.bow_id
        }
        self.filter_system_id = list(bow_filter.keys())[0]

    @property
    def icon(self) -> str | None:
        return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"

    @property
    def is_on(self) -> bool | None:
        return cast(TelemetryFilter, self.get_telemetry_by_systemid(self.filter_system_id)).valve_position == FilterValvePosition.SPILLOVER

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on spillover ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_spillover(self.bow_id, 75)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off spillover ID: %s", self.system_id)
        await self.coordinator.omni_api.async_set_spillover(self.bow_id, 0)
