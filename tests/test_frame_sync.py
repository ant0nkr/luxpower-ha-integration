"""Tests for keeping replies matched to their requests.

Issues #167 and #169: right after connecting, the dongle pushed frames of its own
(hold 0-39 and hold 40-79). Only the first was discarded and every read took
"whatever bytes are waiting" as the answer, so each request got the reply to the
one before it. Every reply failed the register check and was dropped, and the
entities stayed Unknown while the poll still counted as a success.
"""

import asyncio
import pytest
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.classes.lxp_frame_reader import LxpFrameReader
from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient
from custom_components.lxp_modbus.const import TOTAL_REGISTERS

from fake_dongle import FakeDongle, build_frame

DONGLE = b"BA0000000A"
SERIAL = b"0000000001"


def input_value(register):
    return 10000 + register


def hold_value(register):
    # Stays a valid packed time so the hold sanity check never interferes.
    return register % 24


def value_of(function, register):
    return input_value(register) if function == 4 else hold_value(register)


def make_client(**kwargs):
    kwargs.setdefault("block_size", 40)
    kwargs.setdefault("skip_initial_data", False)
    kwargs.setdefault("connection_retries", 1)
    return LxpModbusApiClient("192.0.2.1", 8000, DONGLE.decode(), SERIAL.decode(),
                              asyncio.Lock(), **kwargs)


def stale_hold(register, count=40):
    """A hold block the dongle relays on its own, as in #167's log."""
    return build_frame(DONGLE, SERIAL, 3, register, values=[hold_value(r) for r in range(register, register + count)])


class TestFrameReader:
    """The stream is cut into frames by the header, not by read() boundaries."""

    @pytest.mark.asyncio
    async def test_two_frames_in_one_read_come_out_separately(self):
        dongle = FakeDongle()
        first, second = stale_hold(0), stale_hold(40)
        dongle.push(first + second)
        frames = LxpFrameReader(dongle)

        assert await frames.async_read_frame(1) == first
        assert await frames.async_read_frame(1) == second

    @pytest.mark.asyncio
    async def test_frame_split_across_reads_is_reassembled(self):
        dongle = FakeDongle(chunk=7)
        frame = stale_hold(0)
        dongle.push(frame)

        assert await LxpFrameReader(dongle).async_read_frame(1) == frame

    @pytest.mark.asyncio
    async def test_bytes_before_a_header_are_skipped(self):
        dongle = FakeDongle()
        frame = stale_hold(0)
        dongle.push(b"\x00\xa1\x55garbage" + frame)
        frames = LxpFrameReader(dongle)

        assert await frames.async_read_frame(1) == frame
        assert frames.discarded_bytes == 10

    @pytest.mark.asyncio
    async def test_no_frame_times_out(self):
        with pytest.raises(asyncio.TimeoutError):
            await LxpFrameReader(FakeDongle()).async_read_frame(0.05)


class TestStaleFramesAreSkipped:
    """Frames that are not the answer are dropped and the real answer is used."""

    @pytest.mark.asyncio
    async def test_pushed_frames_do_not_shift_replies(self):
        """The exact pattern from #167: two unsolicited hold frames, then polling."""
        client = make_client()
        dongle = FakeDongle(DONGLE, SERIAL, value_of=value_of)
        dongle.push(stale_hold(0) + stale_hold(40))

        with patch('asyncio.open_connection', return_value=(dongle, dongle)):
            data = await client.async_get_data()

        assert len(data["input"]) == TOTAL_REGISTERS
        assert all(value == input_value(reg) for reg, value in data["input"].items())
        assert len(data["hold"]) == TOTAL_REGISTERS
        assert all(value == hold_value(reg) for reg, value in data["hold"].items())
        assert client.get_connection_stats()["stale_frames_discarded"] == 2

    @pytest.mark.asyncio
    async def test_frames_split_into_small_reads(self):
        client = make_client()
        dongle = FakeDongle(DONGLE, SERIAL, value_of=value_of, chunk=13)

        with patch('asyncio.open_connection', return_value=(dongle, dongle)):
            data = await client.async_get_data()

        assert len(data["input"]) == TOTAL_REGISTERS

    @pytest.mark.asyncio
    async def test_reply_for_another_inverter_is_skipped(self):
        client = make_client()
        dongle = FakeDongle(DONGLE, SERIAL, value_of=value_of)
        dongle.push(build_frame(DONGLE, b"9999999999", 4, 0, values=[1] * 40))

        reg_block = await client.async_request_registers(dongle, dongle, 0, "input", 4)

        assert reg_block[0] == input_value(0)

    @pytest.mark.asyncio
    async def test_exception_reply_ends_the_wait(self):
        """A refused block answers at once instead of costing a timeout."""
        client = make_client()
        dongle = FakeDongle(DONGLE, SERIAL, value_of=value_of)
        dongle.exceptions[(4, 400)] = 2

        with patch('custom_components.lxp_modbus.classes.modbus_client.READ_TIMEOUT', 30):
            reg_block = await asyncio.wait_for(
                client.async_request_registers(dongle, dongle, 400, "input", 4), timeout=1)

        assert reg_block == {}

    @pytest.mark.asyncio
    async def test_write_ack_is_not_confused_with_a_pushed_frame(self):
        client = make_client()
        dongle = FakeDongle(DONGLE, SERIAL, value_of=value_of)
        dongle.push(stale_hold(0))

        with patch('asyncio.open_connection', return_value=(dongle, dongle)):
            assert await client.async_write_register(21, 21) is True


