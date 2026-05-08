from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from pyomnilogic_local import Bow, Chlorinator, Filter, Group, Pump, Relay, Schedule
from pyomnilogic_local.omnitypes import (
    BodyOfWaterType,
    FilterValvePosition,
    RelayFunction,
    RelayType,
)

from .const import DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .typing import OmniLogicEquipment

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

    # Add schedule switches
    for _, _, schedule in coordinator.omni.schedules.items():
        entities.append(OmniLogicScheduleSwitchEntity(coordinator=coordinator, equipment=schedule))

    # Add group switches
    for _, _, group in coordinator.omni.groups.items():
        entities.append(OmniLogicGroupSwitchEntity(coordinator=coordinator, equipment=group))

    async_add_entities(entities)


class OmniLogicSwitchEntity[T: OmniLogicEquipment](OmniLogicEntity[T], SwitchEntity):
    """Base class for switch entities in the OmniLogic integration."""

    @property
    def is_on(self) -> bool | None:
        if hasattr(self.equipment, "is_on"):
            return self.equipment.is_on
        msg = f"is_on not implemented for equipment type: {type(self.equipment)}"
        raise NotImplementedError(msg)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if hasattr(self.equipment, "turn_on"):
            await self.equipment.turn_on()
            self.coordinator.do_next_refresh_after()
        else:
            msg = f"turn_on not implemented for equipment type: {type(self.equipment)}"
            raise NotImplementedError(msg)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if hasattr(self.equipment, "turn_off"):
            await self.equipment.turn_off()
            self.coordinator.do_next_refresh_after()
        else:
            msg = f"turn_off not implemented for equipment type: {type(self.equipment)}"
            raise NotImplementedError(msg)


class OmniLogicRelaySwitchEntity(OmniLogicSwitchEntity[Relay]):
    """Switch entity for general relays (excluding valve actuators)."""

    @property
    def icon(self) -> str | None:
        """Return icon based on relay function."""
        match self.equipment.function:
            case RelayFunction.BACKYARD_LIGHT | RelayFunction.LAMINARS | RelayFunction.LIGHT | RelayFunction.POOL_LIGHT:
                return "mdi:lightbulb" if self.is_on else "mdi:lightbulb-off"
            case _:
                return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"


class OmniLogicPumpSwitchEntity(OmniLogicSwitchEntity[Pump]):
    """Switch entity for pumps."""

    @property
    def icon(self) -> str | None:
        return "mdi:pump" if self.is_on else "mdi:pump-off"


class OmniLogicFilterSwitchEntity(OmniLogicSwitchEntity[Filter]):
    """Switch entity for filters."""

    @property
    def icon(self) -> str | None:
        return "mdi:pump" if self.is_on else "mdi:pump-off"

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return {
            "omni_filter_state": str(self.equipment.state),
            "omni_why_on": str(self.equipment.why_on),
        }


class OmniLogicChlorinatorSwitchEntity(OmniLogicSwitchEntity[Chlorinator]):
    """Switch entity for chlorinators."""

    @property
    def icon(self) -> str | None:
        return "mdi:toggle-switch-variant" if self.is_on else "mdi:toggle-switch-variant-off"


class OmniLogicGroupSwitchEntity(OmniLogicSwitchEntity[Group]):
    """Switch entity for groups."""

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""
        device_info = super().device_info
        _LOGGER.debug(device_info)
        return device_info


class OmniLogicScheduleSwitchEntity(OmniLogicSwitchEntity[Schedule]):
    """Switch entity for general relays (excluding valve actuators)."""

    _controlled_equipment: OmniLogicEquipment

    def __init__(self, coordinator: OmniLogicCoordinator, equipment: Schedule) -> None:
        super().__init__(coordinator, equipment)
        _controlled_equipment = coordinator.omni.get_equipment_by_id(equipment.equipment_id)
        if _controlled_equipment is not None:
            self._controlled_equipment = cast(OmniLogicEquipment, _controlled_equipment)
        else:
            raise ValueError(f"Could not find equipment with ID {equipment.equipment_id} for schedule {equipment.name}")

    @property
    def name(self) -> str:
        days_active_str = "".join([day.title()[:2] for day in self.equipment.days_active])
        return (
            f"Schedule {self._controlled_equipment.name}"
            f" {self.equipment.start_hour:02d}:{self.equipment.start_minute:02d}"
            f" {self.equipment.end_hour:02d}:{self.equipment.end_minute:02d}"
            f" {days_active_str}"
        )

    @property
    def unique_id(self) -> str | None:
        # Unique ID based on only bow_id and system_id as the name is generated based on the schedule
        # parameters, which could be altered by the user. We don't want a user changing the start time
        # of a schedule to result in a new entity being created
        return f"{self.bow_id} {self.system_id} schedule"


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
        self.coordinator.do_next_refresh_after()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug("turning off spillover ID: %s", self.system_id)
        await self.equipment.turn_off_spillover()
        self.coordinator.do_next_refresh_after()
