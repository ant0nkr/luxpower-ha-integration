"""Tests for hold-register poll cadence and battery block back-off."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient
from custom_components.lxp_modbus.const import (
    BATTERY_BACKOFF_POLL_EVERY,
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
    async def test_successful_write_requests_a_hold_refresh(self, ):
        """The client itself flags the refresh, so every platform benefits."""
        client = make_client(connection_retries=1)
        reader, writer = AsyncMock(spec=asyncio.StreamReader), AsyncMock(spec=asyncio.StreamWriter)
        writer.write = MagicMock()
        reader.read = AsyncMock(return_value=b"\x00" * 76)
        client._should_poll_hold()          # consume the forced first poll
        client._should_poll_hold()          # now inside the interval
        client._force_hold_poll = False

        with patch('asyncio.open_connection', return_value=(reader, writer)):
            with patch('custom_components.lxp_modbus.classes.modbus_client.LxpResponse') as response:
                response.return_value = MagicMock(
                    packet_error=False, parsed_values_dictionary={100: 500}
                )
                assert await client.async_write_register(100, 500) is True

        assert client._force_hold_poll is True


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
