"""When each hold register was last read from the inverter.

The client keeps the last good hold registers across failed polls and between its
infrequent settings passes, so a cached value cannot say how old it is. A sensor derived
from hold registers needs that age, both to carry a value forward honestly between
reads and to stop when its source has gone stale.
"""

import asyncio
from unittest.mock import patch

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fake_dongle import FakeDongle
from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient
from custom_components.lxp_modbus.const import BATTERY_INFO_START_REGISTER

START = 1793275200.0       # 2026-10-29T12:00:00Z
BLOCK = 40
POLL_EVERY = 15            # seconds between polls
SETTINGS_GAP = 75          # seconds between settings passes: every 5th poll


class Clock:
    """A hand-wound time.time(). Only that is patched: the client's own timeouts use the
    monotonic clock, which a frozen clock would stop, hanging the test."""

    def __init__(self):
        self.now = START

    def tick(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    clock = Clock()
    with patch("custom_components.lxp_modbus.classes.modbus_client.time_lib.time",
               side_effect=lambda: clock.now):
        yield clock


def make_client():
    return LxpModbusApiClient(
        "192.0.2.1", 8000, "BA0000000A", "0000000001", asyncio.Lock(),
        block_size=BLOCK, connection_retries=1, skip_initial_data=True,
    )


async def poll(client, failing_hold_blocks=(), per_request=None):
    """One poll in which every block is answered, except the hold blocks named.

    ``per_request`` is called as each block is answered, e.g. to let time pass.
    """
    async def fake_request(writer, reader, reg, request_type, function_code):
        if per_request:
            per_request()
        if reg >= BATTERY_INFO_START_REGISTER:
            return {}
        if request_type == "hold" and reg in failing_hold_blocks:
            return {}
        return {reg + offset: 1 for offset in range(BLOCK)}

    dongle = FakeDongle(dongle=b"BA0000000A", serial=b"0000000001", value_of=lambda f, r: 0)
    with patch("asyncio.open_connection", return_value=(dongle, dongle)), \
            patch.object(client, "async_request_registers", side_effect=fake_request):
        return await client.async_get_data()


class TestHoldReadTimes:
    @pytest.mark.asyncio
    async def test_the_settings_pass_stamps_every_register_it_read(self, clock):
        client = make_client()

        data = await poll(client)

        assert data["hold"], "the first poll reads the settings"
        assert set(data["hold_read_at"]) == set(data["hold"])
        assert set(data["hold_read_at"].values()) == {START}

    @pytest.mark.asyncio
    async def test_each_block_is_stamped_when_it_is_read(self, clock):
        """A settings pass takes seconds, and the block with the clock is read first.

        Stamping the whole pass when it ends would make that reading look newer than it is.
        """
        client = make_client()

        data = await poll(client, per_request=lambda: clock.tick(1))

        stamps = data["hold_read_at"]
        assert stamps[BLOCK] - stamps[0] == 1.0
        assert stamps[2 * BLOCK] - stamps[BLOCK] == 1.0
        assert len(set(stamps.values())) > 2

    @pytest.mark.asyncio
    async def test_polls_between_settings_passes_leave_the_stamps_alone(self, clock):
        """The cached values are reported again, and they are not newer for it."""
        client = make_client()
        first = await poll(client)

        clock.tick(POLL_EVERY)
        second = await poll(client)

        assert second["hold"] == first["hold"]
        assert second["hold_read_at"] == first["hold_read_at"]

    @pytest.mark.asyncio
    async def test_the_next_settings_pass_restamps(self, clock):
        client = make_client()
        await poll(client)
        client.request_hold_refresh()       # the cadence itself is covered in test_poll_cadence.py
        clock.tick(SETTINGS_GAP)
        data = await poll(client)

        assert set(data["hold_read_at"].values()) == {START + SETTINGS_GAP}

    @pytest.mark.asyncio
    async def test_a_block_that_fails_keeps_its_old_stamp(self, clock):
        """Only what was actually read is fresh, so a sensor on the failed block ages."""
        client = make_client()
        await poll(client)
        client.request_hold_refresh()       # the cadence itself is covered in test_poll_cadence.py
        clock.tick(SETTINGS_GAP)
        data = await poll(client, failing_hold_blocks=(0,))

        stamps = data["hold_read_at"]
        assert {stamps[register] for register in range(BLOCK)} == {START}       # block 0: old
        assert {stamps[register] for register in range(BLOCK, 2 * BLOCK)} == {START + SETTINGS_GAP}

    @pytest.mark.asyncio
    async def test_cached_data_returned_after_a_failure_keeps_its_old_stamps(self, clock):
        """The dead-connection case: the cache is served, but it is not reported as fresh."""
        client = make_client()
        await poll(client)
        clock.tick(120)

        with patch("asyncio.open_connection", side_effect=ConnectionRefusedError("refused")):
            data = await client.async_get_data()

        assert data["hold"]
        assert set(data["hold_read_at"].values()) == {START}

    @pytest.mark.asyncio
    async def test_the_stamps_are_a_copy(self, clock):
        """Entities write into coordinator.data, which must never reach the client's cache."""
        client = make_client()
        data = await poll(client)

        data["hold_read_at"][12] = 0

        assert client._hold_read_at[12] == START

    def test_a_confirmed_write_stamps_its_register(self, clock):
        """The acknowledgement echoes what the inverter stored, which is a fresh value."""
        client = make_client()

        client._record_hold_read({21: 7})

        assert client._last_good_hold_regs == {21: 7}
        assert client._hold_read_at == {21: START}
