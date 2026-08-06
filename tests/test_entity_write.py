"""Tests for the shared entity write path and number scaling."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.const import DOMAIN
from custom_components.lxp_modbus.number import ModbusBridgeNumber
from custom_components.lxp_modbus.switch import ModbusBridgeSwitch
from custom_components.lxp_modbus.utils import get_bits, set_bits

ENTRY_ID = "test_entry_id"


@pytest.fixture
def api_client():
    """Mock API client that reports successful writes."""
    client = AsyncMock()
    client.async_write_register = AsyncMock(return_value=True)
    return client


@pytest.fixture
def entry():
    """Mock config entry."""
    cfg = MagicMock()
    cfg.entry_id = ENTRY_ID
    cfg.title = "Test Inverter"
    cfg.data = {}
    return cfg


@pytest.fixture
def coordinator():
    """Mock coordinator holding a real data dict and a real write lock."""
    coord = MagicMock()
    coord.data = {"hold": {}, "input": {}}
    coord.async_request_refresh = AsyncMock()
    coord.hass = MagicMock()
    coord.hass.data = {DOMAIN: {ENTRY_ID: {"write_lock": asyncio.Lock()}}}
    return coord


NUMBER_DESC = {
    "name": "Battery Stop Charging Voltage",
    "register": 228,
    "register_type": "hold",
    "min": 40.0,
    "max": 59.5,
    "step": 0.1,
    "unit": "V",
    "multiplier": 10,
    "master_only": False,
}

# Two switches packed into one register, as with H_FUNCTION_ENABLE_1
SWITCH_A_DESC = {
    "name": "AC Charging",
    "register": 21,
    "register_type": "hold",
    "extract": lambda value: get_bits(value, 0, 1),
    "compose": lambda orig, value: set_bits(orig, 0, 1, value),
    "master_only": False,
}
SWITCH_B_DESC = {
    "name": "Forced Discharge",
    "register": 21,
    "register_type": "hold",
    "extract": lambda value: get_bits(value, 3, 1),
    "compose": lambda orig, value: set_bits(orig, 3, 1, value),
    "master_only": False,
}


def make_number(coordinator, entry, api_client, desc=None):
    """Build a number entity with async_write_ha_state stubbed out."""
    entity = ModbusBridgeNumber(coordinator, entry, dict(desc or NUMBER_DESC), "lxp", api_client)
    entity.async_write_ha_state = MagicMock()
    return entity


def make_switch(coordinator, entry, api_client, desc):
    """Build a switch entity with async_write_ha_state stubbed out."""
    entity = ModbusBridgeSwitch(coordinator, entry, dict(desc), "lxp", api_client)
    entity.async_write_ha_state = MagicMock()
    return entity


class TestNumberValueHandling:
    """Scaling and range handling for number entities."""

    def test_native_value_scales_register(self, coordinator, entry, api_client):
        """A register value inside the declared range is scaled for display."""
        coordinator.data["hold"][228] = 585
        entity = make_number(coordinator, entry, api_client)

        assert entity.native_value == 58.5

    def test_native_value_rejects_unimplemented_register(self, coordinator, entry, api_client):
        """A register the inverter does not implement reads 0xFFFF, not 6553.5 V."""
        coordinator.data["hold"][228] = 0xFFFF
        entity = make_number(coordinator, entry, api_client)

        assert entity.native_value is None

    def test_native_value_reports_zero(self, coordinator, entry, api_client):
        """0 is below the documented minimum but means "not configured", not garbage.

        Real hardware holds 0 in many of these settings; hiding it loses real data.
        """
        coordinator.data["hold"][228] = 0
        entity = make_number(coordinator, entry, api_client)

        assert entity.native_value == 0

    def test_native_value_reports_above_documented_maximum(self, coordinator, entry, api_client):
        """Firmware reports values the documentation does not list (e.g. SOC 101%)."""
        coordinator.data["hold"][228] = 600  # 60.0 V, above the declared 59.5 max
        entity = make_number(coordinator, entry, api_client)

        assert entity.native_value == 60.0

    def test_native_value_missing_register(self, coordinator, entry, api_client):
        """An absent register reads as unknown."""
        entity = make_number(coordinator, entry, api_client)

        assert entity.native_value is None

    def test_native_value_keeps_minus_one_on_signed_register(self, coordinator, entry, api_client):
        """0xFFFF is -1 on a signed register, not an unimplemented register.

        Registers like the external CT power offset are signed, so the
        unimplemented-register check must not swallow -1.
        """
        signed_desc = {
            "name": "External CT Power Offset",
            "register": 119,
            "register_type": "hold",
            "min": -32768,
            "max": 32767,
            "step": 1,
            "unit": "W",
            "multiplier": 1,
            "extract": lambda value: value if value < 32768 else value - 65536,
            "compose": lambda orig, value: value if value >= 0 else value + 65536,
            "master_only": False,
        }
        coordinator.data["hold"][119] = 0xFFFF
        entity = make_number(coordinator, entry, api_client, signed_desc)

        assert entity.native_value == -1

    def test_native_value_converts_signed_temperature(self, coordinator, entry, api_client):
        """Observed on hardware: raw 65336 is -20.0 C, not 6533.6 C."""
        temp_desc = {
            "name": "Lead-Acid Discharge Temp Low Limit",
            "register": 106,
            "register_type": "hold",
            "min": -40.0,
            "max": 100.0,
            "step": 0.1,
            "unit": "°C",
            "multiplier": 10,
            "extract": lambda value: value if value < 32768 else value - 65536,
            "compose": lambda orig, value: value if value >= 0 else value + 65536,
            "master_only": False,
        }
        coordinator.data["hold"][106] = 65336
        entity = make_number(coordinator, entry, api_client, temp_desc)

        assert entity.native_value == -20.0

    @pytest.mark.asyncio
    async def test_set_value_rounds_instead_of_truncating(self, coordinator, entry, api_client):
        """58.1 * 10 is 580.999... in binary, so truncation would write 580."""
        entity = make_number(coordinator, entry, api_client)

        await entity.async_set_native_value(58.1)

        api_client.async_write_register.assert_awaited_once_with(228, 581)

    @pytest.mark.asyncio
    async def test_set_value_exact_multiple(self, coordinator, entry, api_client):
        """Values that scale exactly are unaffected by the rounding."""
        entity = make_number(coordinator, entry, api_client)

        await entity.async_set_native_value(59.5)

        api_client.async_write_register.assert_awaited_once_with(228, 595)


class TestSharedWritePath:
    """Behaviour of ModbusBridgeEntity._async_write_register."""

    @pytest.mark.asyncio
    async def test_write_updates_cache_and_requests_refresh(self, coordinator, entry, api_client):
        """A successful write is shown immediately and then re-checked against the inverter."""
        coordinator.data["hold"][21] = 0
        entity = make_switch(coordinator, entry, api_client, SWITCH_A_DESC)

        await entity.async_turn_on()

        api_client.async_write_register.assert_awaited_once_with(21, 1)
        assert coordinator.data["hold"][21] == 1
        entity.async_write_ha_state.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failed_write_leaves_cache_untouched(self, coordinator, entry, api_client):
        """A rejected write must not be reflected in the reported state."""
        coordinator.data["hold"][21] = 0
        api_client.async_write_register = AsyncMock(return_value=False)
        entity = make_switch(coordinator, entry, api_client, SWITCH_A_DESC)

        await entity.async_turn_on()

        assert coordinator.data["hold"][21] == 0
        entity.async_write_ha_state.assert_not_called()
        coordinator.async_request_refresh.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_api_client_is_reported_not_raised(self, coordinator, entry):
        """Read-only entities have no client; writing must fail quietly."""
        entity = make_switch(coordinator, entry, None, SWITCH_A_DESC)

        await entity.async_turn_on()

        coordinator.async_request_refresh.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_concurrent_writes_on_shared_register_do_not_clobber(
        self, coordinator, entry, api_client
    ):
        """Two switches in one register must both survive simultaneous writes.

        Without the shared lock both compose from the same pre-write snapshot and
        the second write erases the first one's bit.
        """
        coordinator.data["hold"][21] = 0
        written = []

        async def slow_write(register, value):
            # Force the two writes to overlap if they are not serialised.
            await asyncio.sleep(0)
            written.append((register, value))
            return True

        api_client.async_write_register = AsyncMock(side_effect=slow_write)

        switch_a = make_switch(coordinator, entry, api_client, SWITCH_A_DESC)
        switch_b = make_switch(coordinator, entry, api_client, SWITCH_B_DESC)

        await asyncio.gather(switch_a.async_turn_on(), switch_b.async_turn_on())

        # bit 0 and bit 3 both set
        assert coordinator.data["hold"][21] == 0b1001
        assert switch_a.is_on is True
        assert switch_b.is_on is True
        assert len(written) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
