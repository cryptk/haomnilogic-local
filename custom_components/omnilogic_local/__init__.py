"""The OmniLogic Local integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    Platform,
)  # CONF_SCAN_INTERVAL kept for migration
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pyomnilogic_local import OmniLogic
from pyomnilogic_local.omnitypes import OmniType

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR
from .coordinator import OmniLogicCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
    Platform.WATER_HEATER,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OmniLogic Local from a config entry."""
    # Create an API instance
    omni = OmniLogic(entry.data[CONF_IP_ADDRESS], entry.data[CONF_PORT], entry.data[CONF_TIMEOUT])

    # Validate that we can talk to the API endpoint
    try:
        await omni.refresh()
    except Exception as error:
        raise ConfigEntryNotReady from error

    # Create our data coordinator
    coordinator = OmniLogicCoordinator(hass=hass, omni=omni)
    await coordinator.async_config_entry_first_refresh()

    device_registry = dr.async_get(hass)

    # Create a device for the Omni Backyard
    _LOGGER.debug("Creating device for backyard: %s", omni.backyard)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"backyard_{BACKYARD_SYSTEM_ID}")},
        manufacturer="Hayward",
        suggested_area="Back Yard",
        name=f"{entry.data[CONF_NAME]} {omni.backyard.name}",
    )

    # Create a device for each Body of Water
    for bow in omni.backyard.bow:
        _LOGGER.debug("Creating device for BOW: %s", bow)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"bow_{bow.system_id}")},
            manufacturer="Hayward",
            suggested_area="Back Yard",
            name=f"{entry.data[CONF_NAME]} {bow.name}",
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
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new = {**config_entry.data}
        # The migration to VERSION 4 removes this, but we need to add it here to migrate from version 1 to version 2
        new[CONF_SCAN_INTERVAL] = 10

        hass.config_entries.async_update_entry(config_entry, data=new, version=2)

    if config_entry.version == 2:
        # Migrate device identifiers from (OmniType, int) to (DOMAIN, str)
        device_registry = dr.async_get(hass)

        # Find all devices associated with this config entry
        devices = dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)

        for device in devices:
            # Look for old-style identifiers
            old_identifiers = set()
            new_identifiers = set()

            for identifier in device.identifiers:
                domain, value = identifier
                # Check if this is an old-style identifier (domain is an OmniType enum value)
                if domain in [OmniType.BACKYARD.value, OmniType.BOW.value]:
                    old_identifiers.add(identifier)
                    # Convert to new format
                    if domain == OmniType.BACKYARD.value:
                        new_identifiers.add((DOMAIN, f"backyard_{value}"))
                    elif domain == OmniType.BOW.value:
                        new_identifiers.add((DOMAIN, f"bow_{value}"))
                else:
                    # Keep other identifiers as-is
                    new_identifiers.add(identifier)

            # Update device if we found old identifiers
            if old_identifiers:
                _LOGGER.debug(
                    "Migrating device %s identifiers from %s to %s",
                    device.id,
                    old_identifiers,
                    new_identifiers,
                )
                device_registry.async_update_device(
                    device.id,
                    new_identifiers=new_identifiers,
                )

        # Migrate entity unique_ids for backyard entities from "None X Y" to "-1 X Y"
        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)

        for entity in entities:
            parts = entity.unique_id.split(" ")
            if parts[0] != "None":
                continue
            parts[0] = "-1"
            new_unique_id = " ".join(parts)
            _LOGGER.debug(
                "Migrating entity %s unique_id from '%s' to '%s'",
                entity.entity_id,
                entity.unique_id,
                new_unique_id,
            )
            entity_registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

        hass.config_entries.async_update_entry(config_entry, version=3)

    if config_entry.version == 3:
        new = {k: v for k, v in config_entry.data.items() if k != CONF_SCAN_INTERVAL}
        hass.config_entries.async_update_entry(config_entry, data=new, version=4)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True
