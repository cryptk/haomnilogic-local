from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, KEY_COORDINATOR
from .types import OmniLogicEntity
from .utils import get_entities_of_type

_LOGGER = logging.getLogger(__name__)

def get_omni_model(data: dict[str,str]) -> str:
    match data['metadata']['omni_type']:
        case 'Filter':
            return data['omni_config']['Filter-Type']
        case _:
            return data['omni_config']['Type']

def get_power_state(data: dict[str,str]) -> int:
    match data['metadata']['omni_type']:
        case _:
            # This pattern works for all "switch" devices I have, it does not work for lights/heaters/etc
            # but in this platform we aren't worried about those. I have it in a match block because I wouldn't
            # be surprised if Hayward didn't follow this standard for everything. The general pattern appears to
            # be the omnilogic type, with the first letter lowercase, with "State" appended. The @ is because the
            # XML API is parsed with xmltodict and this was an XML attribute
            state_prefix = data['metadata']['omni_type'][0].lower() + data['metadata']['omni_type'][1:]
            return int(data['omni_telemetry']['@'+state_prefix+'State'])

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_lights = get_entities_of_type(coordinator.data, "switch")

    entities = []
    for system_id, light in all_lights.items():
        _LOGGER.debug(
            "Configuring switch with ID: %s, Name: %s",
            light["metadata"]["system_id"],
            light["metadata"]["name"],
        )
        entities.append(
            OmniLogicSwitchEntity(coordinator=coordinator, context=system_id)
        )

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
            system_id=switch_data["metadata"]["system_id"],
            bow_id=switch_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.model = get_omni_model(switch_data)
        self.omni_type = switch_data['metadata']['omni_type']
        self._attr_is_on = get_power_state(switch_data)
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        switch_data = self.coordinator.data[self.context]
        self._attr_is_on = get_power_state(switch_data)
        self.async_write_ha_state()

    @property
    def icon(self) -> str | None:
        match self.omni_type:
            case 'Filter':
                return "mdi:pump" if self._attr_is_on else "mdi:pump-off"
            case 'ValveActuator':
                return "mdi:valve-open" if self._attr_is_on else "mdi:valve-closed"
            case _:
                return "mdi:toggle-switch-variant" if self._attr_is_on else "mdi:toggle-switch-variant-off"

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        _LOGGER.debug("turning on switch ID: %s", self.system_id)
        await self.coordinator.omni_api.asyncSetEquipment(self.bow_id, self.system_id, True)
        self._attr_is_on = True
        self.push_assumed_state()
    
    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        _LOGGER.debug("turning off switch ID: %s", self.system_id)
        await self.coordinator.omni_api.asyncSetEquipment(self.bow_id, self.system_id, False)
        self._attr_is_on = False
        self.push_assumed_state()