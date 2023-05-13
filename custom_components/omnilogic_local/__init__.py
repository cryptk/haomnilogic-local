"""The OmniLogic Local integration."""
from __future__ import annotations

from pyomnilogic_local import OmniLogicAPI

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PORT,
    CONF_TIMEOUT,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, KEY_COORDINATOR, UNIQUE_ID
from .coordinator import OmniLogicCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.WATER_HEATER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OmniLogic Local from a config entry."""

    # Create an API instance
    omni_api = OmniLogicAPI(
        (entry.data[CONF_IP_ADDRESS], entry.data[CONF_PORT]), entry.data[CONF_TIMEOUT]
    )

    # Validate that we can talk to the API endpoint
    try:
        await omni_api.async_get_config()
    except Exception as error:
        raise ConfigEntryNotReady from error

    # Create our data coordinator
    coordinator = OmniLogicCoordinator(hass=hass, omni_api=omni_api)
    await coordinator.async_config_entry_first_refresh()

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, UNIQUE_ID)},
        manufacturer="Hayward",
        # TODO: Figure out how to manage device naming, the API does not return a name
        name="omnilogic",
    )

    # Store them for use later
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        KEY_COORDINATOR: coordinator,
        # KEY_DEVICE_REGISTRY: device_registry
        # KEY_OMNI_API: omni_api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