class TestHoldPassIsNotLost:
    """#169 showed hold_polls: 0 after 105 polls."""

    @pytest.mark.asyncio
    async def test_unfinished_hold_pass_is_retried_next_poll(self):
        client = make_client()
        dongle = FakeDongle(DONGLE, SERIAL, value_of=value_of)
        dongle.silent_functions.add(3)

        with patch('custom_components.lxp_modbus.classes.modbus_client.READ_TIMEOUT', 0.05):
            with patch('asyncio.open_connection', return_value=(dongle, dongle)):
                await client.async_get_data()

        assert client._hold_polls == 0
        assert client._should_poll_hold() is True

    @pytest.mark.asyncio
    async def test_finished_hold_pass_waits_for_the_interval(self):
        client = make_client()
        dongle = FakeDongle(DONGLE, SERIAL, value_of=value_of)

        with patch('asyncio.open_connection', return_value=(dongle, dongle)):
            await client.async_get_data()

        assert client._hold_polls == 1
        assert client._should_poll_hold() is False


class TestDiscoverySkipsPushedFrames:
    """The model read in the config flow takes the model frame, not the first bytes."""

    @pytest.mark.asyncio
    async def test_pushed_input_frame_is_not_read_as_the_model(self):
        from custom_components.lxp_modbus.classes.inverter_discovery import get_inverter_model_from_device
        from custom_components.lxp_modbus.utils import decode_model_from_registers

        model_regs = {7: 0x4141, 8: 0x4148}  # "AAHA"-style code
        dongle = FakeDongle(DONGLE, SERIAL, value_of=lambda function, register: model_regs.get(register, 0))
        dongle.push(build_frame(DONGLE, SERIAL, 4, 0, values=[0x5A5A] * 40))

        with patch('asyncio.open_connection', return_value=(dongle, dongle)):
            model = await get_inverter_model_from_device("192.0.2.1", 8000, DONGLE.decode(), SERIAL.decode())

        assert model == decode_model_from_registers(model_regs)


class TestSerialMismatchWarning:
    """#110: a mistyped serial made every reply look stale, with nothing at WARNING."""

    @pytest.mark.asyncio
    async def test_wrong_serial_is_named_once(self, caplog):
        client = make_client()
        dongle = FakeDongle(DONGLE, b"4314970067", value_of=value_of)

        with patch('custom_components.lxp_modbus.classes.modbus_client.READ_TIMEOUT', 0.05):
            for _ in range(2):
                with pytest.raises(asyncio.TimeoutError):
                    await client.async_request_registers(dongle, dongle, 0, "input", 4)

        warnings = [r for r in caplog.records
                    if r.levelname == "WARNING" and "4314970067" in r.getMessage()]
        assert len(warnings) == 1
        assert SERIAL.decode() in warnings[0].getMessage()

    @pytest.mark.asyncio
    async def test_no_warning_once_replies_have_matched(self, caplog):
        client = make_client()
        dongle = FakeDongle(DONGLE, SERIAL, value_of=value_of)
        client._last_good_input_regs = {0: 1}
        dongle.push(build_frame(DONGLE, b"9999999999", 4, 0, values=[1] * 40))

        await client.async_request_registers(dongle, dongle, 0, "input", 4)

        assert not [r for r in caplog.records
                    if r.levelname == "WARNING" and "9999999999" in r.getMessage()]
