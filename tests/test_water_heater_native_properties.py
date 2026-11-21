"""Issue #278: the water heater entity must use the native_* temperature API (HA 2026.11 deprecates the legacy names, they stop working in 2027.11)."""

from __future__ import annotations

import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEPRECATION_RECORDS: list[str] = []


def _module(name: str, **attrs: object) -> types.ModuleType:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_homeassistant_stubs() -> None:
    # Minimal homeassistant stubs: the native_* API is the real one on HA 2026.11.
    ha = _module("homeassistant")

    class _Platform:
        BINARY_SENSOR, BUTTON, LIGHT, NUMBER = "binary_sensor", "button", "light", "number"
        SELECT, SENSOR, SWITCH, VALVE, WATER_HEATER = "select", "sensor", "switch", "valve", "water_heater"

    class _UnitOfTemperature:
        CELSIUS, FAHRENHEIT = "°C", "°F"

    class _UpdateFailed(Exception):
        pass

    class _DataUpdateCoordinator:
        def __init__(self, *args, **kwargs) -> None:
            self.last_update_success = True

        __class_getitem__ = classmethod(lambda cls, item: cls)

    class _CoordinatorEntity(_DataUpdateCoordinator):
        def __init__(self, coordinator) -> None:
            self.coordinator = coordinator
            self.last_update_success = True

        __class_getitem__ = classmethod(lambda cls, item: cls)

        @property
        def available(self) -> bool:
            return self.coordinator.last_update_success

    class _WaterHeaterEntityFeature:
        TARGET_TEMPERATURE, OPERATION_MODE, ON_OFF = 1, 2, 4

    class _WaterHeaterEntity:
        _attr_native_temperature_unit: str = ""
        _attr_native_current_temperature: float | None = None
        _attr_native_target_temperature: float | None = None

        def __init_subclass__(cls, **kwargs: object) -> None:
            super().__init_subclass__(**kwargs)
            for legacy, native in (
                ("temperature_unit", "native_temperature_unit"),
                ("current_temperature", "native_current_temperature"),
                ("target_temperature", "native_target_temperature"),
            ):
                if any(legacy in vars(base) for base in cls.__mro__ if base is not _WaterHeaterEntity):
                    DEPRECATION_RECORDS.append(f"{cls.__name__} provides the deprecated {legacy}, use {native} instead")

        @property
        def native_temperature_unit(self) -> str:
            return getattr(self, "_attr_native_temperature_unit", "")

        @property
        def native_current_temperature(self) -> float | None:
            return getattr(self, "_attr_native_current_temperature", None)

        @property
        def native_target_temperature(self) -> float | None:
            return getattr(self, "_attr_native_target_temperature", None)

    const = _module(
        "homeassistant.const",
        CONF_IP_ADDRESS="ip_address",
        CONF_NAME="name",
        CONF_PORT="port",
        CONF_SCAN_INTERVAL="scan_interval",
        CONF_TIMEOUT="timeout",
        ATTR_TEMPERATURE="temperature",
        STATE_OFF="off",
        STATE_ON="on",
        Platform=_Platform,
        UnitOfTemperature=_UnitOfTemperature,
    )
    components = _module("homeassistant.components")
    helpers = _module("homeassistant.helpers")
    exceptions = _module("homeassistant.exceptions", ConfigEntryNotReady=type("ConfigEntryNotReady", (Exception,), {}))
    core = _module("homeassistant.core", callback=lambda func: func, HomeAssistant=type("HomeAssistant", (), {}))
    device_registry = _module("homeassistant.helpers.device_registry", DeviceInfo=dict, async_get=lambda *args, **kwargs: None)
    entity_registry = _module("homeassistant.helpers.entity_registry", async_get=lambda *args, **kwargs: None)
    update_coordinator = _module(
        "homeassistant.helpers.update_coordinator",
        CoordinatorEntity=_CoordinatorEntity,
        DataUpdateCoordinator=_DataUpdateCoordinator,
        UpdateFailed=_UpdateFailed,
    )
    water_heater = _module(
        "homeassistant.components.water_heater",
        WaterHeaterEntity=_WaterHeaterEntity,
        WaterHeaterEntityFeature=_WaterHeaterEntityFeature,
    )
    for parent, child in ((ha, const), (ha, exceptions), (ha, core), (ha, helpers), (ha, components),
                          (helpers, device_registry), (helpers, entity_registry), (helpers, update_coordinator),
                          (components, water_heater)):
        setattr(parent, child.__name__.rpartition(".")[2], child)


_install_homeassistant_stubs()

from custom_components.omnilogic_local.water_heater import OmniLogicWaterHeaterEntity  # noqa: E402


def _make_entity() -> OmniLogicWaterHeaterEntity:
    equipment = types.SimpleNamespace(bow_id=7, system_id=1, omni_type="Heater", name="Heater", current_set_point=85, is_on=True)
    bow = types.SimpleNamespace(water_temp=87)
    coordinator = types.SimpleNamespace(omni=types.SimpleNamespace(all_bows={7: bow}), last_update_success=True)
    return OmniLogicWaterHeaterEntity(coordinator=coordinator, equipment=equipment)


def test_water_heater_entity_does_not_provide_deprecated_members():
    assert DEPRECATION_RECORDS == []  # HA 2026.11 warns for every legacy member provided


def test_water_heater_entity_provides_native_members():
    for native in ("native_temperature_unit", "native_current_temperature", "native_target_temperature"):
        assert native in OmniLogicWaterHeaterEntity.__dict__


def test_water_heater_entity_reports_values_through_native_api():
    entity = _make_entity()
    assert entity.native_temperature_unit == "°F"
    assert entity.native_target_temperature == 85
    assert entity.native_current_temperature == 87
