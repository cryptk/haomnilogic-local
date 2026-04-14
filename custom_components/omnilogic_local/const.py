"""Constants for the OmniLogic Local integration."""

from typing import Final

from pyomnilogic_local.omnitypes import OmniType

DOMAIN: Final[str] = "omnilogic_local"
KEY_COORDINATOR: Final[str] = "coordinator"

DEFAULT_SCAN_INTERVAL: Final[int] = 10
MIN_SCAN_INTERVAL: Final[int] = 5
UPDATE_DELAY_SECONDS: Final[float] = 1.5

# According to Hayward docs, the backyard always has a system id of 0
BACKYARD_SYSTEM_ID: Final[int] = 0

MANUFACTURER: Final[str] = "Hayward"

PUMP_SPEEDS: Final[list[str]] = ["low", "medium", "high"]

OMNI_TO_HASS_TYPES: dict[str, str] = {
    OmniType.BACKYARD: "device",
    OmniType.BOW: "device",
    OmniType.BOW_MSP: "device",
    OmniType.CHLORINATOR: "switch",
    OmniType.CHLORINATOR_EQUIP: "switch",
    OmniType.CSAD: "sensor",
    OmniType.CL_LIGHT: "light",
    OmniType.FILTER: "switch",
    OmniType.HEATER: "water_heater",
    OmniType.HEATER_EQUIP: "water_heater",
    OmniType.PUMP: "switch",
    OmniType.RELAY: "switch",
    OmniType.SENSOR: "sensor",
    OmniType.VALVE_ACTUATOR: "switch",
    OmniType.VIRT_HEATER: "water_heater",
}
