"""The OmniLogic Local integration."""
from __future__ import annotations

import logging
from typing import cast

from pyomnilogic_local.api import OmniLogicAPI
from pyomnilogic_local.types import OmniType

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import BACKYARD_SYSTEM_ID, DEFAULT_SCAN_INTERVAL, DOMAIN, KEY_COORDINATOR
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
    omni_api = OmniLogicAPI(entry.data[CONF_IP_ADDRESS], entry.data[CONF_PORT], entry.data[CONF_TIMEOUT])

    # Validate that we can talk to the API endpoint
    try:
        await omni_api.async_get_config()
    except Exception as error:
        raise ConfigEntryNotReady from error

    # Create our data coordinator
    coordinator = OmniLogicCoordinator(hass=hass, omni_api=omni_api, scan_interval=entry.data[CONF_SCAN_INTERVAL])
    await coordinator.async_config_entry_first_refresh()

    device_registry = dr.async_get(hass)

    # Create a device for the Omni Backyard
    backyard = get_entities_of_omni_types(coordinator.data, [OmniType.BACKYARD])[BACKYARD_SYSTEM_ID]
    _LOGGER.debug("Creating device for backyard: %s", backyard)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(OmniType.BACKYARD, BACKYARD_SYSTEM_ID)},
        manufacturer="Hayward",
        suggested_area="Back Yard",
        name=f"{entry.data[CONF_NAME]} {backyard.msp_config.name}",
    )

    # Create a device for each Body of Water
    for system_id, bow in get_entities_of_omni_types(coordinator.data, [OmniType.BOW]).items():
        _LOGGER.debug("Creating device for BOW: %s", bow)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(OmniType.BOW, system_id)},
            manufacturer="Hayward",
            suggested_area="Back Yard",
            name=f"{entry.data[CONF_NAME]} {bow.msp_config.name}",
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
    # I think it is a bug that the await for async_unload_platforms above has a signature that indicates it returns a bool, yet unload_ok
    # is detected as "Any" by mypy
    return cast(bool, unload_ok)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    if config_entry.version == 1:
        _LOGGER.debug("Migrating from version %s", config_entry.version)

        new = {**config_entry.data}
        new[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True
