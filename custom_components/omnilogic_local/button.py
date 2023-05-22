from __future__ import annotations

from collections.abc import Sequence
import logging
from typing import TYPE_CHECKING, Literal, TypeVar

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN, KEY_COORDINATOR, OmniModel, OmniType
from .entity import OmniLogicEntity
from .types.entity_index import EntityDataFilterT, EntityDataPumpT
from .utils import get_entities_of_omni_types, get_omni_model

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OmniLogicCoordinator

_LOGGER = logging.getLogger(__name__)

SpeedT = Literal["Vsp_Low_Pump_Speed", "Vsp_Medium_Pump_Speed", "Vsp_High_Pump_Speed"]
SPEED_NAMES: Sequence[SpeedT] = ["Vsp_Low_Pump_Speed", "Vsp_Medium_Pump_Speed", "Vsp_High_Pump_Speed"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the switch platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATOR]

    all_pumps = get_entities_of_omni_types(coordinator.data, [OmniType.FILTER, OmniType.PUMP])

    entities = []
    for system_id, pump in all_pumps.items():
        pump_type = get_omni_model(pump)

        for speed in SPEED_NAMES:
            _LOGGER.debug(
                "Configuring button for pump with ID: %s, Name: %s, Speed: %s",
                pump["metadata"]["system_id"],
                pump["metadata"]["name"],
                speed,
            )
            match pump_type:
                case OmniModel.VARIABLE_SPEED_PUMP:
                    entities.append(OmniLogicPumpButtonEntity(coordinator=coordinator, context=system_id, speed=speed))
                case OmniModel.VARIABLE_SPEED_FILTER:
                    entities.append(OmniLogicFilterButtonEntity(coordinator=coordinator, context=system_id, speed=speed))

    async_add_entities(entities)


T = TypeVar("T", EntityDataFilterT, EntityDataPumpT)


class OmniLogicButtonEntity(OmniLogicEntity[T], ButtonEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    speed: SpeedT
    telem_key_speed: Literal["@pumpSpeed", "@filterSpeed"]
    telem_key_state: Literal["@pumpState", "@filterState"]

    @property
    def name(self) -> str:
        match self.speed:
            case "Vsp_Low_Pump_Speed":
                return f"{self.data['metadata']['name']} Low Speed"
            case "Vsp_Medium_Pump_Speed":
                return f"{self.data['metadata']['name']} Medium Speed"
            case "Vsp_High_Pump_Speed":
                return f"{self.data['metadata']['name']} High Speed"

    @property
    def omni_speed(self) -> int:
        return self.data["config"][self.speed]

    async def async_press(self) -> None:
        await self.coordinator.omni_api.async_set_equipment(self.bow_id, self.system_id, self.omni_speed)

        self.set_telemetry({self.telem_key_speed: self.omni_speed, self.telem_key_state: 1})


class OmniLogicPumpButtonEntity(OmniLogicButtonEntity[EntityDataPumpT]):
    telem_key_speed = "@pumpSpeed"
    telem_key_state = "@pumpState"

    def __init__(self, coordinator: OmniLogicCoordinator, context: int, speed: SpeedT) -> None:
        # It is important that the speed and data members are assigned BEFORE we run the __init__ as they are used to
        # determine the name of the button inside the base class
        self.speed: SpeedT = speed
        super().__init__(coordinator, context)


class OmniLogicFilterButtonEntity(OmniLogicButtonEntity[EntityDataFilterT]):
    telem_key_speed = "@filterSpeed"
    telem_key_state = "@filterState"

    def __init__(self, coordinator: OmniLogicCoordinator, context: int, speed: SpeedT) -> None:
        # It is important that the speed and data members are assigned BEFORE we run the __init__ as they are used to
        # determine the name of the button inside the base class
        self.speed: SpeedT = speed
        super().__init__(coordinator, context)
