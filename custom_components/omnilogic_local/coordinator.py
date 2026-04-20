"""Example integration using DataUpdateCoordinator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pyomnilogic_local.api.exceptions import OmniFragmentationError, OmniMessageFormatError, OmniTimeoutError, OmniValidationError

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
            await self.omni.refresh(force=True)
        except OmniFragmentationError as err:
            self.failure_counts["connection"] = self.failure_counts.get("connection", 0) + 1
            raise UpdateFailed("Failure to fragment or reassemble data to/from OmniLogic") from err
        except OmniMessageFormatError as err:
            self.failure_counts["format"] = self.failure_counts.get("format", 0) + 1
            raise UpdateFailed("Received a malformed or invalid message from OmniLogic") from err
        except OmniTimeoutError as err:
            self.failure_counts["timeout"] = self.failure_counts.get("timeout", 0) + 1
            raise UpdateFailed("Timeout occurred while fetching OmniLogic data") from err
        except OmniValidationError as err:
            self.failure_counts["validation"] = self.failure_counts.get("validation", 0) + 1
            raise UpdateFailed("Received invalid data from OmniLogic") from err
