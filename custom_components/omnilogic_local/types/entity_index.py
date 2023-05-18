from typing import TypedDict

from typing_extensions import NotRequired

from ..const import OmniType
from .mspconfig import MSPBackyardT, MSPBodyOfWaterT, MSPTypeT
from .telemetry import TelemetryBackyardT, TelemetryBodyOfWaterT, TelemetryTypeT


class EntityMetadataT(TypedDict):
    name: str
    hass_type: str
    omni_type: OmniType
    bow_id: NotRequired[int]
    system_id: int


class EntityDataT(TypedDict):
    metadata: EntityMetadataT
    omni_config: MSPTypeT
    omni_telemetry: TelemetryTypeT


class EntityDataBackyardT(TypedDict):
    metadata: EntityMetadataT
    omni_config: MSPBackyardT
    omni_telemetry: TelemetryBackyardT


class EntityDataBodyOfWaterT(TypedDict):
    metadata: EntityMetadataT
    omni_config: MSPBodyOfWaterT
    omni_telemetry: TelemetryBodyOfWaterT


EntityIndexT = dict[int, EntityDataT]

EntityIndexTypeT = EntityDataBackyardT | EntityDataBodyOfWaterT

OMNI_TYPE_TO_ENTITY_TYPE: dict[OmniType, type[EntityIndexTypeT]] = {
    OmniType.BACKYARD: EntityDataBackyardT,
    OmniType.BOW: EntityDataBodyOfWaterT,
    OmniType.BOW_MSP: EntityDataBodyOfWaterT,
}
