"""Tests for how a write is confirmed against the inverter.

Issue #154: on v1.1.0-beta.1 a switch took ~30 s to settle. The inverter had the
new value within a second, but the confirmation went through a full coordinator
refresh, which re-reads every input block and then every settings block. The
service call stayed blocked for the whole poll, so automations serialised at
~30 s per step.

The write acknowledgement already echoes the stored value, and the settings block
that changed is one request on the connection the write just used.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient


def make_client(**kwargs):
    return LxpModbusApiClient(
        "192.0.2.1", 8000, "BA0000000A", "0000000001", asyncio.Lock(), **kwargs
    )


@pytest.fixture
def reader_writer():
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)
    writer.write = MagicMock()
    reader.read = AsyncMock(return_value=b"\x00" * 76)
    return reader, writer


def accepted_response(register, value):
    """A parsed acknowledgement echoing what the inverter stored."""
    return MagicMock(
        packet_error=False,
        device_function=6,
        exception=0,
        register=register,
        parsed_values_dictionary={register: value},
        info="",
    )


async def write_with(client, reader, writer, register, value, reread=None):
    """Run a write against mocked transport, stubbing the post-write re-read."""
    with patch('asyncio.open_connection', return_value=(reader, writer)):
        with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse',
                   return_value=accepted_response(register, value)):
            with patch.object(client, 'async_request_registers',
                              AsyncMock(return_value=reread if reread is not None else {})) as read:
                result = await client.async_write_register(register, value)
    return result, read


class TestConfirmationCost:
    """Confirming a write must not cost a full poll."""

    @pytest.mark.asyncio
    async def test_only_the_affected_settings_block_is_re_read(self, reader_writer):
        """One request, not one per block: the block containing the register."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1, block_size=40)

        result, read = await write_with(client, reader, writer, 21, 62404, reread={21: 62404})

        assert result is True
        read.assert_awaited_once()
        _writer, _reader, start, request_type, function_code = read.await_args.args
        assert (start, request_type, function_code) == (0, "hold", 3)

    @pytest.mark.asyncio
    async def test_re_read_starts_at_the_block_holding_the_register(self, reader_writer):
        """Blocks are aligned the same way the poller aligns them."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1, block_size=125)

        _result, read = await write_with(client, reader, writer, 261, 80, reread={261: 80})

        assert read.await_args.args[2] == 250

    @pytest.mark.asyncio
    async def test_re_read_uses_the_write_connection(self, reader_writer):
        """A second connection would cost the dongle another handshake."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1)

        with patch('asyncio.open_connection', return_value=(reader, writer)) as connect:
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse',
                       return_value=accepted_response(21, 1)):
                with patch.object(client, 'async_request_registers',
                                  AsyncMock(return_value={21: 1})):
                    await client.async_write_register(21, 1)

        assert connect.call_count == 1

    @pytest.mark.asyncio
    async def test_confirmed_write_does_not_force_a_full_settings_poll(self, reader_writer):
        """The value is already known, so the next poll keeps its normal shape."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1)
        client._force_hold_poll = False

        await write_with(client, reader, writer, 21, 62404, reread={21: 62404})

        assert client._force_hold_poll is False


class TestConfirmedValueReachesTheCache:
    """Whatever the inverter reports has to be what entities read."""

    @pytest.mark.asyncio
    async def test_re_read_values_are_cached(self, reader_writer):
        """A write can move sibling settings, so the whole block is kept."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1)

        await write_with(client, reader, writer, 21, 62404, reread={21: 62404, 22: 7})

        assert client.get_cached_data()["hold"] == {21: 62404, 22: 7}

    @pytest.mark.asyncio
    async def test_acknowledged_value_is_cached_without_the_re_read(self, reader_writer):
        """The acknowledgement echoes the stored value, so it stands on its own."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1)

        await write_with(client, reader, writer, 21, 62404, reread={})

        assert client.get_cached_data()["hold"][21] == 62404

    @pytest.mark.asyncio
    async def test_failed_re_read_falls_back_to_the_next_poll(self, reader_writer):
        """A re-read that returns nothing must not leave siblings unchecked."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1)
        client._force_hold_poll = False

        await write_with(client, reader, writer, 21, 62404, reread={})

        assert client._force_hold_poll is True

    @pytest.mark.asyncio
    async def test_re_read_timeout_does_not_undo_a_confirmed_write(self, reader_writer):
        """The inverter accepted it; a failed follow-up read is not a write failure."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1)

        with patch('asyncio.open_connection', return_value=(reader, writer)):
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse',
                       return_value=accepted_response(21, 1)):
                with patch.object(client, 'async_request_registers',
                                  AsyncMock(side_effect=asyncio.TimeoutError)):
                    result = await client.async_write_register(21, 1)

        assert result is True
        assert client._force_hold_poll is True

    @pytest.mark.asyncio
    async def test_rejected_write_is_not_cached(self, reader_writer):
        """Only confirmed values may reach the cache."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1)
        mismatch = MagicMock(
            packet_error=False, device_function=6, exception=0, register=21,
            parsed_values_dictionary={21: 0}, info="",
        )

        with patch('asyncio.open_connection', return_value=(reader, writer)):
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse',
                       return_value=mismatch):
                with patch.object(client, 'async_request_registers', AsyncMock()) as read:
                    assert await client.async_write_register(21, 1) is False

        assert client.get_cached_data()["hold"] == {}
        read.assert_not_awaited()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
