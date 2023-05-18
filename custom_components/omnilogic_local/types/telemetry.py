from typing import TypedDict

from typing_extensions import NotRequired

from ..const import OmniType

TelemetryBackyardT = TypedDict(
    "TelemetryBackyardT",
    {
        "@systemId": int,
        "@airTemp": NotRequired[int],
        "@state": int,
    },
)

TelemetryBodyOfWaterT = TypedDict(
    "TelemetryBodyOfWaterT",
    {
        "@systemId": int,
        "@waterTemp": NotRequired[int],
        "@flow": NotRequired[int],
    },
)

TelemetryFilterT = TypedDict(
    "TelemetryFilterT",
    {"@systemId": int, "@filterState": int, "@filterSpeed": int, "@reportedFilterSpeed": int, "@power": int, "@lastSpeed": int},
)

TelemetryValveActuatorT = TypedDict("TelemetryValveActuatorT", {"@systemId": int, "@valveActuatorState": int, "@whyOn": int})

TelemetryColorLogicLightT = TypedDict(
    "TelemetryColorLogicLightT",
    {"@systemId": int, "@lightState": int, "@currentShow": int, "@speed": int, "@brightness": int, "@specialEffect": int},
)

TelemetryVirtualHeaterT = TypedDict(
    "TelemetryVirtualHeaterT",
    {"@systemId": int, "@Current_Set_Point": int, "@enable": int, "@SolarSetPoint": int, "@Mode": int, "@whyHeaterIsOn": int},
)

TelemetryHeaterT = TypedDict(
    "TelemetryHeaterT",
    {
        "@systemId": int,
        "@heaterState": int,
        "@temp": int,
        "@enable": int,
        "@priority": int,
        "@maintainFor": int,
    },
)

TelemetryGroupT = TypedDict("TelemetryGroupT", {"@systemId": int, "@groupState": int})

TelemetryStatusT = TypedDict(
    "TelemetryStatusT",
    {
        "@version": str,
        "Backyard": TelemetryBackyardT,
        "BodyOfWater": list[TelemetryBodyOfWaterT],
        "Filter": NotRequired[list[TelemetryFilterT]],
        "ValveActuator": NotRequired[list[TelemetryValveActuatorT]],
        "ColorLogic_Light": NotRequired[list[TelemetryColorLogicLightT]],
        "VirtualHeater": NotRequired[TelemetryVirtualHeaterT],
        "Heater": NotRequired[list[TelemetryHeaterT]],
        "Group": NotRequired[list[TelemetryGroupT]],
    },
)


class TelemetryT(TypedDict):
    STATUS: TelemetryStatusT


TelemetryTypeT = (
    TelemetryBackyardT
    | TelemetryBodyOfWaterT
    | TelemetryFilterT
    | TelemetryValveActuatorT
    | TelemetryColorLogicLightT
    | TelemetryVirtualHeaterT
    | TelemetryHeaterT
    | TelemetryGroupT
)
OMNI_TYPE_TO_TELEMETRY_TYPE: dict[OmniType, type[TelemetryTypeT]] = {
    OmniType.BACKYARD: TelemetryBackyardT,
    OmniType.BOW: TelemetryBodyOfWaterT,
    OmniType.BOW_MSP: TelemetryBodyOfWaterT,
}
