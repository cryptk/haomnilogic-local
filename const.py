"""Constants for the OmniLogic Local integration."""

DOMAIN = "omnilogic_local"
KEY_COORDINATOR = "coordinator"
KEY_OMNI_API = "omni_api"
KEY_DEVICE_REGISTRY = "device_registry"
DEFAULT_POLL_INTERVAL = 5

REPOLL_DELAY = 1

UNIQUE_ID = "omnilogic"
MANUFACTURER = "Hayward"

DEVICE_TYPES_FILTER = [
    "Filter",
]

DEVICE_TYPES_LIGHT = [
    "ColorLogic-Light",
]

DEVICE_TYPES_SWITCH = [
    "ValveActuator",
    "Relay",
]


DEVICE_TYPES = DEVICE_TYPES_FILTER + DEVICE_TYPES_LIGHT + DEVICE_TYPES_SWITCH

OMNI_TO_HASS_TYPES = {
    "Filter": "switch",
    "ColorLogic-Light": "light",
    "ValveActuator": "switch",
    "Relay": "switch",
}
