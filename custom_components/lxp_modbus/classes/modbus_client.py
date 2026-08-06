"""Modbus API client for communicating with LuxPower inverters."""
import asyncio
import logging
import time as time_lib

from homeassistant.helpers.update_coordinator import UpdateFailed

from ..const import (
    BATTERY_INFO_START_REGISTER,
    DEFAULT_CONNECTION_RETRIES,
    INITIAL_RETRY_DELAY,
    MAX_CACHED_DATA_FAILURES,
    MAX_RETRY_DELAY,
    READ_TIMEOUT,
    RESPONSE_OVERHEAD,
    RETRY_BACKOFF_MULTIPLIER,
    TOTAL_REGISTERS,
    WRITE_READ_TIMEOUT,
    WRITE_RESPONSE_LENGTH,
    WRITE_RETRY_DELAY,
)
from ..constants.input_registers import I_BAT_PARALLEL_NUM
from .connection_manager import ModbusConnectionManager
from .data_validator import is_data_sane
from .lxp_batteries import LxpBatteries
from .lxp_request_builder import LxpRequestBuilder
from .lxp_response import LxpResponse
from .packet_recovery import PacketRecoveryHandler

_LOGGER = logging.getLogger(__name__)

# Backward-compatible re-exports for tests
from .data_validator import HOLD_TIME_REGISTERS  # noqa: F401


