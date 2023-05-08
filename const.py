"""Constants for the OmniLogic Local integration."""

DOMAIN = "omnilogic_local"
KEY_COORDINATOR = "coordinator"
KEY_OMNI_API = "omni_api"
KEY_DEVICE_REGISTRY = "device_registry"
DEFAULT_POLL_INTERVAL = 5

REPOLL_DELAY = 1

UNIQUE_ID = "omnilogic"
MANUFACTURER = "Hayward"

KEY_MSP_BACKYARD = "Backyard"
KEY_MSP_BOW = "Body-of-water"
KEY_MSP_SYSTEM_ID = "System-Id"

KEY_TELEMETRY_SYSTEM_ID = "@systemId"

OMNI_DEVICE_TYPES_FILTER = [
    "Filter",
]

OMNI_DEVICE_TYPES_LIGHT = [
    "ColorLogic-Light",
]

OMNI_DEVICE_TYPES_SWITCH = [
    "ValveActuator",
    "Relay",
]

OMNI_DEVICE_TYPES_SENSOR = [
    "Sensor"
]


OMNI_DEVICE_TYPES = [
    KEY_MSP_BACKYARD,
    KEY_MSP_BOW,
    *OMNI_DEVICE_TYPES_FILTER,
    *OMNI_DEVICE_TYPES_LIGHT,
    *OMNI_DEVICE_TYPES_SWITCH,
    *OMNI_DEVICE_TYPES_SENSOR
]

OMNI_TO_HASS_TYPES = {
    "Backyard": "device",
    "Body-of-water": "device",
    "Filter": "switch",
    "ColorLogic-Light": "light",
    "ValveActuator": "switch",
    "Relay": "switch",
    "Sensor": "sensor"
}
