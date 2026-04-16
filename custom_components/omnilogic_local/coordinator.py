"""Example integration using DataUpdateCoordinator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import SCAN_INTERVAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pyomnilogic_local import OmniLogic


# Import diagnostic data to reproduce issues
SIMULATION = False
if SIMULATION:
    # This line is only used during development when simulating a pool with diagnostic data
    # Disable the pylint and mypy alerts that don't like it when this variable isn't defined
    pass

_LOGGER = logging.getLogger(__name__)


class OmniLogicCoordinator(DataUpdateCoordinator[None]):
    """Hayward OmniLogic API coordinator."""

    omni: OmniLogic
    # The underlying library stores all of the data and abstracts it via an access layer
    # We don't need to store the data inside of the coordinator
    data: None

    def __init__(self, hass: HomeAssistant, omni: OmniLogic) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="OmniLogic",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=SCAN_INTERVAL,
        )
        self.omni = omni

    async def _async_update_data(self) -> None:
        """Update data via library."""
        await self.omni.refresh(force=True)
