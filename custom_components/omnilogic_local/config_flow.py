"""Config flow for OmniLogic Local integration."""
from __future__ import annotations

import logging
from typing import Any

from pyomnilogic_local.api import OmniLogicAPI
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Required(CONF_NAME, default="Omnilogic"): cv.string,
        vol.Optional(CONF_PORT, default=10444): cv.port,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(cv.positive_int, vol.Clamp(min=MIN_SCAN_INTERVAL)),
        vol.Optional(CONF_TIMEOUT, default=5.0): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    omni = OmniLogicAPI(data[CONF_IP_ADDRESS], data[CONF_PORT], data[CONF_TIMEOUT])
    try:
        config = await omni.async_get_config()
    except TimeoutError as exc:
        raise OmniLogicTimeout from exc
    except Exception as exc:
        raise CannotConnect from exc

    telemetry = await omni.async_get_telemetry()

    # Return info that you want to store in the config entry.
    return {"config": config, "telemetry": telemetry}


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.data = dict(config_entry.data)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            self.data.update(user_input)
            # write updated config entries
            self.hass.config_entries.async_update_entry(self.config_entry, data=self.data)
            # # reload updated config entries
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            self.async_abort(reason="configuration updated")

            return self.async_create_entry(data=self.data)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_IP_ADDRESS, default=self.config_entry.data[CONF_IP_ADDRESS]): cv.string,
                    vol.Required(CONF_PORT, default=self.config_entry.data[CONF_PORT]): cv.port,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        description="bar",
                        msg="foo",
                        default=self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(cv.positive_int, vol.Clamp(min=MIN_SCAN_INTERVAL)),
                    vol.Required(CONF_TIMEOUT, default=self.config_entry.data[CONF_TIMEOUT]): vol.All(
                        vol.Coerce(float), vol.Range(min=0.5, max=10.0)
                    ),
                }
            ),
        )


class OmnilogicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for OmniLogic Local."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect as exc:
                errors["base"] = "cannot_connect"
                _LOGGER.exception("Failed to connect: %s", exc)
            except OmniLogicTimeout as exc:
                errors["base"] = "timeout"
                _LOGGER.exception("Connection timed out: %s", exc)
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", exc)
                errors["base"] = "unknown"
            else:
                # pylint: disable=fixme
                # TODO: https://developers.home-assistant.io/docs/config_entries_config_flow_handler#unique-ids
                # It would be nice to support unique IDs to prevent the same device being set up twice,
                # but so far we don't have anything good that we can use for a unique ID. We could possibly leverage
                # DHCP discovery, which would give us a MAC address that we could use.  The other option is the hostname,
                # which by default has the mac address embedded in it, but that is technically capable of being changed
                # if the user modifies their router configs to override the OmniLogic default hostname.
                # For now, we are just asking for a name, and using that as the unique_id, which will be confusing because
                # a use could rename the integration config entry, but that would not change this unique ID, although they
                # came from the same source... yeah... it's janky... I'll make it better later... somehow
                # we may need to use https://developers.home-assistant.io/docs/entity_registry_index/#unique-id-of-last-resort
                await self.async_set_unique_id(user_input[CONF_NAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback  # type: ignore[misc]
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class OmniLogicTimeout(HomeAssistantError):
    """Error to indicate there is invalid auth."""
