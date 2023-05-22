# We do a lot of work with altering data in TypeDicts, until we figure out a better way, we need to just silence the type checker
# mypy: disable-error-code="typeddict-item"
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BACKYARD_SYSTEM_ID, MANUFACTURER, OmniModel, OmniType
from .types.entity_index import EntityDataBackyardT, EntityIndexTypeVar
from .types.telemetry import (
    TelemetryBackyardT,
    TelemetryBodyOfWaterT,
    TelemetryColorLogicLightT,
    TelemetryFilterT,
    TelemetryGroupT,
    TelemetryHeaterT,
    TelemetryPumpT,
    TelemetryType,
    TelemetryValveActuatorT,
    TelemetryVirtualHeaterT,
)

if TYPE_CHECKING:
    from .coordinator import OmniLogicCoordinator
    from .types.mspconfig import MSPSystemT, MSPType

_LOGGER = logging.getLogger(__name__)


class OmniLogicEntity(CoordinatorEntity, Generic[EntityIndexTypeVar]):
    _attr_has_entity_name = True
    _attr_name: str | None = None

    model: OmniModel | None = None
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
        self.bow_id = coordinator.data[context]["metadata"]["bow_id"]
        self.system_id = context
        self._extra_attributes = extra_attributes

    @callback  # type: ignore[misc]
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.data = cast(EntityIndexTypeVar, self.coordinator.data[self.system_id])
        self.async_write_ha_state()

    def get_config_by_systemid(self, system_id: int) -> MSPType:
        # system_id = system_id if system_id is not None else self.system_id
        return self.coordinator.data[system_id]["config"]

    def set_config(
        self,
        new_config: dict[str, str],
        system_id: int | None = None,
        coordinator_update: bool = True,
    ) -> None:
        system_id = system_id if system_id is not None else self.system_id

        _LOGGER.debug("Updating config for system ID: %s with data: %s", system_id, new_config)
        self.coordinator.data[system_id]["config"].update(new_config)
        if coordinator_update:
            self.coordinator.async_set_updated_data(self.coordinator.data)

    TelT = TypeVar(
        "TelT",
        TelemetryBackyardT,
        TelemetryBodyOfWaterT,
        TelemetryColorLogicLightT,
        TelemetryFilterT,
        TelemetryVirtualHeaterT,
        TelemetryHeaterT,
        TelemetryPumpT,
        TelemetryValveActuatorT,
        TelemetryGroupT,
    )

    def get_telemetry_by_systemid(self, system_id: int) -> TelemetryType | None:
        if self.available:
            return self.coordinator.data[system_id]["telemetry"]
        return None

    def get_system_config(self) -> MSPSystemT:
        return self.coordinator.msp_config["MSPConfig"]["System"]

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
            self.coordinator.data[self.system_id]["telemetry"].update(new_telemetry)  # type: ignore[union-attr]
        except KeyError:
            return None
        self.coordinator.async_set_updated_data(self.coordinator.data)

    @property
    def available(self) -> bool:
        return cast(EntityDataBackyardT, self.coordinator.data[BACKYARD_SYSTEM_ID])["telemetry"]["@state"] == 1

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
    def extra_state_attributes(self) -> dict[str, str | int]:
        return {
            "omni_system_id": self.system_id,
            "omni_bow_id": self.bow_id,
        }

    @property
    def name(self) -> Any:
        return self._attr_name if self._attr_name is not None else self.data["metadata"]["name"]

    @property
    def unique_id(self) -> str | None:
        return f"{self.bow_id} {self.system_id} {self.name}"
