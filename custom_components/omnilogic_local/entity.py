from __future__ import annotations

import logging
from functools import cached_property
from typing import Any, cast

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BACKYARD_SYSTEM_ID, DOMAIN, MANUFACTURER
from .coordinator import OmniLogicCoordinator
from .typing import OmniLogicEquipment

_LOGGER = logging.getLogger(__name__)


class OmniLogicEntity[EquipmentTypes: OmniLogicEquipment](CoordinatorEntity[OmniLogicCoordinator]):
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
        # Tracks whether this entity's equipment was present in the latest telemetry
        # frame. We never overwrite self.equipment with None (see _handle_coordinator_update),
        # so every dereference stays safe; availability is driven by this flag instead.
        self._equipment_available = True
        self.bow_id = equipment.bow_id
        self.system_id = equipment.system_id
        subclass_name = self.__class__.__name__
        _LOGGER.debug("Configuring %s for %s - SystemID: %s, Name: %s", subclass_name, equipment.omni_type, self.system_id, equipment.name)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.system_id is not None:
            # Equipment can be temporarily missing from a telemetry frame (transient
            # comms gap) or genuinely absent. In that case keep the last-known object
            # rather than storing None, so name/device_info/attributes never dereference
            # None (which previously left the entity permanently stuck throwing every
            # poll). Availability is signalled via _equipment_available instead.
            equipment = self.coordinator.omni.get_equipment_by_id(self.system_id)
            self._equipment_available = equipment is not None
            if equipment is not None:
                self.equipment = cast("EquipmentTypes", equipment)
                _LOGGER.debug(
                    "Updating %s for %s - SystemID: %s, Name: %s",
                    self.__class__.__name__,
                    self.equipment.omni_type,
                    self.system_id,
                    self.equipment.name,
                )
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        # By default we consider an entity available if the backyard is ready (not in service mode),
        # Individual entities can override this if needed.
        # If this entity's equipment was missing from the latest telemetry, treat it as unavailable.
        return super().available and self._equipment_available and self.equipment._omni.backyard.is_ready

    @cached_property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""
        # If we have a BOW ID, then we associate with that BOWs device, if not, we associate with the Backyard
        if self.equipment.bow_id is not None and self.equipment.bow_id > BACKYARD_SYSTEM_ID:
            identifiers = {(DOMAIN, f"bow_{self.bow_id}")}
        elif self.equipment.bow_id == BACKYARD_SYSTEM_ID:
            identifiers = {(DOMAIN, f"backyard_{BACKYARD_SYSTEM_ID}")}
        else:
            identifiers = {(DOMAIN, "system")}
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
    def name(self) -> str | None:
        return self._attr_name if hasattr(self, "_attr_name") else self.equipment.name

    @property
    def unique_id(self) -> str | None:
        return f"{self.bow_id} {self.system_id} {self.name}"
