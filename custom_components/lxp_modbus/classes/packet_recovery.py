"""Packet recovery handler for malformed Modbus responses."""
import asyncio
import logging

from .lxp_response import LxpResponse
from ..const import MAX_PACKET_RECOVERY_ATTEMPTS, MAX_PACKET_SIZE, PACKET_RECOVERY_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class PacketRecoveryHandler:
    """Handles recovery of truncated or malformed Modbus packets."""

    def __init__(self):
        """Initialize the recovery handler."""
        self._recovery_attempts_total = 0
        self._recovery_successes = 0
        self._recovery_failures = 0

    async def async_attempt_recovery(self, reader, response_buf: bytes,
                                     expected_length: int, request_type: str,
                                     function_code: int) -> LxpResponse:
        """
        Safely attempt to recover malformed packets with retry limits and validation.

        Args:
            reader: The stream reader
            response_buf: Initial response buffer
            expected_length: Expected packet length
            request_type: Type of request for logging
            function_code: Modbus function code

        Returns:
            LxpResponse: Recovered response or original if recovery fails
        """
        original_response = LxpResponse(response_buf)

        # If packet is not in error or doesn't need recovery, return as-is
        if not original_response.packet_error or original_response.packet_length_calced <= expected_length:
            return original_response

        # Validate recovery parameters
        missing_bytes = original_response.packet_length_calced - expected_length

        # Safety checks before attempting recovery
        if missing_bytes <= 0:
            _LOGGER.debug("No recovery needed for %s(%s): missing_bytes=%s", request_type, function_code, missing_bytes)
            return original_response

        if original_response.packet_length_calced > MAX_PACKET_SIZE:
            _LOGGER.warning("Packet too large for %s(%s): %s > %s, skipping recovery", request_type, function_code, original_response.packet_length_calced, MAX_PACKET_SIZE)
            return original_response

        if missing_bytes > (MAX_PACKET_SIZE - expected_length):
            _LOGGER.warning("Missing bytes too large for %s(%s): %s, skipping recovery", request_type, function_code, missing_bytes)
            return original_response

        # Attempt packet recovery with retry limit
        recovery_attempts = 0
        accumulated_data = response_buf
        self._recovery_attempts_total += 1

        while recovery_attempts < MAX_PACKET_RECOVERY_ATTEMPTS:
            try:
                recovery_attempts += 1
                _LOGGER.debug("Attempting packet recovery #%s for %s(%s): need %s more bytes", recovery_attempts, request_type, function_code, missing_bytes)

                # Read missing bytes with timeout
                new_data = await asyncio.wait_for(reader.read(missing_bytes), timeout=PACKET_RECOVERY_TIMEOUT)

                if not new_data:
                    _LOGGER.debug("No additional data received on recovery attempt #%s", recovery_attempts)
                    break

                accumulated_data += new_data
                recovered_response = LxpResponse(accumulated_data)

                # Check if recovery was successful
                if not recovered_response.packet_error:
                    _LOGGER.debug("Packet recovery successful on attempt #%s for %s(%s)", recovery_attempts, request_type, function_code)
                    self._recovery_successes += 1
                    return recovered_response

                # If still in error but length changed, adjust missing bytes for next attempt
                if recovered_response.packet_length_calced != original_response.packet_length_calced:
                    new_missing = recovered_response.packet_length_calced - len(accumulated_data)
                    if new_missing > 0 and new_missing <= (MAX_PACKET_SIZE - len(accumulated_data)):
                        missing_bytes = new_missing
                        original_response = recovered_response
                        continue

                _LOGGER.debug("Recovery attempt #%s failed for %s(%s): %s", recovery_attempts, request_type, function_code, recovered_response.error_type)
                break

            except asyncio.TimeoutError:
                _LOGGER.debug("Timeout on recovery attempt #%s for %s(%s)", recovery_attempts, request_type, function_code)
                break
            except Exception as e:
                _LOGGER.warning("Error during packet recovery attempt #%s for %s(%s): %s", recovery_attempts, request_type, function_code, e)
                break

        _LOGGER.debug("Packet recovery failed after %s attempts for %s(%s)", recovery_attempts, request_type, function_code)
        self._recovery_failures += 1
        return original_response

    def get_stats(self) -> dict:
        """Get packet recovery statistics for monitoring and debugging."""
        return {
            "total_recovery_attempts": self._recovery_attempts_total,
            "successful_recoveries": self._recovery_successes,
            "failed_recoveries": self._recovery_failures,
            "recovery_success_rate": (
                self._recovery_successes / self._recovery_attempts_total * 100
                if self._recovery_attempts_total > 0 else 0
            )
        }
