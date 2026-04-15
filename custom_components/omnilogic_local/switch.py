from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from pyomnilogic_local import Bow, Chlorinator, Filter, Pump, Relay
from pyomnilogic_local.omnitypes import (
    BodyOfWaterType,
    FilterValvePosition,
    RelayFunction,
    RelayType,
)

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""
    coordinator: OmniLogicCoordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities: list[SwitchEntity] = []

    # Add relay switches (excluding valve actuators)
    for _, _, relay in coordinator.omni.all_relays.items():
        # Skip valve actuators - they belong in valve platform
        if relay.relay_type == RelayType.VALVE_ACTUATOR:
            continue
        entities.append(OmniLogicRelaySwitchEntity(coordinator=coordinator, equipment=relay))

    # Add pump switches
    for _, _, pump in coordinator.omni.all_pumps.items():
        entities.append(OmniLogicPumpSwitchEntity(coordinator=coordinator, equipment=pump))

    # Add filter switches
    for _, _, filter_equipment in coordinator.omni.all_filters.items():
        entities.append(OmniLogicFilterSwitchEntity(coordinator=coordinator, equipment=filter_equipment))

    # Add chlorinator switches
    for _, _, chlorinator in coordinator.omni.all_chlorinators.items():
        entities.append(OmniLogicChlorinatorSwitchEntity(coordinator=coordinator, equipment=chlorinator))

    # Add spillover switches for pools that support it
    for _, _, bow in coordinator.omni.all_bows.items():
        if bow.equip_type == BodyOfWaterType.POOL and bow.supports_spillover:
            entities.append(OmniLogicSpilloverSwitchEntity(coordinator=coordinator, equipment=bow))

    async_add_entities(entities)


class OmniLogicRelaySwitchEntity(OmniLogicEntity[Relay], SwitchEntity):
    """Switch entity for general relays (excluding valve actuators)."""

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Relay) -> None:
        super().__init__(coordinator, equipment)

    @property
    def icon(self) -> str | None:
        """Return icon based on relay function."""
        match self.equipment.function:
            case RelayFunction.LAMINARS:
                return "mdi:light"
            case RelayFunction.LIGHT:
                return "mdi:light"
            case RelayFunction.BACKYARD_LIGHT:
                return "mdi:light"
            case _:
                return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"

    @property
    def is_on(self) -> bool | None:
        return self.equipment.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on relay ID: %s", self.system_id)
        await self.equipment.turn_on()
        self.schedule_delayed_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off relay ID: %s", self.system_id)
        await self.equipment.turn_off()
        self.schedule_delayed_update()


class OmniLogicPumpSwitchEntity(OmniLogicEntity[Pump], SwitchEntity):
    """Switch entity for pumps."""

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Pump) -> None:
        super().__init__(coordinator, equipment)

    @property
    def icon(self) -> str | None:
        return "mdi:pump" if self.is_on else "mdi:pump-off"

    @property
    def is_on(self) -> bool | None:
        return self.equipment.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on pump ID: %s", self.system_id)
        await self.equipment.turn_on()
        self.schedule_delayed_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off pump ID: %s", self.system_id)
        await self.equipment.turn_off()
        self.schedule_delayed_update()


class OmniLogicFilterSwitchEntity(OmniLogicEntity[Filter], SwitchEntity):
    """Switch entity for filters."""

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Filter) -> None:
        super().__init__(coordinator, equipment)

    @property
    def icon(self) -> str | None:
        return "mdi:pump" if self.is_on else "mdi:pump-off"

    @property
    def is_on(self) -> bool | None:
        return self.equipment.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on filter ID: %s", self.system_id)
        await self.equipment.turn_on()
        self.schedule_delayed_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off filter ID: %s", self.system_id)
        await self.equipment.turn_off()
        self.schedule_delayed_update()

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return {
            "omni_filter_state": str(self.equipment.state),
            "omni_why_on": str(self.equipment.why_on),
        }


class OmniLogicChlorinatorSwitchEntity(OmniLogicEntity[Chlorinator], SwitchEntity):
    """Switch entity for chlorinators."""

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Chlorinator) -> None:
        super().__init__(coordinator, equipment)

    @property
    def icon(self) -> str | None:
        return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"

    @property
    def is_on(self) -> bool | None:
        return self.equipment.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on chlorinator ID: %s", self.system_id)
        await self.equipment.turn_on()
        self.schedule_delayed_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off chlorinator ID: %s", self.system_id)
        await self.equipment.turn_off()
        self.schedule_delayed_update()


class OmniLogicSpilloverSwitchEntity(OmniLogicEntity[Bow], SwitchEntity):
    """Switch entity for spillover control."""

    _attr_name = "Spillover"

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Bow) -> None:
        super().__init__(coordinator, equipment)
        # Get the filter for this body of water to check spillover state
        # In the OmniLogic system, there is always exactly one filter per BoW
        # The underlying library should be modified to not have filters be a list
        _, _, self.filter = equipment.filters.items()[0]

    @property
    def icon(self) -> str | None:
        return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"

    @property
    def is_on(self) -> bool | None:
        """Check if spillover is currently active."""
        return self.filter.valve_position == FilterValvePosition.SPILLOVER

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug("turning on spillover ID: %s", self.system_id)
        await self.equipment.turn_on_spillover()
        self.schedule_delayed_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off spillover ID: %s", self.system_id)
        await self.equipment.turn_off_spillover()
        self.schedule_delayed_update()
