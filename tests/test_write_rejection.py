"""Tests for how an inverter's refusal of a write is reported.

Issues #136, #140 and #144 all reported "cannot set X" with logs showing
function=134 and Exception=3. That is a Modbus exception response: the inverter
received the write and refused it. It was being logged as a confirmation mismatch,
which reads like a bug in the integration, and then retried twice more for nothing.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient
from custom_components.lxp_modbus.classes.lxp_request_builder import LxpRequestBuilder
from custom_components.lxp_modbus.const import MODBUS_EXCEPTION_MESSAGES


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


def rejection_response(register, exception_code):
    """A parsed response standing in for a Modbus exception reply."""
    return MagicMock(
        packet_error=False,
        device_function=0x86,          # 0x06 | 0x80, as seen in the issue logs
        exception=exception_code,
        register=register,
        parsed_values_dictionary={},
        info=f"Exception={exception_code} function=134 register={register}",
    )


class TestRejectedWrite:
    """A refused write is reported as a refusal and not retried."""

    @pytest.mark.asyncio
    async def test_rejected_write_returns_false(self, reader_writer):
        reader, writer = reader_writer
        client = make_client(connection_retries=3)

        with patch('asyncio.open_connection', return_value=(reader, writer)):
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse',
                       return_value=rejection_response(168, 3)):
                assert await client.async_write_register(168, 18) is False

    @pytest.mark.asyncio
    async def test_rejected_write_is_not_retried(self, reader_writer):
        """Retrying a refusal cannot help and hammers a dongle for nothing."""
        reader, writer = reader_writer
        client = make_client(connection_retries=3)

        with patch('asyncio.open_connection', return_value=(reader, writer)) as connect:
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse',
                       return_value=rejection_response(168, 3)):
                await client.async_write_register(168, 18)

        assert connect.call_count == 1, "a refused write must be attempted only once"

    @pytest.mark.asyncio
    async def test_rejection_reason_is_logged(self, reader_writer, caplog):
        """The log must say the inverter refused it, and why."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1)

        with caplog.at_level("ERROR"):
            with patch('asyncio.open_connection', return_value=(reader, writer)):
                with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse',
                           return_value=rejection_response(261, 3)):
                    await client.async_write_register(261, 80)

        assert "rejected" in caplog.text
        assert "illegal data value" in caplog.text
        assert "confirmation mismatch" not in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_unknown_exception_code_still_reported(self, reader_writer, caplog):
        """An unmapped code must not turn into a KeyError."""
        reader, writer = reader_writer
        client = make_client(connection_retries=1)

        with caplog.at_level("ERROR"):
            with patch('asyncio.open_connection', return_value=(reader, writer)):
                with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse',
                           return_value=rejection_response(100, 99)):
                    assert await client.async_write_register(100, 1) is False

        assert "unknown exception code 99" in caplog.text

    @pytest.mark.asyncio
    async def test_retryable_failure_is_still_retried(self, reader_writer):
        """Only refusals stop the retries; transient failures keep them."""
        reader, writer = reader_writer
        client = make_client(connection_retries=3)
        packet_error = MagicMock(
            packet_error=True, device_function=6, exception=0,
            parsed_values_dictionary={}, info="bad packet",
        )

        with patch('asyncio.open_connection', return_value=(reader, writer)) as connect:
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse',
                       return_value=packet_error):
                assert await client.async_write_register(100, 1) is False

        assert connect.call_count == 3

    def test_every_standard_exception_code_has_a_message(self):
        for code in (1, 2, 3, 4, 6):
            assert code in MODBUS_EXCEPTION_MESSAGES
            assert len(MODBUS_EXCEPTION_MESSAGES[code]) > 10


class TestRequestBuilderGuards:
    """Issue #129: an out-of-range count produced an unexplained polling failure."""

    def test_negative_register_count_is_rejected_clearly(self):
        with pytest.raises(ValueError, match="register_count"):
            LxpRequestBuilder.prepare_packet_for_read(
                b"BA0000000A", b"0000000001", 0, -5, 4
            )

    def test_zero_register_count_is_rejected(self):
        with pytest.raises(ValueError, match="register_count"):
            LxpRequestBuilder.prepare_packet_for_read(
                b"BA0000000A", b"0000000001", 0, 0, 4
            )

    def test_negative_start_register_is_rejected_clearly(self):
        with pytest.raises(ValueError, match="start_register"):
            LxpRequestBuilder.prepare_packet_for_read(
                b"BA0000000A", b"0000000001", -1, 10, 4
            )

    def test_valid_request_still_builds(self):
        packet = LxpRequestBuilder.prepare_packet_for_read(
            b"BA0000000A", b"0000000001", 0, 125, 4
        )
        assert len(packet) == 38


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
