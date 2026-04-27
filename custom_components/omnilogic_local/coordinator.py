"""Example integration using DataUpdateCoordinator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import SCAN_INTERVAL, UPDATE_DELAY_SECONDS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pyomnilogic_local import OmniLogic

_LOGGER = logging.getLogger(__name__)


class OmniLogicCoordinator(DataUpdateCoordinator[None]):
    """Hayward OmniLogic API coordinator."""

    omni: OmniLogic
    # The underlying library stores all of the data and abstracts it via an access layer
    # We don't need to store the data inside of the coordinator
    data: None

    failure_counts: dict[str, int] = {}

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
        try:
            # This ensures that telemetry is updated on every refresh
            # The MSP Config will be refreshed if the stored config checksum doesn't match the
            # config checksum in the telemetry.
            await self.omni.refresh(force_telemetry=True)
        except Exception as err:
            err_name = type(err).__name__
            self.failure_counts[err_name] = self.failure_counts.get(err_name, 0) + 1
            raise UpdateFailed("Failed to update data from OmniLogic") from err

    def do_next_refresh_after(self, delay: float = UPDATE_DELAY_SECONDS) -> None:
        """Delay the next refresh by a given number of seconds."""

        _LOGGER.debug("Performing next refresh in %s seconds", delay)

        self._retry_after = delay
        self._schedule_refresh()
