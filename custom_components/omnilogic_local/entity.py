from __future__ import annotations

import logging
from typing import Any, Generic, TypeVar, cast

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyomnilogic_local import (
    CSAD,
    Backyard,
    Bow,
    Chlorinator,
    ChlorinatorEquipment,
    ColorLogicLight,
    CSADEquipment,
    Filter,
    Group,
    Heater,
    HeaterEquipment,
    Pump,
    Relay,
    Schedule,
    Sensor,
)

from .const import BACKYARD_SYSTEM_ID, DOMAIN, MANUFACTURER, UPDATE_DELAY_SECONDS
from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)

EquipmentTypes = TypeVar(
    "EquipmentTypes",
    bound=CSAD
    | Backyard
    | Bow
    | Chlorinator
    | ChlorinatorEquipment
    | ColorLogicLight
    | CSADEquipment
    | Filter
    | Group
    | Heater
    | HeaterEquipment
    | Pump
    | Relay
    | Schedule
    | Sensor,
)


class OmniLogicEntity(CoordinatorEntity[OmniLogicCoordinator], Generic[EquipmentTypes]):
    _attr_has_entity_name = True

    equipment: EquipmentTypes
    coordinator: OmniLogicCoordinator

    def __init__(
        self,
        coordinator: OmniLogicCoordinator,
        equipment: EquipmentTypes,
    ) -> None:
        super().__init__(coordinator=coordinator)
        self.equipment = equipment
        self.bow_id = equipment.bow_id
        self.system_id = equipment.system_id
        subclass_name = self.__class__.__name__
        _LOGGER.debug("Configuring %s for %s - SystemID: %s, Name: %s", subclass_name, equipment.omni_type, self.system_id, equipment.name)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.system_id is not None:
            subclass_name = self.__class__.__name__
            _LOGGER.debug(
                "Updating %s for %s - SystemID: %s, Name: %s", subclass_name, self.equipment.omni_type, self.system_id, self.equipment.name
            )
            self.equipment = cast("EquipmentTypes", self.coordinator.omni.get_equipment_by_id(self.system_id))
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        # By default we consider an entity available if the backyard is ready (not in service mode),
        # Individual entities can override this if needed.
        return self.equipment._omni.backyard.is_ready

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        # If we have a BOW ID, then we associate with that BOWs device, if not, we associate with the Backyard
        if self.equipment.bow_id is not None and self.equipment.bow_id != -1:
            identifiers = {(DOMAIN, f"bow_{self.bow_id}")}
        else:
            identifiers = {(DOMAIN, f"backyard_{BACKYARD_SYSTEM_ID}")}
        return DeviceInfo(
            identifiers=identifiers,
            manufacturer=MANUFACTURER,
        )

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return {}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base_attributes: dict[str, Any] = {
            "omni_system_id": self.system_id,
            "omni_bow_id": self.bow_id,
        }
        return self._extra_state_attributes | base_attributes

    @property
    def name(self) -> Any:
        return self._attr_name if hasattr(self, "_attr_name") else self.equipment.name

    @property
    def unique_id(self) -> str | None:
        return f"{self.bow_id} {self.system_id} {self.name}"

    @callback
    def schedule_delayed_update(self, delay: float = UPDATE_DELAY_SECONDS) -> None:
        """Schedule a coordinator refresh after a short delay.

        Call this at the end of any action method (async_turn_on, async_turn_off, etc.)
        to give the OmniLogic time to reflect the change in its telemetry before we poll.
        Any currently pending interval refresh is cancelled and rescheduled for `delay`
        seconds from now, ensuring no back-to-back updates occur. The interval clock
        resets naturally once the refresh completes.
        """
        _LOGGER.debug("Scheduling delayed update for %s in %s seconds", self.name, delay)
        self.coordinator._retry_after = delay
        self.coordinator._schedule_refresh()
