from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, KEY_COORDINATOR
from .types import OmniLogicEntity
from .utils import get_entities_of_omni_type

_LOGGER = logging.getLogger(__name__)

OMNI_SPEED_FRIENDLY_NAMES = {
    "Vsp-Low-Pump-Speed": "Low Speed",
    "Vsp-Medium-Pump-Speed": "Medium Speed",
    "Vsp-High-Pump-Speed": "High Speed",
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_filters = get_entities_of_omni_type(coordinator.data, "Filter")

    entities = []
    for system_id, filter_pump in all_filters.items():
        if filter_pump["omni_config"]["Filter-Type"] == "FMT_VARIABLE_SPEED_PUMP":
            for speed in OMNI_SPEED_FRIENDLY_NAMES:
                if filter_pump["omni_config"].get(speed):
                    _LOGGER.debug(
                        "Configuring button for filter with ID: %s, Name: %s, Speed: %s",
                        filter_pump["metadata"]["system_id"],
                        filter_pump["metadata"]["name"],
                        speed,
                    )
                    entities.append(
                        OmniLogicButtonEntity(
                            coordinator=coordinator, context=system_id, speed=speed
                        )
                    )

    async_add_entities(entities)


class OmniLogicButtonEntity(OmniLogicEntity, ButtonEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, context, speed) -> None:
        """Pass coordinator to CoordinatorEntity."""
        filter_data = coordinator.data[context]
        super().__init__(
            coordinator,
            context=context,
            name=f"{filter_data['metadata']['name']} {OMNI_SPEED_FRIENDLY_NAMES[speed]}",
            # The system_id is used for the entity unique_id, the filters system_id is already used for the filter switch
            # so we can't use it directly for these buttons.
            system_id=f"{filter_data['metadata']['system_id']}_button_{speed}",
            bow_id=filter_data["metadata"]["bow_id"],
            extra_attributes=None,
        )
        self.filter_system_id = filter_data["metadata"]["system_id"]
        self.omni_type = filter_data["metadata"]["omni_type"]
        self.speed = int(filter_data["omni_config"][speed])

    async def async_press(self) -> None:
        await self.coordinator.omni_api.async_set_equipment(
            self.bow_id, self.filter_system_id, self.speed
        )
        self.coordinator.data[self.filter_system_id]["omni_telemetry"][
            "@filterSpeed"
        ] = self.speed
        self.coordinator.data[self.filter_system_id]["omni_telemetry"][
            "@filterState"
        ] = "1"
        self.coordinator.async_set_updated_data(self.coordinator.data)