class LxpModbusApiClient:
    """A client for communicating with a LuxPower inverter.

    Orchestrates register reading and writing using composed dependencies:
    - ModbusConnectionManager: TCP connection lifecycle
    - PacketRecoveryHandler: Malformed packet recovery
    - Data validation via is_data_sane()
    """

    def __init__(self, host: str, port: int, dongle_serial: str, inverter_serial: str, lock: asyncio.Lock,
                 block_size: int = 125, connection_retries: int = DEFAULT_CONNECTION_RETRIES,
                 skip_initial_data: bool = True, request_battery_data: bool = False):
        """Initialize the API client."""
        self._dongle_serial = dongle_serial
        self._inverter_serial = inverter_serial
        self._lock = lock
        self._block_size = block_size
        self._connection_retries = connection_retries
        self._request_battery_data = request_battery_data
        self._last_good_input_regs = {}
        self._last_good_hold_regs = {}
        self._last_good_battery_data = {}
        self._connection_retry_count = 0
        self._last_successful_connection = None
        self._connection_failure_count = 0

        # Composed dependencies
        self._connection_manager = ModbusConnectionManager(
            host, port, connection_retries, skip_initial_data
        )
        self._packet_recovery = PacketRecoveryHandler()

    async def async_safe_packet_recovery(self, reader, response_buf: bytes,
                                         expected_length: int, request_type: str,
                                         function_code: int) -> LxpResponse:
        """Delegate packet recovery to the PacketRecoveryHandler."""
        return await self._packet_recovery.async_attempt_recovery(
            reader, response_buf, expected_length, request_type, function_code
        )

    async def async_request_registers(self, writer, reader, reg, request_type, function_code) -> dict:
        """Request a block of registers and return parsed values."""
        count = min(self._block_size, TOTAL_REGISTERS - reg) if (reg < BATTERY_INFO_START_REGISTER) else self._block_size
        req = LxpRequestBuilder.prepare_packet_for_read(
            self._dongle_serial.encode(), self._inverter_serial.encode(),
            reg, count, function_code
        )
        expected_length = RESPONSE_OVERHEAD + (count * 2)
        writer.write(req)
        await writer.drain()
        response_buf = await asyncio.wait_for(reader.read(expected_length), timeout=READ_TIMEOUT)

        _LOGGER.debug(
            "Polling %s(%d) %d-%d: Req[%d]: %s, Resp[%d/%d]: %s",
            request_type,
            function_code,
            reg, reg + count - 1,
            len(req),
            req.hex(),
            len(response_buf) if response_buf else 0,
            expected_length,
            response_buf.hex() if response_buf else "None"
        )

        if response_buf and len(response_buf) > RESPONSE_OVERHEAD:
            response = LxpResponse(response_buf)

            # Attempt safe packet recovery if needed
            if response.packet_error and response.packet_length_calced > expected_length:
                response = await self.async_safe_packet_recovery(
                    reader, response_buf, expected_length, request_type, function_code
                )

            if (not response.packet_error
               and response.serial_number == self._inverter_serial.encode()
               and function_code == response.device_function
               and reg == response.register
               and is_data_sane(response.parsed_values_dictionary, request_type)
               ):

                if len(response.parsed_values_dictionary) != count:
                    _LOGGER.debug("%s(%s) response has different register count (%s) than requested (%s)",
                                  request_type, function_code, len(response.parsed_values_dictionary), count)

                # Battery data needs special decoding — returns dict keyed by serial
                # This will not work correctly with small blocks if they are not aligned
                if response.register >= BATTERY_INFO_START_REGISTER:
                    bat_dict = LxpBatteries(response).get_battery_info()
                    _LOGGER.debug("Battery data decoded: %s", list(bat_dict.keys()))
                    return bat_dict

                return response.parsed_values_dictionary
            else:
                _LOGGER.debug("ignoring %s(%s) packet for regs %s-%s : response=%s",
                              request_type, function_code, reg, reg + count - 1, response.info)

        return {}

    async def async_discard_initial_data(self, reader):
        """Delegate initial data discard to the connection manager."""
        await self._connection_manager.async_discard_initial_data(reader)

    def get_recovery_stats(self) -> dict:
        """Get packet recovery statistics for monitoring and debugging."""
        return self._packet_recovery.get_stats()

    def _snapshot(self) -> dict:
        """Return a copy of the last known good dataset.

        Copies are essential: entities optimistically write their new value into
        ``coordinator.data`` after a successful register write. Handing out the
        internal dictionaries would let that optimistic value overwrite the cache
        permanently, so a value the inverter never accepted would be reported as
        real until the register block happened to be re-read successfully.
        """
        return {
            "input": dict(self._last_good_input_regs),
            "hold": dict(self._last_good_hold_regs),
            "battery": {serial: dict(regs) for serial, regs in self._last_good_battery_data.items()},
        }

    def _last_success_description(self) -> str:
        """Describe how long ago the last successful connection was."""
        if not self._last_successful_connection:
            return "never"
        elapsed_time = time_lib.time() - self._last_successful_connection
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s ago"

    async def async_get_data(self) -> dict:
        """Fetch data from the inverter, backfilling with old data on partial failure."""
        _LOGGER.debug("API Client: Polling the inverter for new data...")

        retry_delay = INITIAL_RETRY_DELAY
        last_error = None

        for attempt in range(self._connection_retries):
            if attempt > 0:
                # Back off *outside* the lock. Sleeping while holding it would block
                # every user-initiated write for the whole backoff period.
                _LOGGER.info("Connection retry attempt %s/%s in %.1fs...",
                             attempt, self._connection_retries, retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * RETRY_BACKOFF_MULTIPLIER, MAX_RETRY_DELAY)

            try:
                await self._async_poll_once()
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as err:
                last_error = err
                _LOGGER.warning("Connection attempt %s/%s failed: %s",
                                attempt + 1, self._connection_retries, err)
                continue

            self._last_successful_connection = time_lib.time()
            self._connection_failure_count = 0
            if attempt > 0:
                self._connection_retry_count += 1
                _LOGGER.info("Successfully reconnected after %s attempts", attempt)
            return self._snapshot()

        return self._handle_poll_failure(last_error)

    async def _async_poll_once(self) -> None:
        """Run a single polling pass and merge the result into the cache.

        Raises the underlying connection error so the caller can retry.
        """
        newly_polled_input_regs = {}
        newly_polled_hold_regs = {}
        newly_polled_battery_data = {}
        writer = None

        async with self._lock:
            reader, writer = await self._connection_manager.async_connect()
            try:
                await self._connection_manager.async_discard_initial_data(reader)

                try:
                    # Poll INPUT registers (expecting function code 4)
                    for reg in range(0, TOTAL_REGISTERS, self._block_size):
                        reg_block = await self.async_request_registers(writer, reader, reg, "input", 4)
                        if len(reg_block) > 0:
                            newly_polled_input_regs.update(reg_block)

                    # Poll battery data if enabled and inverter reports connected batteries
                    # The decoding routine needs 120 registers for complete block processing
                    if (self._request_battery_data
                            and I_BAT_PARALLEL_NUM in newly_polled_input_regs
                            and newly_polled_input_regs[I_BAT_PARALLEL_NUM] > 0
                            and self._block_size >= 120):
                        for reg in range(BATTERY_INFO_START_REGISTER,
                                         BATTERY_INFO_START_REGISTER + 120,
                                         self._block_size):
                            bat_block = await self.async_request_registers(
                                writer, reader, reg, "input/bat", 4)
                            newly_polled_battery_data.update(bat_block)

                    # Poll HOLD registers (expecting function code 3)
                    for reg in range(0, TOTAL_REGISTERS, self._block_size):
                        reg_block = await self.async_request_registers(writer, reader, reg, "hold", 3)
                        if len(reg_block) > 0:
                            newly_polled_hold_regs.update(reg_block)

                except asyncio.TimeoutError:
                    _LOGGER.debug("Timeout requesting data from inverter")
            finally:
                await self._connection_manager.async_close(writer)

        # Merge new data with the last known good data
        if len(newly_polled_input_regs):
            self._last_good_input_regs.update(newly_polled_input_regs)

        if len(newly_polled_battery_data):
            self._last_good_battery_data.update(newly_polled_battery_data)

        if len(newly_polled_hold_regs):
            self._last_good_hold_regs.update(newly_polled_hold_regs)

    def _handle_poll_failure(self, error: Exception | None) -> dict:
        """Decide what to report after every connection attempt failed.

        A short cache window keeps entities populated across a flaky dongle blip;
        past that the failure is surfaced so Home Assistant marks the entities
        unavailable instead of presenting stale values as live.
        """
        self._connection_failure_count += 1

        _LOGGER.error("Total polling failure: %s. Consecutive failures: %s. Last success: %s",
                      error, self._connection_failure_count, self._last_success_description())

        if (self._last_good_input_regs
                and self._last_good_hold_regs
                and self._connection_failure_count <= MAX_CACHED_DATA_FAILURES):
            _LOGGER.warning(
                "Returning cached data due to temporary connection failure (%s/%s before entities go unavailable)",
                self._connection_failure_count, MAX_CACHED_DATA_FAILURES,
            )
            return self._snapshot()

        raise UpdateFailed(f"Error communicating with inverter: {error}")

    async def async_write_register(self, register: int, value: int) -> bool:
        """Write a single register value to the inverter with validation and retries."""
        for attempt in range(self._connection_retries):
            if attempt > 0:
                # Retry delay is taken outside the lock so a stalled write does not
                # also stall polling for the duration of the backoff.
                await asyncio.sleep(WRITE_RETRY_DELAY)

            try:
                if await self._async_write_once(register, value, attempt):
                    return True
            except Exception as ex:
                _LOGGER.error("Exception during write attempt %d for register %s: %s",
                              attempt + 1, register, ex)

        _LOGGER.error("Failed to write register %s after %d attempts.", register, self._connection_retries)
        return False

    async def _async_write_once(self, register: int, value: int, attempt: int) -> bool:
        """Perform a single write attempt and confirm it was applied."""
        async with self._lock:
            _LOGGER.debug("Write attempt %s/%s for register %s with value %s",
                          attempt + 1, self._connection_retries, register, value)

            try:
                reader, writer = await self._connection_manager.async_connect()
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                _LOGGER.warning("Connection attempt failed during write: %s", e)
                return False

            try:
                await self._connection_manager.async_discard_initial_data(reader)

                req = LxpRequestBuilder.prepare_packet_for_write(
                    self._dongle_serial.encode(), self._inverter_serial.encode(), register, value
                )
                writer.write(req)
                await writer.drain()

                # A bare read() here can block forever while holding the shared
                # lock, which wedges polling and every later write.
                response_buf = await asyncio.wait_for(
                    reader.read(WRITE_RESPONSE_LENGTH), timeout=WRITE_READ_TIMEOUT
                )
            except asyncio.TimeoutError:
                _LOGGER.warning("Write attempt %s for register %s timed out waiting for acknowledgement",
                                attempt + 1, register)
                return False
            finally:
                await self._connection_manager.async_close(writer)

            _LOGGER.debug(
                "Modbus WRITE: Sent to reg %s, value %s, resp: %s",
                register, value, response_buf.hex() if response_buf else "None"
            )

            # --- Response Validation ---
            if not response_buf:
                _LOGGER.warning("Write attempt %d failed: Response not received", attempt + 1)
                return False

            response = LxpResponse(response_buf)
            if response.packet_error:
                _LOGGER.warning("Write attempt %s failed: Inverter returned a packet error. %s",
                                attempt + 1, response.info)
                return False

            response_dict = response.parsed_values_dictionary
            if register in response_dict:
                received_value = response_dict.get(register)
                if received_value == value:
                    _LOGGER.info("Successfully wrote register %s with value %s.", register, value)
                    return True

                _LOGGER.warning("Write attempt %s failed: Confirmation mismatch, sent=%s received=%s",
                                attempt + 1, value, received_value)
            else:
                _LOGGER.warning("Write attempt %s failed: Confirmation mismatch, written register %s not received on confirmation. %s",
                                attempt + 1, register, response.info)

            return False

    def get_connection_stats(self) -> dict:
        """Return connection statistics for diagnostics."""
        return {
            "host": self._connection_manager.host,
            "port": self._connection_manager.port,
            "block_size": self._block_size,
            "connection_retries": self._connection_retries,
            "request_battery_data": self._request_battery_data,
            "consecutive_failures": self._connection_failure_count,
            "reconnect_count": self._connection_retry_count,
            "last_success": self._last_success_description(),
            "cached_input_registers": len(self._last_good_input_regs),
            "cached_hold_registers": len(self._last_good_hold_regs),
            "cached_batteries": list(self._last_good_battery_data),
        }
