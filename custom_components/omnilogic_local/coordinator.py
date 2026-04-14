"""Example integration using DataUpdateCoordinator."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pyomnilogic_local.models.mspconfig import MSPConfig, OmniBase

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.core import HomeAssistant
    from pyomnilogic_local import OmniLogic


# Import diagnostic data to reproduce issues
SIMULATION = False
if SIMULATION:
    # This line is only used during development when simulating a pool with diagnostic data
    # Disable the pylint and mypy alerts that don't like it when this variable isn't defined
    pass

_LOGGER = logging.getLogger(__name__)


def device_walk(base: OmniBase | MSPConfig) -> Iterable[OmniBase]:
    for _key, value in base:
        if isinstance(value, OmniBase) and hasattr(value, "system_id"):
            yield value.without_subdevices()
            yield from device_walk(value)
        if isinstance(value, list):
            for device in [d for d in value if hasattr(d, "system_id")]:
                yield device.without_subdevices()
                yield from device_walk(device)


class OmniLogicCoordinator(DataUpdateCoordinator[None]):
    """Hayward OmniLogic API coordinator."""

    omni: OmniLogic
    # The underlying library stores all of the data and abstracts it via an access layer
    # We don't need to store the data inside of the
    data: None

    def __init__(self, hass: HomeAssistant, omni: OmniLogic, scan_interval: int) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="OmniLogic",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=scan_interval),
        )
        self.omni = omni

    async def _async_update_data(self) -> None:
        """Update data via library."""
        await self.omni.refresh(force=True)
