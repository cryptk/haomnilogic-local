from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import OMNI_TO_HASS_TYPES

if TYPE_CHECKING:
    from pyomnilogic_local.omnitypes import OmniType

    from .types.entity_index import EntityIndexT

_LOGGER = logging.getLogger(__name__)


def get_entities_of_hass_type(entities: EntityIndexT, hass_type: str) -> EntityIndexT:
    found = {}
    for system_id, entity in entities.items():
        if OMNI_TO_HASS_TYPES[entity.msp_config.omni_type] == hass_type:
            found[system_id] = entity
    return found


def get_entities_of_omni_types(entities: EntityIndexT, omni_types: list[OmniType]) -> EntityIndexT:
    found = {}
    for system_id, entity in entities.items():
        if entity.msp_config.omni_type in omni_types:
            found[system_id] = entity
    return found
