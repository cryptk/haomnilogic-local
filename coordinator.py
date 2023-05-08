"""Example integration using DataUpdateCoordinator."""
from __future__ import annotations

from datetime import timedelta
import logging

import async_timeout
from pyomnilogic_local import OmniLogicAPI
import xmltodict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL, DEVICE_TYPES, OMNI_TO_HASS_TYPES
from .utils import get_config_by_systemid, one_or_many

_LOGGER = logging.getLogger(__name__)


def build_device_index(data: dict[str, str]) -> dict[int,dict[str,str]]:
    device_index = {}
    for device_type, device_data in data['STATUS'].items():
        if device_type in DEVICE_TYPES:
            for device in one_or_many(device_data):
                config = get_config_by_systemid(data['MSPConfig'], device['@systemId'])
                device_index[int(device['@systemId'])] = {
                    'metadata': {
                        'name': config.get('Name', device_type),
                        'hass_type': OMNI_TO_HASS_TYPES[device_type],
                        'omni_type': device_type,
                        'bow_id': config['Body-of-water-Id'],
                        'system_id': int(device['@systemId']),
                    },
                    'omni_config': config,
                    'omni_telemetry': device
                }

    return device_index

class OmniLogicCoordinator(DataUpdateCoordinator):
    """Hayward OmniLogic API coordinator."""

    _config = None

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

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """

        # Reset the update interval
        self.update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL)

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                # listening_idx = set(self.async_contexts())

                if self._config is None:
                    _LOGGER.debug("Fetching OmniLogic MSPConfig")
                    self._config = await self.omni_api.asyncGetConfig()
                _LOGGER.debug("Fetching OmniLogic Telemetry")
                telemetry = await self.omni_api.asyncGetTelemetry()
                omnilogic_data = xmltodict.parse(self._config) | xmltodict.parse(telemetry)
                # _LOGGER.debug(json.dumps(omnilogic_data, indent=2))
                device_index = build_device_index(omnilogic_data)

                return device_index
        except TimeoutError as exc:
            raise UpdateFailed("Error communicating with API") from exc
