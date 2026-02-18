"""Tests for the PacketRecoveryHandler class."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from custom_components.lxp_modbus.classes.packet_recovery import PacketRecoveryHandler
from custom_components.lxp_modbus.const import (
    MAX_PACKET_RECOVERY_ATTEMPTS,
    MAX_PACKET_SIZE,
    PACKET_RECOVERY_TIMEOUT,
)


def _make_mock_response(packet_error=False, packet_length_calced=100, error_type="No Error"):
    """Create a mock LxpResponse with the given attributes."""
    mock = MagicMock()
    mock.packet_error = packet_error
    mock.packet_length_calced = packet_length_calced
    mock.error_type = error_type
    return mock


class TestPacketRecoveryHandler:
    """Test cases for PacketRecoveryHandler."""

    @pytest.fixture
    def handler(self):
        """Create a fresh PacketRecoveryHandler instance."""
        return PacketRecoveryHandler()

    # ------------------------------------------------------------------ #
    # 1. Initialization
    # ------------------------------------------------------------------ #

    def test_init_stats_all_zero(self, handler):
        """Test that all internal counters start at zero."""
        assert handler._recovery_attempts_total == 0
        assert handler._recovery_successes == 0
        assert handler._recovery_failures == 0

    # ------------------------------------------------------------------ #
    # 2. get_stats - initial state
    # ------------------------------------------------------------------ #

    def test_get_stats_initial_state(self, handler):
        """Test get_stats returns zeros and 0% success rate on a fresh handler."""
        stats = handler.get_stats()

        assert stats["total_recovery_attempts"] == 0
        assert stats["successful_recoveries"] == 0
        assert stats["failed_recoveries"] == 0
        assert stats["recovery_success_rate"] == 0

    # ------------------------------------------------------------------ #
    # 3. get_stats - after setting values
    # ------------------------------------------------------------------ #

    def test_get_stats_after_setting_values(self, handler):
        """Test get_stats reflects manually set internal counters."""
        handler._recovery_attempts_total = 20
        handler._recovery_successes = 15
        handler._recovery_failures = 5

        stats = handler.get_stats()

        assert stats["total_recovery_attempts"] == 20
        assert stats["successful_recoveries"] == 15
        assert stats["failed_recoveries"] == 5
        assert stats["recovery_success_rate"] == 75.0

    # ------------------------------------------------------------------ #
    # 4. async_attempt_recovery - no error (returns original)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_attempt_recovery_no_error_returns_original(self, handler):
        """When packet_error is False the original response is returned immediately."""
        reader = AsyncMock()
        response_buf = b"\x00" * 100

        no_error_response = _make_mock_response(
            packet_error=False, packet_length_calced=100
        )

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            return_value=no_error_response,
        ) as mock_cls:
            result = await handler.async_attempt_recovery(
                reader, response_buf, 100, "input", 4
            )

        assert result is no_error_response
        reader.read.assert_not_called()
        # No recovery was attempted
        assert handler._recovery_attempts_total == 0

    # ------------------------------------------------------------------ #
    # 5. async_attempt_recovery - packet_length_calced <= expected
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_attempt_recovery_length_lte_expected_returns_original(self, handler):
        """When packet_length_calced <= expected_length, return original even if packet_error."""
        reader = AsyncMock()
        response_buf = b"\x00" * 50

        response = _make_mock_response(
            packet_error=True, packet_length_calced=50
        )

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            return_value=response,
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, 50, "input", 4
            )

        assert result is response
        reader.read.assert_not_called()
        assert handler._recovery_attempts_total == 0

    @pytest.mark.asyncio
    async def test_attempt_recovery_length_less_than_expected_returns_original(self, handler):
        """When packet_length_calced < expected_length, return original."""
        reader = AsyncMock()
        response_buf = b"\x00" * 50

        response = _make_mock_response(
            packet_error=True, packet_length_calced=40
        )

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            return_value=response,
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, 50, "input", 4
            )

        assert result is response
        reader.read.assert_not_called()
        assert handler._recovery_attempts_total == 0

    # ------------------------------------------------------------------ #
    # 6. async_attempt_recovery - packet too large (skip recovery)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_attempt_recovery_packet_too_large_skips_recovery(self, handler):
        """When packet_length_calced > MAX_PACKET_SIZE, recovery is skipped."""
        reader = AsyncMock()
        response_buf = b"\x00" * 100
        expected_length = 80

        response = _make_mock_response(
            packet_error=True,
            packet_length_calced=MAX_PACKET_SIZE + 1,
        )

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            return_value=response,
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        assert result is response
        reader.read.assert_not_called()
        assert handler._recovery_attempts_total == 0

    @pytest.mark.asyncio
    async def test_attempt_recovery_missing_bytes_too_large_skips_recovery(self, handler):
        """When missing_bytes > (MAX_PACKET_SIZE - expected_length), recovery is skipped."""
        reader = AsyncMock()
        response_buf = b"\x00" * 100
        expected_length = 100
        # packet_length_calced is within MAX_PACKET_SIZE but
        # missing_bytes = packet_length_calced - expected_length > MAX_PACKET_SIZE - expected_length
        # i.e. packet_length_calced > MAX_PACKET_SIZE which overlaps with the previous test.
        # To hit the missing_bytes branch specifically we need:
        #   packet_length_calced <= MAX_PACKET_SIZE  AND
        #   (packet_length_calced - expected_length) > (MAX_PACKET_SIZE - expected_length)
        # That simplifies to packet_length_calced > MAX_PACKET_SIZE, so the two guards
        # are practically equivalent. We can still verify the guard fires with a value of
        # exactly MAX_PACKET_SIZE + 1 by using a small expected_length so the first guard
        # doesn't trigger.
        # Actually re-reading: both guards fire for the same values so let's use a
        # direct scenario: expected_length=100, packet_length_calced=MAX_PACKET_SIZE
        # missing_bytes = MAX_PACKET_SIZE - 100 = 924
        # MAX_PACKET_SIZE - expected_length = 924  -> 924 > 924 is False, so no skip.
        # Use packet_length_calced=MAX_PACKET_SIZE (1024): first guard 1024 > 1024 is False.
        # So both guards pass. Need packet_length_calced=MAX_PACKET_SIZE exactly and expected
        # small enough. Actually the second guard is strictly greater, so it won't trigger when
        # equal to MAX_PACKET_SIZE. Let's just make sure the first guard (packet too large) is
        # what triggers. We already tested that above.

        # For completeness, test a scenario where expected_length = 0 and
        # packet_length_calced = MAX_PACKET_SIZE. Then missing_bytes = MAX_PACKET_SIZE,
        # MAX_PACKET_SIZE - expected_length = MAX_PACKET_SIZE, so missing_bytes > ... is False.
        # So the missing_bytes guard never fires independently of the packet_too_large guard
        # when packet_length_calced <= MAX_PACKET_SIZE. We include the test to document that.
        pass  # guard is subsumed by packet_too_large; covered in test above

    # ------------------------------------------------------------------ #
    # 7. async_attempt_recovery - timeout during recovery
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_attempt_recovery_timeout(self, handler):
        """When the reader times out, recovery fails and stats are updated."""
        reader = AsyncMock()
        reader.read.side_effect = asyncio.TimeoutError()
        response_buf = b"\x00" * 100
        expected_length = 100

        original_response = _make_mock_response(
            packet_error=True, packet_length_calced=200
        )

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            return_value=original_response,
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        assert result is original_response
        assert handler._recovery_attempts_total == 1
        assert handler._recovery_failures == 1
        assert handler._recovery_successes == 0

    # ------------------------------------------------------------------ #
    # 8. async_attempt_recovery - success increments stats
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_attempt_recovery_success_increments_stats(self, handler):
        """Successful recovery increments _recovery_successes and _recovery_attempts_total."""
        reader = AsyncMock()
        reader.read.return_value = b"\x00" * 100  # extra bytes

        response_buf = b"\x00" * 100
        expected_length = 100

        original_response = _make_mock_response(
            packet_error=True, packet_length_calced=200
        )
        recovered_response = _make_mock_response(
            packet_error=False, packet_length_calced=200
        )

        # First call to LxpResponse -> original, second -> recovered
        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            side_effect=[original_response, recovered_response],
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        assert result is recovered_response
        assert handler._recovery_attempts_total == 1
        assert handler._recovery_successes == 1
        assert handler._recovery_failures == 0

    @pytest.mark.asyncio
    async def test_attempt_recovery_success_returns_recovered_response(self, handler):
        """The recovered LxpResponse (not the original) is returned on success."""
        reader = AsyncMock()
        reader.read.return_value = b"\xff" * 50

        response_buf = b"\x00" * 80
        expected_length = 80

        original_response = _make_mock_response(
            packet_error=True, packet_length_calced=130
        )
        recovered_response = _make_mock_response(
            packet_error=False, packet_length_calced=130
        )

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            side_effect=[original_response, recovered_response],
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        assert result is recovered_response
        assert result is not original_response

    # ------------------------------------------------------------------ #
    # 9. async_attempt_recovery - failure increments stats
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_attempt_recovery_failure_increments_stats(self, handler):
        """Failed recovery (still packet_error after read) increments _recovery_failures."""
        reader = AsyncMock()
        reader.read.return_value = b"\x00" * 100

        response_buf = b"\x00" * 100
        expected_length = 100

        original_response = _make_mock_response(
            packet_error=True, packet_length_calced=200, error_type="Wrong CRC"
        )
        still_broken_response = _make_mock_response(
            packet_error=True, packet_length_calced=200, error_type="Wrong CRC"
        )

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            side_effect=[original_response, still_broken_response],
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        assert result is original_response
        assert handler._recovery_attempts_total == 1
        assert handler._recovery_failures == 1
        assert handler._recovery_successes == 0

    @pytest.mark.asyncio
    async def test_attempt_recovery_failure_empty_data(self, handler):
        """Recovery fails when reader returns empty bytes."""
        reader = AsyncMock()
        reader.read.return_value = b""  # No additional data received

        response_buf = b"\x00" * 100
        expected_length = 100

        original_response = _make_mock_response(
            packet_error=True, packet_length_calced=200
        )

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            return_value=original_response,
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        assert result is original_response
        assert handler._recovery_attempts_total == 1
        assert handler._recovery_failures == 1

    @pytest.mark.asyncio
    async def test_attempt_recovery_failure_generic_exception(self, handler):
        """Recovery fails when an unexpected exception is raised during read."""
        reader = AsyncMock()
        reader.read.side_effect = OSError("Connection reset")

        response_buf = b"\x00" * 100
        expected_length = 100

        original_response = _make_mock_response(
            packet_error=True, packet_length_calced=200
        )

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            return_value=original_response,
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        assert result is original_response
        assert handler._recovery_attempts_total == 1
        assert handler._recovery_failures == 1
        assert handler._recovery_successes == 0

    # ------------------------------------------------------------------ #
    # 10. Recovery success rate calculation
    # ------------------------------------------------------------------ #

    def test_success_rate_zero_attempts(self, handler):
        """Success rate is 0 when no recovery attempts have been made."""
        stats = handler.get_stats()
        assert stats["recovery_success_rate"] == 0

    def test_success_rate_all_successful(self, handler):
        """Success rate is 100% when all attempts succeed."""
        handler._recovery_attempts_total = 5
        handler._recovery_successes = 5
        handler._recovery_failures = 0

        stats = handler.get_stats()
        assert stats["recovery_success_rate"] == 100.0

    def test_success_rate_all_failed(self, handler):
        """Success rate is 0% when all attempts fail."""
        handler._recovery_attempts_total = 5
        handler._recovery_successes = 0
        handler._recovery_failures = 5

        stats = handler.get_stats()
        assert stats["recovery_success_rate"] == 0.0

    def test_success_rate_mixed(self, handler):
        """Success rate is correctly calculated with mixed results."""
        handler._recovery_attempts_total = 8
        handler._recovery_successes = 3
        handler._recovery_failures = 5

        stats = handler.get_stats()
        assert stats["recovery_success_rate"] == pytest.approx(37.5)

    def test_success_rate_single_success(self, handler):
        """Success rate is 100% with exactly one successful attempt."""
        handler._recovery_attempts_total = 1
        handler._recovery_successes = 1
        handler._recovery_failures = 0

        stats = handler.get_stats()
        assert stats["recovery_success_rate"] == 100.0

    # ------------------------------------------------------------------ #
    # Additional edge-case tests
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_attempt_recovery_respects_max_attempts(self, handler):
        """Recovery loop does not exceed MAX_PACKET_RECOVERY_ATTEMPTS."""
        reader = AsyncMock()
        # Always return some data so the loop keeps going
        reader.read.return_value = b"\x00" * 50

        response_buf = b"\x00" * 100
        expected_length = 100

        original_response = _make_mock_response(
            packet_error=True, packet_length_calced=200, error_type="Wrong CRC"
        )
        # Every constructed LxpResponse still has an error, but with a *changing*
        # packet_length_calced so that the retry branch triggers.
        call_count = 0

        def response_factory(data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return original_response
            # Subsequent calls: still errored, but with an adjusted calced length
            # to trigger "continue" in the retry loop.
            resp = _make_mock_response(
                packet_error=True,
                packet_length_calced=200 + call_count * 10,
                error_type="Wrong CRC",
            )
            return resp

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            side_effect=response_factory,
        ):
            result = await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        # The reader should have been called at most MAX_PACKET_RECOVERY_ATTEMPTS times
        assert reader.read.call_count <= MAX_PACKET_RECOVERY_ATTEMPTS
        assert handler._recovery_failures == 1

    @pytest.mark.asyncio
    async def test_multiple_recovery_sessions_accumulate_stats(self, handler):
        """Running multiple recovery sessions accumulates stats correctly."""
        reader = AsyncMock()

        response_buf = b"\x00" * 100
        expected_length = 100

        # -- First session: success --
        original_1 = _make_mock_response(packet_error=True, packet_length_calced=200)
        recovered_1 = _make_mock_response(packet_error=False, packet_length_calced=200)
        reader.read.return_value = b"\x00" * 100

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            side_effect=[original_1, recovered_1],
        ):
            await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        assert handler._recovery_attempts_total == 1
        assert handler._recovery_successes == 1
        assert handler._recovery_failures == 0

        # -- Second session: failure (timeout) --
        reader.read.side_effect = asyncio.TimeoutError()
        original_2 = _make_mock_response(packet_error=True, packet_length_calced=200)

        with patch(
            "custom_components.lxp_modbus.classes.packet_recovery.LxpResponse",
            return_value=original_2,
        ):
            await handler.async_attempt_recovery(
                reader, response_buf, expected_length, "input", 4
            )

        assert handler._recovery_attempts_total == 2
        assert handler._recovery_successes == 1
        assert handler._recovery_failures == 1

        # -- Verify cumulative stats --
        stats = handler.get_stats()
        assert stats["total_recovery_attempts"] == 2
        assert stats["successful_recoveries"] == 1
        assert stats["failed_recoveries"] == 1
        assert stats["recovery_success_rate"] == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
