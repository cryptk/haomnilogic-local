"""Example integration using DataUpdateCoordinator."""
from __future__ import annotations

from datetime import timedelta
import logging

import async_timeout
from pyomnilogic_local.api import OmniLogicAPI
import xmltodict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (  # KEY_MSP_BACKYARD,; KEY_MSP_BOW,
    DEFAULT_POLL_INTERVAL,
    KEY_MSP_SYSTEM_ID,
    OMNI_TO_HASS_TYPES,
    OMNI_TYPES,
    OMNI_TYPES_BOW,
    OmniType,
)
from .utils import get_telemetry_by_systemid, one_or_many

# Import diagnostic data to reproduce issues
# import json
# from .test_diagnostic_data import TEST_DIAGNOSTIC_DATA

_LOGGER = logging.getLogger(__name__)


# This function filters out any entities that may be nested under the passes in entity
def get_single_entity_config(raw_data: dict) -> dict:
    return {key: value for key, value in raw_data.items() if key not in OMNI_TYPES}


def build_entity_item(omni_entity_type: str, entity_config: dict, bow_id: int | None = None):
    for entity in one_or_many(entity_config):
        # Filter the data down to only this one entity and not any nested entities
        config = get_single_entity_config(entity)
        # config = get_single_entity_config({omni_device_type: device_data})
        # The returned entity had no system ID, which means we cannot address it via the API
        if not config:
            continue

        # Heaters support "virtual devices" where multiple heaters work in coordination and are controlled
        # by the single "virtual heater" for temperature set points
        if omni_entity_type == "Heater":
            heater_equipment = [entry for entry in entity["Operation"] if OmniType.HEATER_EQUIP in entry][0]
            for heater in one_or_many(heater_equipment[OmniType.HEATER_EQUIP]):
                yield {
                    "metadata": {
                        "name": heater.get("Name", omni_entity_type),
                        "hass_type": OMNI_TO_HASS_TYPES[OmniType.HEATER_EQUIP],
                        "omni_type": OmniType.HEATER_EQUIP.value,
                        "bow_id": bow_id,
                        "system_id": heater[KEY_MSP_SYSTEM_ID],
                    },
                    "omni_config": heater,
                }

        yield {
            "metadata": {
                "name": config.get("Name", omni_entity_type),
                "hass_type": OMNI_TO_HASS_TYPES[omni_entity_type],
                "omni_type": omni_entity_type,
                "bow_id": bow_id,
                "system_id": config[KEY_MSP_SYSTEM_ID],
            },
            "omni_config": config,
        }


def build_entity_index(data: dict[str, str]) -> dict[int, dict[str, str]]:
    entity_index = {}

    for tier in (
        data["MSPConfig"],
        data["MSPConfig"][OmniType.BACKYARD],
        data["MSPConfig"][OmniType.BACKYARD][OmniType.BOW_MSP],
    ):
        for item in one_or_many(tier):
            bow_id = item[KEY_MSP_SYSTEM_ID] if item.get("Type") in OMNI_TYPES_BOW else None
            for omni_entity_type, entity_data in item.items():
                if omni_entity_type not in OMNI_TYPES:
                    continue
                for entity in build_entity_item(omni_entity_type, entity_data, bow_id):
                    entity["metadata"]["bow_id"] = bow_id
                    entity["omni_telemetry"] = get_telemetry_by_systemid(data["STATUS"], entity["metadata"]["system_id"])
                    entity_index[entity["metadata"]["system_id"]] = entity

    return entity_index


def xml_postprocessor(_, key, value):
    """Post process XML to convert hyphens to underscore and attempt to convert values to int."""
    try:
        newkey = key.replace("-", "_")
    except (ValueError, TypeError):
        newkey = key

    try:
        newvalue = int(value)
    except (ValueError, TypeError):
        newvalue = value

    return newkey, newvalue


class OmniLogicCoordinator(DataUpdateCoordinator):
    """Hayward OmniLogic API coordinator."""

    msp_config: dict = None
    telemetry: dict = None

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
                # Initially we only pulled the msp_config at integration startup as it rarely changes
                # Then we learned that heater set points (which can change often enough) are stored
                # within the MSP Config, not the telemetry, so now we pull the msp_config on every update
                _LOGGER.debug("Fetching OmniLogic MSPConfig")
                # we postprocess the XML to convert hyphens to underscores to simplify typing with TypedDict later
                # and attempt to convert values to int to make equality comparisons easier without having to constantly int() everything
                self.msp_config = xmltodict.parse(await self.omni_api.async_get_config(), postprocessor=xml_postprocessor)

                _LOGGER.debug("Fetching OmniLogic Telemetry")
                # We postprocess the XML to convert hyphens to underscores to simplify typing with TypedDict later
                # and attempt to convert values to int to make equality comparisons easier without having to constantly int() everything
                self.telemetry = xmltodict.parse(await self.omni_api.async_get_telemetry(), postprocessor=xml_postprocessor)

                # The below is used if we have a test_diagnostic_data.py populated with a diagnostic data file to reproduce an issue
                # test_data = json.loads(TEST_DIAGNOSTIC_DATA)
                # self.msp_config = test_data["data"]["msp_config"]
                # self.telemetry = test_data["data"]["telemetry"]

                omnilogic_data = self.msp_config | self.telemetry

                entity_index = build_entity_index(omnilogic_data)

                # pprint.pprint(entity_index)

                return entity_index
        except TimeoutError as exc:
            raise UpdateFailed("Error communicating with API") from exc
