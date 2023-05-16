"""Diagnostics support for ESPHome."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, KEY_COORDINATOR
from .coordinator import OmniLogicCoordinator


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diag: dict[str, Any] = {}

    diag["config"] = config_entry.as_dict()

    coordinator: OmniLogicCoordinator = hass.data[DOMAIN][config_entry.entry_id].get(KEY_COORDINATOR)
    if coordinator:
        diag["msp_config"] = coordinator.msp_config
        diag["telemetry"] = coordinator.telemetry
        diag["data"] = coordinator.data

    # There are no credentials or other secrets within the diagnostic data for this integration
    return async_redact_data(diag, [])
