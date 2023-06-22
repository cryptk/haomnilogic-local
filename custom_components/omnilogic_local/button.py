from __future__ import annotations

from collections.abc import Sequence
import logging
from typing import TYPE_CHECKING, Final, Literal, TypeVar

from pyomnilogic_local.types import (
    FilterState,
    FilterType,
    OmniType,
    PumpState,
    PumpType,
)

from homeassistant.components.button import ButtonEntity

from .const import BACKYARD_SYSTEM_ID, DOMAIN, KEY_COORDINATOR
from .entity import OmniLogicEntity
from .types.entity_index import EntityIndexBackyard, EntityIndexFilter, EntityIndexPump
from .utils import get_entities_of_omni_types

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)

SpeedT = Literal["low", "medium", "high"]
SPEED_NAMES: Final[Sequence[SpeedT]] = ["low", "medium", "high"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_pumps = get_entities_of_omni_types(coordinator.data, [OmniType.FILTER, OmniType.PUMP])

    entities = []
    for system_id, pump in all_pumps.items():
        for speed in SPEED_NAMES:
            _LOGGER.debug(
                "Configuring button for pump with ID: %s, Name: %s, Speed: %s",
                pump.msp_config.system_id,
                pump.msp_config.name,
                speed,
            )
            match pump.msp_config.type:
                case PumpType.VARIABLE_SPEED:
                    entities.append(OmniLogicPumpButtonEntity(coordinator=coordinator, context=system_id, speed=speed))
                case FilterType.VARIABLE_SPEED:
                    entities.append(OmniLogicFilterButtonEntity(coordinator=coordinator, context=system_id, speed=speed))

    async_add_entities(entities)

    _LOGGER.debug("Configuring button for restore idle with ID: %s", BACKYARD_SYSTEM_ID)
    entities.append(OmniLogicIdleButtonEntity(coordinator=coordinator, context=BACKYARD_SYSTEM_ID))


T = TypeVar("T", EntityIndexFilter, EntityIndexPump)


class OmniLogicSpeedPresetButtonEntity(OmniLogicEntity[T], ButtonEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    speed: SpeedT

    on_state: PumpState | FilterState

    def __init__(self, coordinator: OmniLogicCoordinator, context: int, speed: SpeedT) -> None:
        # It is important that the speed and data members are assigned BEFORE we run the __init__ as they are used to
        # determine the name of the button
        self.speed: SpeedT = speed
        super().__init__(coordinator, context)

    @property
    def icon(self) -> str:
        match self.speed:
            case "low":
                return "mdi:speedometer-slow"
            case "medium":
                return "mdi:speedometer-medium"
            case "high":
                return "mdi:speedometer"

    @property
    def name(self) -> str:
        return f"{self.data.msp_config.name} {self.speed.capitalize()} Speed"

    @property
    def omni_speed(self) -> int:
        match self.speed:
            case "low":
                return self.data.msp_config.low_speed
            case "medium":
                return self.data.msp_config.medium_speed
            case "high":
                return self.data.msp_config.high_speed

    async def async_press(self) -> None:
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, self.omni_speed)

        self.set_telemetry({"speed": self.omni_speed, "state": self.on_state})

    @property
    def extra_state_attributes(self) -> dict[str, str | int]:
        return super().extra_state_attributes | {"speed": self.omni_speed}


class OmniLogicPumpButtonEntity(OmniLogicSpeedPresetButtonEntity[EntityIndexPump]):
    on_state = PumpState.ON


class OmniLogicFilterButtonEntity(OmniLogicSpeedPresetButtonEntity[EntityIndexFilter]):
    on_state = FilterState.ON


class OmniLogicIdleButtonEntity(OmniLogicEntity[EntityIndexBackyard], ButtonEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator: OmniLogicCoordinator, context: int) -> None:
        super().__init__(coordinator, context)

    @property
    def name(self) -> str:
        return "Restore Idle"

    async def async_press(self) -> None:
        await self.coordinator.omni_api.async_restore_idle_state()
