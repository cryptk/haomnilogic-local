"""Constants for the OmniLogic Local integration."""
from typing import Final

from pyomnilogic_local.types import OmniType

# from homeassistant.backports.enum import StrEnum

DOMAIN: Final[str] = "omnilogic_local"
KEY_COORDINATOR: Final[str] = "coordinator"
DEFAULT_POLL_INTERVAL: Final[int] = 20

# According to Hayward docs, the backyard always has a system id of 0
BACKYARD_SYSTEM_ID: Final[int] = 0

UNIQUE_ID: Final[str] = "omnilogic"
MANUFACTURER: Final[str] = "Hayward"


OMNI_TO_HASS_TYPES: dict[str, str] = {
    OmniType.BACKYARD: "device",
    OmniType.BOW: "device",
    OmniType.BOW_MSP: "device",
    OmniType.CHLORINATOR: "switch",
    OmniType.CHLORINATOR_EQUIP: "switch",
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
