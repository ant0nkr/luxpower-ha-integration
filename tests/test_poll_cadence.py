"""Tests for hold-register poll cadence and battery block back-off."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient

from fake_dongle import DUMMY_FRAME, FakeDongle
from custom_components.lxp_modbus.const import (
    BATTERY_BACKOFF_POLL_EVERY,
    BATTERY_INFO_START_REGISTER,
    BATTERY_EMPTY_POLLS_BEFORE_BACKOFF,
    HOLD_REGISTER_POLL_EVERY,
)


def make_client(**kwargs):
    """Build a client with a real lock and no network."""
    return LxpModbusApiClient(
        "192.0.2.1", 8000, "BA0000000A", "0000000001", asyncio.Lock(), **kwargs
    )


class TestHoldPollCadence:
    """Settings registers are configuration and are not re-read every poll."""

    def test_first_poll_reads_hold(self):
        """Setup must populate settings, or every control starts unknown."""
        client = make_client()

        assert client._should_poll_hold() is True

    def test_hold_is_skipped_until_the_interval_elapses(self):
        """Only every Nth poll pays for the settings blocks."""
        client = make_client()
        client._should_poll_hold()  # consume the forced first poll

        decisions = [client._should_poll_hold() for _ in range(HOLD_REGISTER_POLL_EVERY)]

        assert decisions[:-1] == [False] * (HOLD_REGISTER_POLL_EVERY - 1)
        assert decisions[-1] is True

    def test_cadence_repeats(self):
        """Over many polls the ratio holds."""
        client = make_client()
        polls = 100
        reads = sum(1 for _ in range(polls) if client._should_poll_hold())

        # First poll is forced, the rest follow the interval.
        expected = 1 + (polls - 1) // HOLD_REGISTER_POLL_EVERY
        assert reads == pytest.approx(expected, abs=1)

    def test_request_hold_refresh_forces_the_next_poll(self):
        """A write must be confirmed on the next poll, not up to N polls later."""
        client = make_client()
        client._should_poll_hold()
        assert client._should_poll_hold() is False

        client.request_hold_refresh()

        assert client._should_poll_hold() is True

    def test_forced_refresh_resets_the_interval(self):
        """After a forced read the interval starts again, it does not double up."""
        client = make_client()
        client._should_poll_hold()
        client.request_hold_refresh()
        client._should_poll_hold()

        decisions = [client._should_poll_hold() for _ in range(HOLD_REGISTER_POLL_EVERY - 1)]
        assert decisions == [False] * (HOLD_REGISTER_POLL_EVERY - 1)

    @pytest.mark.asyncio
    async def test_write_whose_confirmation_read_fails_requests_a_hold_refresh(self):
        """A write is normally confirmed inline; the cadence is the fallback.

        See test_write_confirmation.py for the inline path.
        """
        client = make_client(connection_retries=1)
        reader, writer = AsyncMock(spec=asyncio.StreamReader), AsyncMock(spec=asyncio.StreamWriter)
        writer.write = MagicMock()
        reader.read = AsyncMock(return_value=DUMMY_FRAME)
        client._should_poll_hold()          # consume the forced first poll
        client._should_poll_hold()          # now inside the interval
        client._force_hold_poll = False

        with patch('asyncio.open_connection', return_value=(reader, writer)):
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse') as response:
                response.return_value = MagicMock(
                    tcp_function=194, serial_number=b"0000000001",
                    packet_error=False, device_function=6, exception=0, register=100,
                    parsed_values_dictionary={100: 500},
                )
                # The mocked response is not a read reply, so the inline
                # confirmation read never gets its answer.
                assert await client.async_write_register(100, 500) is True

        assert client._force_hold_poll is True


class TestFailedConnectionKeepsSettingsPass:
    """A poll that never connects must not use up the settings pass it was due.

    Otherwise, after an outage, the first polls that do connect skip the settings read, and
    everything derived from settings stays stale for up to HOLD_REGISTER_POLL_EVERY polls
    after the input registers have recovered.
    """

    @pytest.mark.asyncio
    async def test_a_refused_connection_keeps_the_pass(self):
        client = make_client()          # the first poll is a settings pass

        with patch("asyncio.open_connection", side_effect=ConnectionRefusedError("refused")):
            with pytest.raises(ConnectionRefusedError):
                await client._async_poll_once()

        assert client._force_hold_poll is True
        assert client._should_poll_hold() is True

    @pytest.mark.asyncio
    async def test_a_poll_that_was_not_due_a_pass_does_not_claim_one(self):
        client = make_client()
        client._should_poll_hold()      # consume the forced first pass
        assert client._force_hold_poll is False

        with patch("asyncio.open_connection", side_effect=ConnectionRefusedError("refused")):
            with pytest.raises(ConnectionRefusedError):
                await client._async_poll_once()

        assert client._force_hold_poll is False

    @pytest.mark.asyncio
    async def test_the_retry_after_a_refusal_reads_the_settings(self):
        """The same poll's retry connects, and must be the one that reads the settings."""
        client = make_client(connection_retries=2, block_size=40)
        dongle = FakeDongle(dongle=b"BA0000000A", serial=b"0000000001", value_of=lambda f, r: 0)

        async def answer(writer, reader, reg, request_type, function_code):
            return {reg + offset: 1 for offset in range(40)} if reg < BATTERY_INFO_START_REGISTER else {}

        with patch("asyncio.open_connection", side_effect=[ConnectionRefusedError("refused"), (dongle, dongle)]), \
                patch.object(client, "async_request_registers", side_effect=answer):
            data = await client.async_get_data()

        assert data["hold"], "the retry that connected skipped the settings pass"


