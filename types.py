from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, UNIQUE_ID

if TYPE_CHECKING:
    from .coordinator import OmniLogicCoordinator


class OmniLogicEntity(CoordinatorEntity):
    _attr_name = None
    _attr_has_entity_name = True
    _attr_unique_id = None

    model = None

    def __init__(
        self,
        coordinator: OmniLogicCoordinator,
        context,
        name: str,  # OmniLogic device name
        system_id: int,  # OmniLogic SystemID
        bow_id: int,  # OmniLogic Body of Water ID
        extra_attributes: dict[str, str],  # Extra attributes dictionary
    ) -> None:
        super().__init__(coordinator=coordinator, context=context)
        self.coordinator = coordinator
        self.context = context
        self.bow_id = bow_id
        self.system_id = system_id
        self._attr_name = name
        self._attr_unique_id = system_id
        self._extra_attributes = extra_attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, UNIQUE_ID)},
            manufacturer=MANUFACTURER,
            # model=self.model,
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return {
            "omni_system_id": self.system_id,
        } | ({"omni_bow_id": self.bow_id} if self.bow_id is not None else {})

    def push_assumed_state(self):
        # It takes the controller ~1s to return back the new state in the telemetry data, so just in case the next poll is happening
        # within that time period, we want to cancel it, and reschedule the next poll to occur after the full POLL_INTERVAL
        self.coordinator._schedule_refresh()
        self.async_write_ha_state()
