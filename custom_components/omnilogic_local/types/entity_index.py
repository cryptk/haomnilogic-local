from __future__ import annotations

from typing import TypeAlias, TypedDict, TypeVar

from typing_extensions import NotRequired

from ..const import OmniType
from .mspconfig import (
    MSPBackyardT,
    MSPBodyOfWaterT,
    MSPColorLogicLightT,
    MSPFilterT,
    MSPHeaterEquipT,
    MSPHeaterT,
    MSPPumpT,
    MSPRelayT,
    MSPSensorT,
)
from .telemetry import (
    TelemetryBackyardT,
    TelemetryBodyOfWaterT,
    TelemetryColorLogicLightT,
    TelemetryFilterT,
    TelemetryHeaterT,
    TelemetryPumpT,
    TelemetryRelayT,
    TelemetryValveActuatorT,
    TelemetryVirtualHeaterT,
)


class EntityMetadataT(TypedDict):
    name: str
    hass_type: str
    omni_type: OmniType
    bow_id: NotRequired[int]
    system_id: int


class EntityDataBackyardT(TypedDict):
    metadata: EntityMetadataT
    config: MSPBackyardT
    telemetry: TelemetryBackyardT


class EntityDataBodyOfWaterT(TypedDict):
    metadata: EntityMetadataT
    config: MSPBodyOfWaterT
    telemetry: TelemetryBodyOfWaterT


class EntityDataColorLogicLightT(TypedDict):
    metadata: EntityMetadataT
    config: MSPColorLogicLightT
    telemetry: TelemetryColorLogicLightT


class EntityDataFilterT(TypedDict):
    metadata: EntityMetadataT
    config: MSPFilterT
    telemetry: TelemetryFilterT


class EntityDataHeaterT(TypedDict):
    metadata: EntityMetadataT
    config: MSPHeaterT
    telemetry: TelemetryVirtualHeaterT


class EntityDataHeaterEquipT(TypedDict):
    metadata: EntityMetadataT
    config: MSPHeaterEquipT
    telemetry: TelemetryHeaterT


class EntityDataPumpT(TypedDict):
    metadata: EntityMetadataT
    config: MSPPumpT
    telemetry: TelemetryPumpT


class EntityDataRelayT(TypedDict):
    metadata: EntityMetadataT
    config: MSPRelayT
    telemetry: TelemetryRelayT


class EntityDataSensorT(TypedDict):
    metadata: EntityMetadataT
    config: MSPSensorT
    telemetry: None


class EntityDataValveActuatorT(TypedDict):
    metadata: EntityMetadataT
    config: MSPRelayT
    telemetry: TelemetryValveActuatorT


EntityIndexType: TypeAlias = (
    EntityDataBackyardT
    | EntityDataBodyOfWaterT
    | EntityDataColorLogicLightT
    | EntityDataFilterT
    | EntityDataHeaterT
    | EntityDataHeaterEquipT
    | EntityDataPumpT
    | EntityDataRelayT
    | EntityDataSensorT
    | EntityDataValveActuatorT
)

EntityIndexTypeVar = TypeVar(
    "EntityIndexTypeVar",
    EntityDataBackyardT,
    EntityDataBodyOfWaterT,
    EntityDataColorLogicLightT,
    EntityDataFilterT,
    EntityDataHeaterT,
    EntityDataHeaterEquipT,
    EntityDataPumpT,
    EntityDataRelayT,
    EntityDataSensorT,
    EntityDataValveActuatorT,
)

EntityIndexT = dict[int, EntityIndexType]


# OMNI_TYPE_TO_ENTITY_TYPE: dict[OmniType, type[EntityIndexTypeT]] = {
#     OmniType.BACKYARD: EntityDataBackyardT,
#     OmniType.BOW: EntityDataBodyOfWaterT,
#     OmniType.BOW_MSP: EntityDataBodyOfWaterT,
# }
