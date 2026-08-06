"""Tests for diagnostics output and module importability."""

import importlib
import pytest
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.const import DOMAIN
from custom_components.lxp_modbus.diagnostics import async_get_config_entry_diagnostics

ENTRY_ID = "test_entry_id"

# Every module in the integration, so an import-time error in a file without unit
# tests (platforms, config flow, diagnostics) still fails the suite.
INTEGRATION_MODULES = [
    "custom_components.lxp_modbus",
    "custom_components.lxp_modbus.binary_sensor",
    "custom_components.lxp_modbus.button",
    "custom_components.lxp_modbus.config_flow",
    "custom_components.lxp_modbus.const",
    "custom_components.lxp_modbus.coordinator",
    "custom_components.lxp_modbus.diagnostics",
    "custom_components.lxp_modbus.entity",
    "custom_components.lxp_modbus.number",
    "custom_components.lxp_modbus.select",
    "custom_components.lxp_modbus.sensor",
    "custom_components.lxp_modbus.switch",
    "custom_components.lxp_modbus.time",
    "custom_components.lxp_modbus.utils",
    "custom_components.lxp_modbus.classes.connection_manager",
    "custom_components.lxp_modbus.classes.data_validator",
    "custom_components.lxp_modbus.classes.inverter_discovery",
    "custom_components.lxp_modbus.classes.lxp_batteries",
    "custom_components.lxp_modbus.classes.lxp_packet_utils",
    "custom_components.lxp_modbus.classes.lxp_request_builder",
    "custom_components.lxp_modbus.classes.lxp_response",
    "custom_components.lxp_modbus.classes.modbus_client",
    "custom_components.lxp_modbus.classes.packet_recovery",
    "custom_components.lxp_modbus.entity_descriptions.binary_sensor_types",
    "custom_components.lxp_modbus.entity_descriptions.button_types",
    "custom_components.lxp_modbus.entity_descriptions.number_types",
    "custom_components.lxp_modbus.entity_descriptions.selectbox_types",
    "custom_components.lxp_modbus.entity_descriptions.sensor_types",
    "custom_components.lxp_modbus.entity_descriptions.switch_types",
    "custom_components.lxp_modbus.entity_descriptions.time_types",
]


@pytest.mark.parametrize("module_name", INTEGRATION_MODULES)
def test_module_imports(module_name):
    """Every module must import cleanly."""
    assert importlib.import_module(module_name) is not None


@pytest.fixture
def hass_with_entry():
    """Mock hass populated the way async_setup_entry populates it."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.update_interval = None
    coordinator.failed_updates = 0
    coordinator.is_recovering = False
    coordinator.last_success = 1234567890.0
    coordinator.data = {
        "input": {0: 100},
        "hold": {21: 1},
        "battery": {"BATTERY01": {5000: 7}},
    }

    api_client = MagicMock()
    api_client.get_connection_stats = MagicMock(return_value={
        "host": "192.168.1.50",
        "port": 8000,
        "consecutive_failures": 0,
    })
    api_client.get_recovery_stats = MagicMock(return_value={"total_recovery_attempts": 0})

    hass = MagicMock()
    hass.data = {DOMAIN: {ENTRY_ID: {
        "coordinator": coordinator,
        "api_client": api_client,
        "platforms": ["sensor"],
    }}}
    return hass


@pytest.fixture
def entry():
    """Mock config entry with secrets in its data."""
    cfg = MagicMock()
    cfg.entry_id = ENTRY_ID
    cfg.title = "Test Inverter"
    cfg.version = 1
    cfg.data = {
        "host": "192.168.1.50",
        "port": 8000,
        "dongle_serial": "BA12345678",
        "inverter_serial": "1234567890",
        "poll_interval": 60,
    }
    cfg.options = {}
    return cfg


class TestDiagnostics:
    """Config entry diagnostics."""

    @pytest.mark.asyncio
    async def test_redacts_host_and_serials(self, hass_with_entry, entry):
        """Diagnostics can be attached to a public issue, so identifiers are hidden."""
        result = await async_get_config_entry_diagnostics(hass_with_entry, entry)

        data = result["entry"]["data"]
        assert data["host"] != "192.168.1.50"
        assert data["dongle_serial"] != "BA12345678"
        assert data["inverter_serial"] != "1234567890"
        # Non-identifying settings are kept, or the dump is useless
        assert data["poll_interval"] == 60
        assert result["connection"]["host"] != "192.168.1.50"
        assert result["connection"]["port"] == 8000

    @pytest.mark.asyncio
    async def test_includes_registers_with_string_keys(self, hass_with_entry, entry):
        """Register maps are keyed by int, which JSON cannot represent."""
        result = await async_get_config_entry_diagnostics(hass_with_entry, entry)

        assert result["registers"]["input"] == {"0": 100}
        assert result["registers"]["hold"] == {"21": 1}
        assert result["registers"]["battery"] == {"BATTERY01": {"5000": 7}}

    @pytest.mark.asyncio
    async def test_includes_coordinator_health(self, hass_with_entry, entry):
        """The failure counters are the reason this dump exists."""
        result = await async_get_config_entry_diagnostics(hass_with_entry, entry)

        assert result["coordinator"]["last_update_success"] is True
        assert result["coordinator"]["failed_updates"] == 0
        assert result["coordinator"]["is_recovering"] is False
        assert result["packet_recovery"] == {"total_recovery_attempts": 0}

    @pytest.mark.asyncio
    async def test_survives_missing_runtime_data(self, entry):
        """Diagnostics must still work for an entry that failed to set up."""
        hass = MagicMock()
        hass.data = {}

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert "entry" in result
        assert "coordinator" not in result
        assert "connection" not in result

    @pytest.mark.asyncio
    async def test_is_json_serialisable(self, hass_with_entry, entry):
        """A dump that cannot be serialised is not a dump."""
        import json

        result = await async_get_config_entry_diagnostics(hass_with_entry, entry)

        assert json.dumps(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
