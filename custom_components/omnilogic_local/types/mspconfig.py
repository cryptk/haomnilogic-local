from typing import Literal, TypedDict

from typing_extensions import NotRequired

from ..const import OmniColorLogicLightType, OmniModel, OmniRelayFunction, OmniType


class MSPHeaterEquipT(TypedDict):
    System_Id: int
    Name: str
    Enabled: Literal["yes", "no"]
    Min_Speed_For_Operation: int
    Sensor_System_Id: int


class MSPHeaterT(TypedDict):
    System_Id: int
    Enabled: Literal["yes", "no"]
    Current_Set_Point: int
    SolarSetPoint: int
    Min_Settable_Water_Temp: int
    Max_Settable_Water_Temp: int
    Operation: list[dict[Literal[OmniType.HEATER_EQUIP], MSPHeaterEquipT]]


class MSPColorLogicLightT(TypedDict):
    System_Id: int
    Name: str
    Type: Literal[OmniColorLogicLightType.UCL, OmniColorLogicLightType.FOUR_ZERO, OmniColorLogicLightType.TWO_FIVE]
    V2_Active: Literal["yes", "no"]


class MSPRelayT(TypedDict):
    System_Id: int
    Name: str
    Type: Literal[OmniModel.RELAY_LOW_VOLTAGE, OmniModel.RELAY_HIGH_VOLTAGE, OmniModel.RELAY_VALVE_ACTUATOR]
    Function: Literal[OmniRelayFunction.FOUNTAIN, OmniRelayFunction.WATERFALL, OmniRelayFunction.WATER_FEATURE]


class MSPFilterT(TypedDict):
    System_Id: int
    Name: str
    Filter_Type: Literal[OmniModel.SINGLE_SPEED_FILTER, OmniModel.DUAL_SPEED_FILTER, OmniModel.VARIABLE_SPEED_FILTER]
    Max_Pump_Speed: int
    Min_Pump_Speed: int
    Max_Pump_RPM: int
    Min_Pump_RPM: int
    Vsp_Low_Pump_Speed: int
    Vsp_Medium_Pump_Speed: int
    Vsp_High_Pump_Speed: int
    Vsp_Custom_Pump_Speed: int


class MSPSensorT(TypedDict):
    System_Id: int
    Name: str
    Type: Literal[OmniModel.SENSOR_AIR, OmniModel.SENSOR_FLOW, OmniModel.SENSOR_SOLAR, OmniModel.SENSOR_WATER]
    Units: Literal["UNITS_FAHRENHEIT", "UNITS_CELSIUS"]


class MSPBodyOfWaterT(TypedDict):
    System_Id: int
    Name: str
    Type: Literal[OmniModel.BOW_POOL, OmniModel.BOW_SPA]
    Filter: NotRequired[list[MSPFilterT]]
    Relay: NotRequired[list[MSPRelayT]]
    ColorLogic_Light: NotRequired[list[MSPColorLogicLightT]]
    Sensor: NotRequired[list[MSPSensorT]]
    Heater: NotRequired[MSPHeaterT]


class MSPBackyardT(TypedDict):
    System_Id: int
    Name: str
    Sensor: NotRequired[list[MSPSensorT]]
    Body_of_water: NotRequired[list[MSPBodyOfWaterT]]


class MSPSystemT(TypedDict):
    Msp_Vsp_Speed_Format: Literal["Percent", "RPM"]
    Units: Literal["Standard", "Metric"]
    Msp_Chlor_Display: Literal["Salt", "Minerals"]


class MSPDataT(TypedDict):
    System: MSPSystemT
    Backyard: MSPBackyardT
    CHECKSUM: int


class MSPConfigT(TypedDict):
    MSPConfig: MSPDataT


MSPTypeT = (
    MSPSystemT | MSPBackyardT | MSPBodyOfWaterT | MSPFilterT | MSPRelayT | MSPColorLogicLightT | MSPSensorT | MSPHeaterT | MSPHeaterEquipT
)

OMNI_TYPE_TO_MSP_TYPE: dict[OmniType, type[MSPTypeT]] = {
    OmniType.BACKYARD: MSPBackyardT,
    OmniType.BOW: MSPBodyOfWaterT,
    OmniType.BOW_MSP: MSPBodyOfWaterT,
}
