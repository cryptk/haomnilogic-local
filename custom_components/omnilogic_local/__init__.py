"""The OmniLogic Local integration."""
from __future__ import annotations

import logging

from pyomnilogic_local.api import OmniLogicAPI

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

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR, OmniType
from .coordinator import OmniLogicCoordinator
from .utils import get_entities_of_omni_types

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.WATER_HEATER,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OmniLogic Local from a config entry."""

    # Create an API instance
    omni_api = OmniLogicAPI((entry.data[CONF_IP_ADDRESS], entry.data[CONF_PORT]), entry.data[CONF_TIMEOUT])

    # Validate that we can talk to the API endpoint
    try:
        await omni_api.async_get_config()
    except Exception as error:
        raise ConfigEntryNotReady from error

    # Create our data coordinator
    coordinator = OmniLogicCoordinator(hass=hass, omni_api=omni_api)
    await coordinator.async_config_entry_first_refresh()

    device_registry = dr.async_get(hass)

    # Create a device for the Omni Backyard
    backyard = get_entities_of_omni_types(coordinator.data, [OmniType.BACKYARD])[BACKYARD_SYSTEM_ID]
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(OmniType.BACKYARD, BACKYARD_SYSTEM_ID)},
        manufacturer="Hayward",
        suggested_area="Back Yard",
        name=f"{entry.data[CONF_NAME]} {backyard['metadata']['name']}",
    )

    # Create a device for each Body of Water
    for system_id, bow in get_entities_of_omni_types(coordinator.data, [OmniType.BOW_MSP]).items():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(OmniType.BOW_MSP, system_id)},
            manufacturer="Hayward",
            suggested_area="Back Yard",
            name=f"{entry.data[CONF_NAME]} {bow['metadata']['name']}",
        )

    # Store them for use later
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        KEY_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
