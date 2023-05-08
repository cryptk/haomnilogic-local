"""Example integration using DataUpdateCoordinator."""
from __future__ import annotations

import logging
from datetime import timedelta
import json

import async_timeout
import xmltodict
from pyomnilogic_local import OmniLogicAPI

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)

from .const import DEFAULT_POLL_INTERVAL, OMNI_DEVICE_TYPES, OMNI_TO_HASS_TYPES, KEY_MSP_SYSTEM_ID
from .utils import get_telemetry_by_systemid, get_config_by_systemid, get_entities_of_type, one_or_many

_LOGGER = logging.getLogger(__name__)

# This function filters out any entities that may be nested under the passes in entity
def get_single_entity_config(raw_data: dict) -> dict:
    return {key: value for key, value in raw_data.items() if not key in OMNI_DEVICE_TYPES}

def build_entity_item(omni_entity_type: str, entity_config: dict, bow_id: int | None = None):

    for entity in one_or_many(entity_config):
        # Filter the data down to only this one entity and not any nested entities
        config = get_single_entity_config(entity)
        # config = get_single_entity_config({omni_device_type: device_data})
        # The returned entity had no system ID, which means we cannot address it via the API
        if not config:
            continue

        yield {
                'metadata': {
                    'name': config.get('Name', omni_entity_type),
                    'hass_type': OMNI_TO_HASS_TYPES[omni_entity_type],
                    'omni_type': omni_entity_type,
                    'bow_id': bow_id,
                    'system_id': int(config[KEY_MSP_SYSTEM_ID]),
                },
                'omni_config': config
            }

def build_entity_index(data: dict[str, str]) -> dict[int,dict[str,str]]:
    entity_index = {}

    for tier in [data["MSPConfig"], data["MSPConfig"]["Backyard"], data["MSPConfig"]["Backyard"]["Body-of-water"]]:
        for item in one_or_many(tier):
            bow_id = int(item[KEY_MSP_SYSTEM_ID]) if item.get('Type') == "BOW_POOL" else None
            for omni_entity_type, entity_data in tier.items():
                if omni_entity_type not in OMNI_DEVICE_TYPES:
                    continue
                for entity in build_entity_item(omni_entity_type, entity_data, bow_id):
                    entity['metadata']['bow_id'] = bow_id
                    entity['omni_telemetry'] = get_telemetry_by_systemid(data['STATUS'], entity['metadata']['system_id'])
                    entity_index[int(entity['metadata']['system_id'])] = entity
    
    return entity_index


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

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                # listening_idx = set(self.async_contexts())

                # The MSPConfig only changes if there are hardware/configuration changes to the Omni
                # We don't need to pull this every time, currently we only pull it one time when the integration
                # is loaded.
                if self._config is None:
                    _LOGGER.debug("Fetching OmniLogic MSPConfig")
                    self._config = await self.omni_api.asyncGetConfig()

                _LOGGER.debug("Fetching OmniLogic Telemetry")
                telemetry = await self.omni_api.asyncGetTelemetry()

                omnilogic_data = xmltodict.parse(self._config) | xmltodict.parse(telemetry)

                entity_index = build_entity_index(omnilogic_data)

                return entity_index
        except TimeoutError as exc:
            raise UpdateFailed("Error communicating with API") from exc
