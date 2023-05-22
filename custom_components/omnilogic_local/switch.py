from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN, KEY_COORDINATOR, OmniModel, OmniType
from .entity import OmniLogicEntity
from .types.entity_index import (
    EntityDataFilterT,
    EntityDataPumpT,
    EntityDataRelayT,
    EntityDataValveActuatorT,
)
from .utils import get_entities_of_hass_type

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""

    entities = []
    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    all_switches = get_entities_of_hass_type(coordinator.data, "switch")

    for system_id, switch in all_switches.items():
        match switch["metadata"]["omni_type"]:
            case OmniType.RELAY:
                _LOGGER.debug(
                    "Configuring switch for relay with ID: %s, Name: %s",
                    switch["metadata"]["system_id"],
                    switch["metadata"]["name"],
                )
                match switch["config"]["Type"]:
                    case OmniModel.RELAY_VALVE_ACTUATOR:
                        entities.append(OmniLogicRelayValveActuatorSwitchEntity(coordinator=coordinator, context=system_id))
                    case OmniModel.RELAY_HIGH_VOLTAGE:
                        entities.append(OmniLogicRelayHighVoltageSwitchEntity(coordinator=coordinator, context=system_id))
            case OmniType.FILTER:
                _LOGGER.debug(
                    "Configuring switch for filter with ID: %s, Name: %s",
                    switch["metadata"]["system_id"],
                    switch["metadata"]["name"],
                )
                entities.append(OmniLogicFilterSwitchEntity(coordinator=coordinator, context=system_id))
            case OmniType.PUMP:
                _LOGGER.debug(
                    "Configuring switch for pump with ID: %s, Name: %s",
                    switch["metadata"]["system_id"],
                    switch["metadata"]["name"],
                )
                entities.append(OmniLogicPumpSwitchEntity(coordinator=coordinator, context=system_id))

    async_add_entities(entities)


T = TypeVar("T", EntityDataRelayT, EntityDataFilterT, EntityDataPumpT, EntityDataValveActuatorT)


class OmniLogicSwitchEntity(OmniLogicEntity[T], SwitchEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_key_state: Literal["@valveActuatorState", "@filterState", "@pumpState", "@relayState"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on switch ID: %s", self.system_id)
        # telem_key = kwargs["telem_key"]
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, True)
        self.set_telemetry({self.telem_key_state: 1})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off switch ID: %s", self.system_id)
        # telem_key = kwargs["telem_key"]
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, False)
        self.set_telemetry({self.telem_key_state: 0})


class OmniLogicRelayValveActuatorSwitchEntity(OmniLogicSwitchEntity[EntityDataValveActuatorT]):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_key_state = "@valveActuatorState"

    @property
    def icon(self) -> str | None:
        return "mdi:valve-open" if self.is_on else "mdi:valve-closed"

    @property
    def is_on(self) -> bool | None:
        return self.data["telemetry"][self.telem_key_state] == 1


class OmniLogicRelayHighVoltageSwitchEntity(OmniLogicSwitchEntity[EntityDataRelayT]):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_key_state = "@relayState"

    @property
    def icon(self) -> str | None:
        return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"

    @property
    def is_on(self) -> bool | None:
        return self.data["telemetry"][self.telem_key_state] == 1


class OmniLogicPumpSwitchEntity(OmniLogicSwitchEntity[EntityDataPumpT]):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_key_state = "@pumpState"
    telem_key_speed = "@pumpSpeed"

    @property
    def icon(self) -> str | None:
        return "mdi:pump" if self.is_on else "mdi:pump-off"

    @property
    def is_on(self) -> bool | None:
        return self.data["telemetry"][self.telem_key_state] != 0

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await super().async_turn_off(telem_key=[self.telem_key_state, self.telem_key_speed], **kwargs)
        self.set_telemetry({self.telem_key_speed: 0})


class OmniLogicFilterSwitchEntity(OmniLogicSwitchEntity[EntityDataFilterT]):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    telem_key_speed = "@filterSpeed"
    telem_key_state = "@filterState"

    @property
    def is_on(self) -> bool | None:
        return self.data["telemetry"][self.telem_key_state] != 0

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await super().async_turn_off(telem_key=[self.telem_key_state, self.telem_key_speed], **kwargs)
        self.set_telemetry({self.telem_key_speed: 0})
