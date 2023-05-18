from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BACKYARD_SYSTEM_ID, MANUFACTURER, OmniType

if TYPE_CHECKING:
    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


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
        # self.coordinator = coordinator
        # self.context = context
        self.bow_id = bow_id
        self.system_id = system_id
        self._attr_name = name
        self._attr_unique_id = f"{system_id}_{name}"
        self._extra_attributes = extra_attributes

    def get_config(self, system_id=None):
        system_id = system_id if system_id is not None else self.system_id
        return self.coordinator.data[system_id]["omni_config"]

    def set_config(
        self,
        new_config: dict[str, str],
        system_id: int | None = None,
        coordinator_update: bool = True,
    ):
        system_id = system_id if system_id is not None else self.system_id

        _LOGGER.debug("Updating config for system ID: %s with data: %s", system_id, new_config)
        self.coordinator.data[system_id]["omni_config"].update(new_config)
        if coordinator_update:
            self.coordinator.async_set_updated_data(self.coordinator.data)

    def get_telemetry(self, system_id: int | None = None):
        system_id = system_id if system_id is not None else self.system_id
        if self.available:
            return self.coordinator.data[system_id]["omni_telemetry"]

    def set_telemetry(
        self,
        new_telemetry: dict[str, Any],
        system_id: int | None = None,
        coordinator_update: bool = True,
    ):
        system_id = system_id if system_id is not None else self.system_id

        _LOGGER.debug(
            "Updating telemetry for system ID: %s with data: %s",
            system_id,
            new_telemetry,
        )
        self.coordinator.data[system_id]["omni_telemetry"].update(new_telemetry)
        if coordinator_update:
            self.coordinator.async_set_updated_data(self.coordinator.data)

    @property
    def available(self) -> bool:
        return self.coordinator.data[BACKYARD_SYSTEM_ID]["omni_telemetry"]["@state"] == 1

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        # If we have a BOW ID, then we associate with that BOWs device, if not, we associate with the Backyard
        if self.bow_id is not None:
            identifiers = {(OmniType.BOW_MSP, self.bow_id)}
        else:
            identifiers = {(OmniType.BACKYARD, BACKYARD_SYSTEM_ID)}
        return DeviceInfo(
            identifiers=identifiers,
            manufacturer=MANUFACTURER,
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return {
            "omni_system_id": self.system_id,
        } | ({"omni_bow_id": self.bow_id} if self.bow_id is not None else {})
