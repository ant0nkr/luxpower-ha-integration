"""Tests for the per-group "data read at" timestamps."""

import asyncio
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from homeassistant.const import EntityCategory

from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient
from custom_components.lxp_modbus.const import (
    BATTERY_INFO_START_REGISTER,
    MAX_CACHED_DATA_FAILURES,
    TOTAL_REGISTERS,
)
from custom_components.lxp_modbus.constants.input_registers import I_BAT_PARALLEL_NUM
from custom_components.lxp_modbus.entity_descriptions.sensor_types import SENSOR_TYPES
from custom_components.lxp_modbus.sensor import ModbusBridgeSensor

BLOCK_SIZE = 125
INPUT_STARTS = list(range(0, TOTAL_REGISTERS, BLOCK_SIZE))


def make_client(**kwargs):
    """Build a client with a real lock and no network."""
    client = LxpModbusApiClient(
        "192.0.2.1", 8000, "BA0000000A", "0000000001", asyncio.Lock(),
        block_size=BLOCK_SIZE, connection_retries=1, skip_initial_data=False, **kwargs
    )
    client._connection_manager.async_connect = AsyncMock(return_value=(MagicMock(), MagicMock()))
    client._connection_manager.async_discard_initial_data = AsyncMock()
    client._connection_manager.async_close = AsyncMock()
    return client


def dongle(missing=(), timeout_at=None, error_at=None, batteries=0):
    """Fake register reads: every block answers with the same unchanged values."""

    async def request(writer, reader, reg, request_type, function_code):
        if reg == timeout_at and request_type == "input":
            raise asyncio.TimeoutError(f"No answer for {reg}")
        if reg == error_at and request_type == "input":
            raise ConnectionResetError("dongle dropped the connection")
        if (request_type, reg) in missing:
            return {}
        if request_type == "input/bat":
            return {"BAT1": {reg: 1}}
        block = {r: 7 for r in range(reg, min(reg + BLOCK_SIZE, TOTAL_REGISTERS))}
        if request_type == "input" and I_BAT_PARALLEL_NUM in block:
            block[I_BAT_PARALLEL_NUM] = batteries
        return block

    return request


async def poll_at(client, now, **dongle_kwargs):
    """Run one async_get_data() at a fixed wall-clock time."""
    with patch.object(client, "async_request_registers", side_effect=dongle(**dongle_kwargs)), \
            patch("custom_components.lxp_modbus.classes.modbus_client.time_lib.time", return_value=now):
        return await client.async_get_data()


class TestInputReadAt:
    """The timestamp proves a value is current even when the value did not change."""

    async def test_unknown_before_the_first_poll(self):
        client = make_client()

        assert client.get_cached_data()["meta"]["input_read_at"] is None

    async def test_complete_pass_sets_the_timestamp(self):
        client = make_client()

        data = await poll_at(client, 1000.0)

        assert data["meta"]["input_read_at"] == 1000.0

    async def test_unchanged_values_still_advance_the_timestamp(self):
        """This is the case last_reported cannot show."""
        client = make_client()
        first = await poll_at(client, 1000.0)

        second = await poll_at(client, 1060.0)

        assert second["input"] == first["input"]
        assert second["meta"]["input_read_at"] == 1060.0

    async def test_block_never_read_keeps_the_group_unknown(self):
        client = make_client()

        data = await poll_at(client, 1000.0, missing={("input", INPUT_STARTS[-1])})

        assert data["input"], "the blocks that did answer are still published"
        assert data["meta"]["input_read_at"] is None

    async def test_missing_block_holds_the_group_at_its_last_read(self):
        """A pass where one block returns nothing is reported as a successful poll."""
        client = make_client()
        await poll_at(client, 1000.0)

        data = await poll_at(client, 1060.0, missing={("input", INPUT_STARTS[1])})

        assert data["meta"]["input_read_at"] == 1000.0

    async def test_timeout_mid_pass_holds_the_group_at_the_oldest_block(self):
        client = make_client()
        await poll_at(client, 1000.0)

        data = await poll_at(client, 1060.0, timeout_at=INPUT_STARTS[2])

        assert data["meta"]["input_read_at"] == 1000.0

    async def test_group_recovers_once_every_block_is_read_again(self):
        client = make_client()
        await poll_at(client, 1000.0)
        await poll_at(client, 1060.0, timeout_at=INPUT_STARTS[2])

        data = await poll_at(client, 1120.0)

        assert data["meta"]["input_read_at"] == 1120.0

    async def test_failed_pass_records_nothing(self):
        """A pass that raises discards its data, so it must not claim a read either."""
        client = make_client()
        await poll_at(client, 1000.0)

        data = await poll_at(client, 1060.0, error_at=INPUT_STARTS[-1])

        assert data["meta"]["input_read_at"] == 1000.0
        assert client._block_read_at[("input", INPUT_STARTS[0])] == 1000.0

    async def test_cached_fallback_reports_the_old_timestamp(self):
        """Cached data keeps entities available, but is visibly not current."""
        client = make_client()
        await poll_at(client, 1000.0)
        client._connection_manager.async_connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))

        for _ in range(MAX_CACHED_DATA_FAILURES):
            data = await poll_at(client, 1060.0)
            assert data["meta"]["input_read_at"] == 1000.0


class TestBatteryReadAt:

    async def test_unknown_when_battery_data_is_not_requested(self):
        client = make_client()

        data = await poll_at(client, 1000.0, batteries=1)

        assert data["meta"]["battery_read_at"] is None

    async def test_set_when_the_battery_block_answers(self):
        client = make_client(request_battery_data=True)

        data = await poll_at(client, 1000.0, batteries=1)

        assert data["meta"]["battery_read_at"] == 1000.0

    async def test_empty_battery_block_is_not_a_read(self):
        client = make_client(request_battery_data=True)

        data = await poll_at(client, 1000.0, batteries=1,
                             missing={("input/bat", BATTERY_INFO_START_REGISTER)})

        assert data["meta"]["battery_read_at"] is None


class TestReadAtSensor:
    """The diagnostic sensors use the existing description machinery."""

    @staticmethod
    def make_sensor(name, data):
        desc = next(d for d in SENSOR_TYPES if d["name"] == name)
        coordinator = MagicMock()
        coordinator.data = data
        entry = MagicMock()
        entry.data = {}
        return ModbusBridgeSensor(coordinator, entry, desc, "lxp", None)

    def test_reports_a_utc_timestamp(self):
        sensor = self.make_sensor("Input Data Read At", {"meta": {"input_read_at": 1000.0}})

        assert sensor.native_value == datetime.fromtimestamp(1000.0, tz=timezone.utc)
        assert sensor.device_class == "timestamp"
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.entity_registry_enabled_default is False

    def test_unknown_until_every_block_is_read(self):
        sensor = self.make_sensor("Input Data Read At", {"meta": {"input_read_at": None}})

        assert sensor.native_value is None

    def test_fingerprint_follows_the_timestamp(self):
        """The sensor writes once per complete pass; value entities still skip."""
        sensor = self.make_sensor("Input Data Read At", {"meta": {"input_read_at": 1000.0}})
        first = sensor._source_fingerprint()

        sensor.coordinator.data = {"meta": {"input_read_at": 1060.0}}

        assert sensor._source_fingerprint() != first

    def test_battery_sensor_is_grouped_with_the_battery(self):
        sensor = self.make_sensor("Battery Data Read At", {"meta": {"battery_read_at": 1000.0}})

        assert sensor._desc["device_group"] == "Battery"
        assert sensor.native_value == datetime.fromtimestamp(1000.0, tz=timezone.utc)
