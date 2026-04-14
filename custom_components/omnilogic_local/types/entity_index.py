from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from pyomnilogic_local.models.mspconfig import (
    MSPCSAD,
    MSPBackyard,
    MSPBoW,
    MSPChlorinator,
    MSPChlorinatorEquip,
    MSPColorLogicLight,
    MSPFilter,
    MSPHeaterEquip,
    MSPPump,
    MSPRelay,
    MSPSchedule,
    MSPSensor,
    MSPVirtualHeater,
)
from pyomnilogic_local.models.telemetry import (
    TelemetryBackyard,
    TelemetryBoW,
    TelemetryChlorinator,
    TelemetryColorLogicLight,
    TelemetryCSAD,
    TelemetryFilter,
    TelemetryGroup,
    TelemetryHeater,
    TelemetryPump,
    TelemetryRelay,
    TelemetryValveActuator,
    TelemetryVirtualHeater,
)


@dataclass
class EntityIndexData:
    msp_config: (
        MSPSchedule
        | MSPBackyard
        | MSPBoW
        | MSPVirtualHeater
        | MSPHeaterEquip
        | MSPRelay
        | MSPFilter
        | MSPSensor
        | MSPColorLogicLight
        | MSPChlorinator
        | MSPChlorinatorEquip
        | MSPCSAD
    )
    telemetry: (
        TelemetryBackyard
        | TelemetryBoW
        | TelemetryChlorinator
        | TelemetryColorLogicLight
        | TelemetryFilter
        | TelemetryGroup
        | TelemetryHeater
        | TelemetryPump
        | TelemetryRelay
        | TelemetryValveActuator
        | TelemetryVirtualHeater
        | TelemetryCSAD
    )


EntityIndexT = dict[int, EntityIndexData]


class EntityIndexBackyard:
    msp_config: MSPBackyard
    telemetry: TelemetryBackyard


class EntityIndexBodyOfWater:
    msp_config: MSPBoW
    telemetry: TelemetryBoW


class EntityIndexColorLogicLight:
    msp_config: MSPColorLogicLight
    telemetry: TelemetryColorLogicLight


class EntityIndexFilter:
    msp_config: MSPFilter
    telemetry: TelemetryFilter


class EntityIndexHeater:
    msp_config: MSPVirtualHeater
    telemetry: TelemetryVirtualHeater


class EntityIndexHeaterEquip:
    msp_config: MSPHeaterEquip
    telemetry: TelemetryHeater


class EntityIndexChlorinator:
    msp_config: MSPChlorinator
    telemetry: TelemetryChlorinator


class EntityIndexCSAD:
    msp_config: MSPCSAD
    telemetry: TelemetryCSAD


class EntityIndexChlorinatorEquip:
    msp_config: MSPChlorinatorEquip
    telemetry: TelemetryChlorinator


class EntityIndexPump:
    msp_config: MSPPump
    telemetry: TelemetryPump


class EntityIndexRelay:
    msp_config: MSPRelay
    telemetry: TelemetryRelay


class EntityIndexSensor:
    msp_config: MSPSensor
    telemetry: None


class EntityIndexValveActuator:
    msp_config: MSPRelay
    telemetry: TelemetryValveActuator


EntityIndexTypeVar = TypeVar(
    "EntityIndexTypeVar",
    EntityIndexBackyard,
    EntityIndexBodyOfWater,
    EntityIndexColorLogicLight,
    EntityIndexChlorinator,
    EntityIndexChlorinatorEquip,
    EntityIndexCSAD,
    EntityIndexFilter,
    EntityIndexHeater,
    EntityIndexHeaterEquip,
    EntityIndexPump,
    EntityIndexRelay,
    EntityIndexSensor,
    EntityIndexValveActuator,
)
