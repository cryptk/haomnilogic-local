from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, KEY_COORDINATOR, OMNI_TYPES_PUMP, OmniModels
from .types import OmniLogicEntity
from .utils import get_entities_of_omni_types, get_omni_model

_LOGGER = logging.getLogger(__name__)

OMNI_SPEED_FRIENDLY_NAMES = {
    "Vsp_Low_Pump_Speed": "Low Speed",
    "Vsp_Medium_Pump_Speed": "Medium Speed",
    "Vsp_High_Pump_Speed": "High Speed",
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_pumps = get_entities_of_omni_types(coordinator.data, OMNI_TYPES_PUMP)

    entities = []
    for system_id, pump in all_pumps.items():
        pump_type = get_omni_model(pump)
        # pump_type = pump["omni_config"]["Filter-Type"] if pump["metadata"]["omni_type"] == OmniTypes.FILTER else pump["omni_config"]["Type"]

        for speed in OMNI_SPEED_FRIENDLY_NAMES:
            _LOGGER.debug(
                "Configuring button for pump with ID: %s, Name: %s, Speed: %s",
                pump["metadata"]["system_id"],
                pump["metadata"]["name"],
                speed,
            )
            match pump_type:
                case OmniModels.VARIABLE_SPEED_PUMP:
                    entities.append(OmniLogicPumpButtonEntity(coordinator=coordinator, context=system_id, speed=speed))
                case OmniModels.VARIABLE_SPEED_FILTER:
                    entities.append(OmniLogicFilterButtonEntity(coordinator=coordinator, context=system_id, speed=speed))

    async_add_entities(entities)


class OmniLogicButtonEntity(OmniLogicEntity, ButtonEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context, name=None) -> None:
        """Pass coordinator to CoordinatorEntity."""
        button_data = coordinator.data[context]
        name = button_data["metadata"]["name"] if name is None else name
        super().__init__(
            coordinator,
            context=context,
            name=name,
            # The system_id is used for the entity unique_id, the filters system_id is already used for the filter switch
            # so we can't use it directly for these buttons.
            system_id=context,
            bow_id=button_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.omni_type = button_data["metadata"]["omni_type"]


class OmniLogicPumpButtonEntity(OmniLogicButtonEntity):
    # button_data['metadata']['name']} {OMNI_SPEED_FRIENDLY_NAMES[speed]}",

    def __init__(self, coordinator, context, speed) -> None:
        button_data = coordinator.data[context]
        super().__init__(
            coordinator,
            context,
            name=f"{button_data['metadata']['name']} {OMNI_SPEED_FRIENDLY_NAMES[speed]}",
        )
        self.speed = button_data["omni_config"][speed]
        self.telem_key_speed = "@pumpSpeed"
        self.telem_key_state = "@pumpState"

    async def async_press(self):
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, self.speed)

        self.set_telemetry({self.telem_key_speed: self.speed, self.telem_key_state: 1})


class OmniLogicFilterButtonEntity(OmniLogicPumpButtonEntity):
    def __init__(self, coordinator, context, speed) -> None:
        super().__init__(coordinator, context, speed)
        self.telem_key_speed = "@filterSpeed"
        self.telem_key_state = "@filterState"
