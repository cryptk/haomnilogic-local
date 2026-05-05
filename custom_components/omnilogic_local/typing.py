from pyomnilogic_local import (
    CSAD,
    Backyard,
    Bow,
    Chlorinator,
    ChlorinatorEquipment,
    ColorLogicLight,
    CSADEquipment,
    Filter,
    Group,
    Heater,
    HeaterEquipment,
    Pump,
    Relay,
    Schedule,
    Sensor,
)

type OmniLogicEquipment = (
    CSAD
    | Backyard
    | Bow
    | Chlorinator
    | ChlorinatorEquipment
    | ColorLogicLight
    | CSADEquipment
    | Filter
    | Group
    | Heater
    | HeaterEquipment
    | Pump
    | Relay
    | Schedule
    | Sensor
)
