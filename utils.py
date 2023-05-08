from __future__ import annotations

import logging

from .const import DEVICE_TYPES
from .errors import UnknownDevice
from .types import OmniLogicEntity

_LOGGER = logging.getLogger(__name__)


def one_or_many(obj):
    if isinstance(obj, list):
        yield from obj
    else:
        yield obj


def get_config_by_systemid(mspconfig: dict[str, str], system_id: int) -> dict[str, str]:
    for ommni_type, items in mspconfig["Backyard"].items():
        if ommni_type in DEVICE_TYPES:
            for item in one_or_many(items):
                if item["System-Id"] == system_id:
                    return item

    for bow in one_or_many(mspconfig["Backyard"]["Body-of-water"]):
        for ommni_type, items in bow.items():
            if ommni_type in DEVICE_TYPES:
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
