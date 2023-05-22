from __future__ import annotations

from collections.abc import Generator
import logging
from typing import TypeVar

from .const import KEY_TELEMETRY_SYSTEM_ID, OMNI_TYPES, OmniType
from .entity import OmniLogicEntity
from .errors import UnknownDevice
from .types.entity_index import EntityIndexT
from .types.telemetry import TelemetryStatusT, TelemetryType

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def one_or_many(obj: T | list[T]) -> Generator[T, None, None]:
    if isinstance(obj, list):
        yield from obj
    else:
        yield obj


def get_telemetry_by_systemid(telemetry: TelemetryStatusT, system_id: int) -> TelemetryType | None:
    for omni_type, omni_data in telemetry.items():
        if omni_type in OMNI_TYPES:
            for entity in one_or_many(omni_data):
                if entity[KEY_TELEMETRY_SYSTEM_ID] == system_id:
                    return entity
    return None


def get_config_by_systemid(mspconfig: dict[str, str], system_id: int) -> dict[str, str]:
    for omni_type, items in mspconfig["Backyard"].items():
        if omni_type in OMNI_TYPES:
            for item in one_or_many(items):
                if item["System-Id"] == system_id:
                    return item

    for bow in one_or_many(mspconfig["Backyard"]["Body-of-water"]):
        for omni_type, items in bow.items():
            if omni_type in OMNI_TYPES:
                for item in one_or_many(items):
                    if item["System-Id"] == system_id:
                        item["Body-of-water-Id"] = bow["System-Id"]
                        return item

    raise UnknownDevice("device config not found")


def get_entities_of_hass_type(entities: EntityIndexT, hass_type: str) -> dict[int, OmniLogicEntity]:
    found = {}
    for system_id, entity in entities.items():
        if entity["metadata"]["hass_type"] == hass_type:
            found[system_id] = entity
    return found


def get_entities_of_omni_types(entities: EntityIndexT, omni_types: list[OmniType]) -> dict[int, OmniLogicEntity]:
    found = {}
    for system_id, entity in entities.items():
        if entity["metadata"]["omni_type"] in omni_types:
            found[system_id] = entity
    return found


def get_omni_model(data: dict[str, str]) -> str:
    match data["metadata"]["omni_type"]:
        case OmniType.FILTER:
            return data["config"]["Filter_Type"]
        case _:
            return data["config"]["Type"]
