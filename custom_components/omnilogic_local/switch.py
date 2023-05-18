from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, KEY_COORDINATOR, OmniModel, OmniType
from .entity import OmniLogicEntity
from .utils import get_entities_of_hass_type, get_omni_model

_LOGGER = logging.getLogger(__name__)


def get_power_state(data: dict[str, str]) -> int:
    match data["metadata"]["omni_type"]:
        case OmniType.RELAY:
            match data["omni_config"]["Type"]:
                case OmniModel.RELAY_VALVE_ACTUATOR:
                    return data["omni_telemetry"]["@valveActuatorState"]
                case _:
                    state_prefix = data["metadata"]["omni_type"][0].lower() + data["metadata"]["omni_type"][1:]
                    return data["omni_telemetry"]["@" + state_prefix + "State"]
        case _:
            # This pattern works for some "switch" devices I have, it does not work for everything. Notably, "Relays" represent
            # the physical relay within the Omni, but they are represented in the telemetry by what they control (I.E.: ValveActuator)
            # The generic pattern appears to be the omnilogic type, with the first letter lowercase, with "State" appended.
            # The @ is because the XML API is parsed with xmltodict and this was an XML attribute
            state_prefix = data["metadata"]["omni_type"][0].lower() + data["metadata"]["omni_type"][1:]
            return data["omni_telemetry"]["@" + state_prefix + "State"]


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
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
                match switch["omni_config"]["Type"]:
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


class OmniLogicSwitchEntity(OmniLogicEntity, SwitchEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context) -> None:
        """Pass coordinator to CoordinatorEntity."""
        switch_data = coordinator.data[context]
        super().__init__(
            coordinator,
            context=context,
            name=switch_data["metadata"]["name"],
            system_id=context,
            bow_id=switch_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.model = get_omni_model(switch_data)
        self.omni_type = switch_data["metadata"]["omni_type"]

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        _LOGGER.debug("turning on switch ID: %s", self.system_id)
        telem_key = kwargs["telem_key"]
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, True)
        self.set_telemetry({telem_key: 1})

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        _LOGGER.debug("turning off switch ID: %s", self.system_id)
        telem_key = kwargs["telem_key"]
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, False)
        # telem_key might be a list of items to set to 0, or just a single item
        if isinstance(telem_key, list):
            self.set_telemetry({key: 0 for key in telem_key})
        else:
            self.set_telemetry({telem_key: 0})


class OmniLogicRelayValveActuatorSwitchEntity(OmniLogicSwitchEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    @property
    def icon(self) -> str | None:
        return "mdi:valve-open" if self.is_on else "mdi:valve-closed"

    @property
    def is_on(self) -> bool | None:
        return self.get_telemetry()["@valveActuatorState"]

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await super().async_turn_on(telem_key="@valveActuatorState", **kwargs)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await super().async_turn_off(telem_key="@valveActuatorState", **kwargs)


class OmniLogicRelayHighVoltageSwitchEntity(OmniLogicSwitchEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    @property
    def icon(self) -> str | None:
        return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"

    @property
    def is_on(self) -> bool | None:
        return self.get_telemetry()["@relayState"]

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await super().async_turn_on(telem_key="@relayState", **kwargs)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await super().async_turn_off(telem_key="@relayState", **kwargs)


class OmniLogicPumpSwitchEntity(OmniLogicSwitchEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context) -> None:
        super().__init__(coordinator, context)
        self.telem_key_speed = "@pumpSpeed"
        self.telem_key_state = "@pumpState"

    @property
    def is_on(self) -> bool | None:
        return self.get_telemetry()[self.telem_key_state]

    @property
    def icon(self) -> str | None:
        return "mdi:pump" if self.is_on else "mdi:pump-off"

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await super().async_turn_on(telem_key=self.telem_key_state, **kwargs)

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await super().async_turn_off(telem_key=[self.telem_key_state, self.telem_key_speed], **kwargs)


class OmniLogicFilterSwitchEntity(OmniLogicPumpSwitchEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context) -> None:
        super().__init__(coordinator, context)
        self.telem_key_speed = "@filterSpeed"
        self.telem_key_state = "@filterState"
