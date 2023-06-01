"""Example integration using DataUpdateCoordinator."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
import logging

import async_timeout
from pyomnilogic_local.api import OmniLogicAPI
from pyomnilogic_local.models.mspconfig import MSPConfig, OmniBase
from pyomnilogic_local.models.telemetry import Telemetry

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL
from .types.entity_index import EntityIndexData

# Import diagnostic data to reproduce issues
SIMULATION = False
if SIMULATION:
    import json

    from .test_diagnostic_data import TEST_DIAGNOSTIC_DATA

_LOGGER = logging.getLogger(__name__)


def device_walk(base: OmniBase) -> Iterable[OmniBase]:
    for _key, value in base:
        if isinstance(value, OmniBase):
            if hasattr(value, "system_id"):
                yield value.without_subdevices()
                yield from device_walk(value)
        if isinstance(value, list):
            for device in [d for d in value if hasattr(d, "system_id")]:
                yield device.without_subdevices()
                yield from device_walk(device)


class OmniLogicCoordinator(DataUpdateCoordinator):
    """Hayward OmniLogic API coordinator."""

    msp_config_xml: str
    msp_config: MSPConfig
    telemetry_xml: str
    telemetry: Telemetry
    data: dict[int, EntityIndexData]

    def __init__(self, hass: HomeAssistant, omni_api: OmniLogicAPI) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="OmniLogic",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )
        self.omni_api = omni_api

    async def _async_update_data(self) -> dict[int, EntityIndexData]:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(30):

                if SIMULATION:
                    _LOGGER.debug("Simulating Omni MSPConfig and Telemetry")
                    test_data = json.loads(TEST_DIAGNOSTIC_DATA.replace(r"\"", r"'"))
                    self.msp_config = MSPConfig.load_xml(test_data["data"]["msp_config"])
                    self.telemetry = Telemetry.load_xml(test_data["data"]["telemetry"])

                else:
                    # Initially we only pulled the msp_config at integration startup as it rarely changes
                    # Then we learned that heater set points (which can change often enough) are stored
                    # within the MSP Config, not the telemetry, so now we pull the msp_config on every update
                    _LOGGER.debug("Fetching OmniLogic MSPConfig")
                    # we postprocess the XML to convert hyphens to underscores to simplify typing with TypedDict later
                    # and attempt to convert values to int to make equality comparisons easier without having to constantly int() everything
                    self.msp_config_xml = await self.omni_api.async_get_config(raw=True)
                    self.msp_config = MSPConfig.load_xml(self.msp_config_xml)

                    _LOGGER.debug("Fetching OmniLogic Telemetry")
                    # We postprocess the XML to convert hyphens to underscores to simplify typing with TypedDict later
                    # and attempt to convert values to int to make equality comparisons easier without having to constantly int() everything
                    self.telemetry_xml = await self.omni_api.async_get_telemetry(raw=True)
                    self.telemetry = Telemetry.load_xml(self.telemetry_xml)

                entity_index: dict[int, EntityIndexData] = {}
                for device in device_walk(self.msp_config):
                    entity_index[device.system_id] = EntityIndexData(device, self.telemetry.get_telem_by_systemid(device.system_id))

                return entity_index
        except TimeoutError as exc:
            raise UpdateFailed("Error communicating with API") from exc
