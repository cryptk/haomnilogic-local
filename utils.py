from __future__ import annotations

import logging

from .const import KEY_TELEMETRY_SYSTEM_ID, OMNI_DEVICE_TYPES
from .errors import UnknownDevice
from .types import OmniLogicEntity

_LOGGER = logging.getLogger(__name__)


def one_or_many(obj):
    if isinstance(obj, list):
        yield from obj
    else:
        yield obj


def get_telemetry_by_systemid(telemetry: dict, system_id: int) -> dict[str, str]:
    for omni_type, omni_data in telemetry.items():
        if omni_type in OMNI_DEVICE_TYPES:
            for entity in one_or_many(omni_data):
                # _LOGGER.debug("entity: %s", entity)
                if int(entity[KEY_TELEMETRY_SYSTEM_ID]) == system_id:
                    return entity


def get_config_by_systemid(mspconfig: dict[str, str], system_id: int) -> dict[str, str]:
    for omni_type, items in mspconfig["Backyard"].items():
        if omni_type in OMNI_DEVICE_TYPES:
            for item in one_or_many(items):
                if item["System-Id"] == system_id:
                    return item

    for bow in one_or_many(mspconfig["Backyard"]["Body-of-water"]):
        for omni_type, items in bow.items():
            if omni_type in OMNI_DEVICE_TYPES:
                for item in one_or_many(items):
                    if item["System-Id"] == system_id:
                        item["Body-of-water-Id"] = bow["System-Id"]
                        return item

    raise UnknownDevice("device config not found")


def get_entities_of_type(
    entities: dict[int, OmniLogicEntity], hass_type: str
) -> dict[int, OmniLogicEntity]:
    found = {}
    for system_id, entity in entities.items():
        if entity["metadata"]["hass_type"] == hass_type:
            # _LOGGER.debug(system_id)
            found[int(system_id)] = entity
    # _LOGGER.debug(found)
    return found
