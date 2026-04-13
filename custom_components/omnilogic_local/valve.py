from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.valve import ValveEntity
from pyomnilogic_local.omnitypes import RelayFunction, RelayType
from pyomnilogic_local.relay import Relay

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the valve platform."""
    entities: list[ValveEntity] = []
    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    # Add valve actuator relays
    for _, system_id, relay in coordinator.omni.all_relays.items():
        # Only add valve actuators - standard relays belong in switch platform
        if relay.relay_type == RelayType.VALVE_ACTUATOR:
            _LOGGER.debug(
                "Configuring valve for valve actuator with ID: %s, Name: %s",
                system_id,
                relay.name,
            )
            entities.append(OmniLogicValveEntity(coordinator=coordinator, equipment=relay))

    async_add_entities(entities)


class OmniLogicValveEntity(OmniLogicEntity[Relay], ValveEntity):
    """Valve entity for valve actuator relays."""

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Relay) -> None:
        super().__init__(coordinator, equipment)

    @property
    def reports_position(self) -> bool:
        """Return False as valve actuators are binary (open/closed) with no position reporting."""
        return False

    @property
    def is_closed(self) -> bool | None:
        """Return True if the valve is closed."""
        return not self.equipment.is_on

    @property
    def icon(self) -> str | None:
        """Return icon based on valve function."""
        match self.equipment.function:
            case RelayFunction.WATERFALL:
                return "mdi:waterfall"
            case RelayFunction.FOUNTAIN:
                return "mdi:fountain"
            case RelayFunction.WATER_FEATURE:
                return "mdi:fountain"
            case RelayFunction.WATER_SLIDE:
                return "mdi:slide"
            case _:
                return "mdi:valve-open" if not self.is_closed else "mdi:valve-closed"

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        """Return extra state attributes."""
        return super().extra_state_attributes | {
            "why_on": self.equipment.why_on,
        }

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.debug("opening valve ID: %s", self.system_id)
        await self.equipment.turn_on()

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.debug("closing valve ID: %s", self.system_id)
        await self.equipment.turn_off()