class TestBatteryBackoff:
    """Some batteries never publish the 5000+ block even with packs connected."""

    def test_polled_every_cycle_initially(self):
        """Nothing is assumed until the block has actually been tried."""
        client = make_client()

        assert all(client._should_poll_battery() for _ in range(BATTERY_EMPTY_POLLS_BEFORE_BACKOFF))

    def test_backs_off_after_repeated_empty_responses(self):
        """After enough empty reads the block stops being polled every cycle."""
        client = make_client()
        for _ in range(BATTERY_EMPTY_POLLS_BEFORE_BACKOFF):
            client._record_battery_result(False)

        decisions = [client._should_poll_battery() for _ in range(BATTERY_BACKOFF_POLL_EVERY)]

        assert decisions[:-1] == [False] * (BATTERY_BACKOFF_POLL_EVERY - 1)
        assert decisions[-1] is True, "back-off must retry, never give up permanently"

    def test_never_gives_up_permanently(self):
        """A pack that starts answering later must still be found."""
        client = make_client()
        for _ in range(BATTERY_EMPTY_POLLS_BEFORE_BACKOFF):
            client._record_battery_result(False)

        polls = BATTERY_BACKOFF_POLL_EVERY * 5
        retries = sum(1 for _ in range(polls) if client._should_poll_battery())

        assert retries >= 4

    def test_any_data_restores_every_cycle_polling(self):
        """LuxPower-brand packs that answer must not be penalised."""
        client = make_client()
        for _ in range(BATTERY_EMPTY_POLLS_BEFORE_BACKOFF):
            client._record_battery_result(False)
        assert client._should_poll_battery() is False

        client._record_battery_result(True)

        assert all(client._should_poll_battery() for _ in range(BATTERY_EMPTY_POLLS_BEFORE_BACKOFF))

    def test_packs_that_answer_immediately_never_back_off(self):
        """The common case must be completely unaffected."""
        client = make_client()
        for _ in range(50):
            assert client._should_poll_battery() is True
            client._record_battery_result(True)

    def test_explicit_serials_never_back_off(self):
        """Configured serials assert the packs exist, so silence is a fault."""
        client = make_client(battery_serials_configured=True)
        for _ in range(BATTERY_EMPTY_POLLS_BEFORE_BACKOFF * 3):
            client._record_battery_result(False)

        assert all(client._should_poll_battery() for _ in range(20))


class TestCadenceDiagnostics:
    """The counters exist so a support dump can show what was skipped."""

    def test_connection_stats_report_cadence(self):
        client = make_client()
        client._should_poll_hold()

        stats = client.get_connection_stats()

        assert stats["hold_poll_every"] == HOLD_REGISTER_POLL_EVERY
        assert stats["polls"] == 1
        assert "battery_empty_polls" in stats
        assert "battery_skipped_polls" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
