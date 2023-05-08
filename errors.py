"""Custom error types for the omnilogic integration."""
from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class UnknownDevice(HomeAssistantError):
    """Error to inticate we received telemetry for a device that we have no config data for."""
