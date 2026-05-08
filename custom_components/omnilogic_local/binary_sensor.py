from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.const import EntityCategory
from pyomnilogic_local import Backyard, Bow, Chlorinator, HeaterEquipment
from pyomnilogic_local.omnitypes import ChlorinatorAlert, ChlorinatorError, ChlorinatorStatus

from .const import DOMAIN, KEY_COORDINATOR
from .coordinator import OmniLogicCoordinator
from .entity import OmniLogicEntity
from .typing import OmniLogicEquipment

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class OmniLogicBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an OmniLogic binary sensor entity"""

    extra_state_attributes_fn: Callable[[OmniLogicEquipment], dict[str, Any]] = field(default_factory=lambda: lambda _: {})
    value_fn: Callable[[OmniLogicEquipment], bool | None]


CHLORINATOR_BINARY_SENSORS: tuple[OmniLogicBinarySensorEntityDescription, ...] = (
    OmniLogicBinarySensorEntityDescription(
        key="generating",
        name="Generating",
        value_fn=lambda equipment: equipment.is_generating if isinstance(equipment, Chlorinator) else None,
    ),
    OmniLogicBinarySensorEntityDescription(
        key="error_present",
        name="Error Present",
        device_class=BinarySensorDeviceClass.PROBLEM,
        extra_state_attributes_fn=lambda equipment: (
            {"error_messages": equipment.error_messages} if isinstance(equipment, Chlorinator) else {}
        ),
        value_fn=lambda equipment: equipment.has_error if isinstance(equipment, Chlorinator) else None,
    ),
    OmniLogicBinarySensorEntityDescription(
        key="alert_present",
        name="Alert Present",
        device_class=BinarySensorDeviceClass.PROBLEM,
        extra_state_attributes_fn=lambda equipment: (
            {"alert_messages": equipment.alert_messages} if isinstance(equipment, Chlorinator) else {}
        ),
        value_fn=lambda equipment: equipment.has_alert if isinstance(equipment, Chlorinator) else None,
    ),
    OmniLogicBinarySensorEntityDescription(
        key="super_chlorinating",
        name="Super-Chlorinating",
        value_fn=lambda equipment: (equipment.sc_mode != 0) if isinstance(equipment, Chlorinator) else None,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""
    coordinator: OmniLogicCoordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]
    entities: list[BinarySensorEntity] = []

    # Create a binary sensor entity indicating if we are in Service Mode
    entities.append(OmniLogicServiceModeBinarySensorEntity(coordinator=coordinator, equipment=coordinator.omni.backyard))

    # Create binary sensor entities for each piece of Heater-Equipment

    for _, _, heater_equipment in coordinator.omni.all_heater_equipment.items():
        entities.append(
            OmniLogicHeaterEquipBinarySensorEntity(
                coordinator=coordinator,
                equipment=heater_equipment,
            )
        )

    # Create flow binary sensors for each BoW
    for _, _, bow in coordinator.omni.backyard.bow.items():
        entities.append(
            OmniLogicFlowBinarySensorEntity(
                coordinator=coordinator,
                equipment=bow,
            )
        )

    # Create binary sensor entities for each chlorinator based on the descriptions in CHLORINATOR_BINARY_SENSORS
    for _, _, chlorinator in coordinator.omni.all_chlorinators.items():
        entities.extend(
            OmniLogicChlorinatorBinarySensorEntity(
                coordinator=coordinator,
                equipment=chlorinator,
                entity_description=description,
            )
            for description in CHLORINATOR_BINARY_SENSORS
        )

    # Create binary sensor entities for each chlorinator status, alert, and error message
    status_flags_filter: list[ChlorinatorStatus] = [
        # We create a non-diagnostic binary sensor for these as they are more commonly used
        ChlorinatorStatus.GENERATING,
        ChlorinatorStatus.ALERT_PRESENT,
        ChlorinatorStatus.ERROR_PRESENT,
    ]
    entities.extend(
        OmniLogicChlorinatorStatusBinarySensorEntity(
            coordinator=coordinator,
            equipment=chlorinator,
            needle=statusFlag,
            haystack=chlorinator.status,
        )
        for statusFlag in ChlorinatorStatus
        if statusFlag not in status_flags_filter
        for _, _, chlorinator in coordinator.omni.all_chlorinators.items()
    )
    entities.extend(
        OmniLogicChlorinatorStatusBinarySensorEntity(
            coordinator=coordinator,
            equipment=chlorinator,
            needle=statusFlag,
            haystack=chlorinator.alert_messages,
        )
        for _, _, chlorinator in coordinator.omni.all_chlorinators.items()
        for statusFlag in ChlorinatorAlert
    )
    entities.extend(
        OmniLogicChlorinatorStatusBinarySensorEntity(
            coordinator=coordinator,
            equipment=chlorinator,
            needle=statusFlag,
            haystack=chlorinator.error_messages,
        )
        for _, _, chlorinator in coordinator.omni.all_chlorinators.items()
        for statusFlag in ChlorinatorError
    )

    async_add_entities(entities)


class OmniLogicServiceModeBinarySensorEntity(OmniLogicEntity[Backyard], BinarySensorEntity):
    """Binary sensor entity for system service mode status."""

    _attr_name = "Service Mode"

    @property
    def available(self) -> bool:
        # This is one of the few things we can pull from the telemetry even if we are in service mode
        # This is only unavailable if the coordinator is unavailable (e.g. can't connect to the API at all)
        return super().available

    @property
    def is_on(self) -> bool:
        # The library returns if the system is ready, we want this sensor to indicate if we are NOT ready
        return not self.equipment.is_ready


class OmniLogicHeaterEquipBinarySensorEntity(OmniLogicEntity[HeaterEquipment], BinarySensorEntity):
    """Binary sensor entity for heater equipment running status."""

    _attr_device_class = BinarySensorDeviceClass.HEAT

    @property
    def icon(self) -> str | None:
        return "mdi:water-boiler" if self.is_on else "mdi:water-boiler-off"

    @property
    def name(self) -> str:
        return f"{self.equipment.name} Heater Equipment Status"

    @property
    def is_on(self) -> bool:
        return self.equipment.is_on


class OmniLogicFlowBinarySensorEntity(OmniLogicEntity[Bow], BinarySensorEntity):
    """Binary sensor entity for body of water flow status."""

    @property
    def icon(self) -> str | None:
        return "mdi:water-check" if self.is_on else "mdi:water-remove"

    @property
    def name(self) -> str:
        return f"{self.equipment.name} Flow"

    @property
    def is_on(self) -> bool | None:
        return self.equipment.flow


class OmniLogicChlorinatorBinarySensorEntity(OmniLogicEntity[Chlorinator], BinarySensorEntity):
    """Binary sensor entity for chlorinator generating status."""

    entity_description: OmniLogicBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: OmniLogicCoordinator,
        equipment: Chlorinator,
        entity_description: OmniLogicBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, equipment)
        self.entity_description = entity_description
        self._attr_name = f"{equipment.name} {str(entity_description.name)}" if hasattr(entity_description, "name") else None

    @property
    def _extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.extra_state_attributes_fn(self.equipment)

    @property
    def is_on(self) -> bool | None:
        # Override the cached value with a dynamic value based on the entity description function
        return self.entity_description.value_fn(self.equipment)


class OmniLogicChlorinatorStatusBinarySensorEntity(OmniLogicEntity[Chlorinator], BinarySensorEntity):
    """Binary sensor entity for chlorinator status (e.g. alerts, errors)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: OmniLogicCoordinator,
        equipment: Chlorinator,
        needle: ChlorinatorStatus | ChlorinatorAlert | ChlorinatorError,
        haystack: list[str],
    ) -> None:
        super().__init__(coordinator, equipment)
        self._needle = needle
        self._haystack = haystack
        self._attr_name = f"{self.equipment.name} {self._needle}"

    @property
    def is_on(self) -> bool | None:
        return self._needle.name in self._haystack
