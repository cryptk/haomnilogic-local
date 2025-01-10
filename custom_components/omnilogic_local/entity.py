from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Generic, cast

from pyomnilogic_local.models.mspconfig import MSPSystem
from pyomnilogic_local.models.telemetry import TelemetryBackyard, TelemetryType
from pyomnilogic_local.omnitypes import BackyardState, OmniType

from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BACKYARD_SYSTEM_ID, MANUFACTURER
from .types.entity_index import EntityIndexTypeVar

if TYPE_CHECKING:
    from pyomnilogic_local.models.mspconfig import MSPConfigType

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)


class OmniLogicEntity(CoordinatorEntity, Generic[EntityIndexTypeVar]):
    _attr_has_entity_name = True

    data: EntityIndexTypeVar
    coordinator: OmniLogicCoordinator

    def __init__(
        self,
        coordinator: OmniLogicCoordinator,
        context: int,
        extra_attributes: dict[str, str] | None = None,  # Extra attributes dictionary
    ) -> None:
        super().__init__(coordinator=coordinator, context=context)
        self.data = cast(EntityIndexTypeVar, coordinator.data[context])
        self.bow_id = coordinator.data[context].msp_config.bow_id
        self.system_id = context
        self._extra_attributes = extra_attributes

    @callback  # type: ignore[misc]
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = cast(EntityIndexTypeVar, self.coordinator.data[self.system_id])
        self.async_write_ha_state()

    def get_config_by_systemid(self, system_id: int) -> MSPConfigType:
        return self.coordinator.data[system_id].msp_config

    def set_config(
        self,
        new_config: dict[str, int | str],
        system_id: int | None = None,
        coordinator_update: bool = True,
    ) -> None:
        system_id = system_id if system_id is not None else self.system_id

        _LOGGER.debug("Updating config for system ID: %s with data: %s", system_id, new_config)

        for key, value in new_config.items():
            setattr(self.coordinator.data[system_id].msp_config, key, value)
        if coordinator_update:
            self.coordinator.async_set_updated_data(self.coordinator.data)

    def get_telemetry_by_systemid(self, system_id: int) -> TelemetryType | None:
        if self.available:
            return self.coordinator.data[system_id].telemetry
        return None

    def get_system_config(self) -> MSPSystem:
        return self.coordinator.msp_config.system

    def set_telemetry(
        self,
        new_telemetry: dict[str, Any],
    ) -> None:
        _LOGGER.debug(
            "Updating telemetry for system ID: %s with data: %s",
            self.system_id,
            new_telemetry,
        )
        try:
            for key, value in new_telemetry.items():
                setattr(self.coordinator.data[self.system_id].telemetry, key, value)
        except KeyError:
            return None
        self.coordinator.async_set_updated_data(self.coordinator.data)

    @property
    def available(self) -> bool:
        return cast(TelemetryBackyard, self.coordinator.data[BACKYARD_SYSTEM_ID].telemetry).state is BackyardState.ON

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        # If we have a BOW ID, then we associate with that BOWs device, if not, we associate with the Backyard
        if self.bow_id is not None:
            identifiers = {(OmniType.BOW, self.bow_id)}
        else:
            identifiers = {(OmniType.BACKYARD, BACKYARD_SYSTEM_ID)}
        return DeviceInfo(
            identifiers=identifiers,
            manufacturer=MANUFACTURER,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | int]:
        return {
            "omni_system_id": self.system_id,
            "omni_bow_id": self.bow_id,
        }

    @property
    def name(self) -> Any:
        return self._attr_name if hasattr(self, "_attr_name") else self.data.msp_config.name

    @property
    def unique_id(self) -> str | None:
        return f"{self.bow_id} {self.system_id} {self.name}"
