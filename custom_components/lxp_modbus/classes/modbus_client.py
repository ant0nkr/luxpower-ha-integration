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
    MAX_EMPTY_DATA_FAILURES,
    READ_TIMEOUT,
    RESPONSE_OVERHEAD,
    RETRY_BACKOFF_MULTIPLIER,
    TOTAL_REGISTERS,
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
        count = min(self._block_size, TOTAL_REGISTERS - reg)
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
                if response.register == BATTERY_INFO_START_REGISTER:
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

    async def async_get_data(self) -> dict:
        """Fetch data from the inverter, backfilling with old data on partial failure."""
        _LOGGER.debug("API Client: Polling the inverter for new data...")

        # Initialize connection state for this attempt
        connection_success = False
        connection_retry = False
        retry_delay = INITIAL_RETRY_DELAY
        writer = None

        try:
            async with self._lock:
                # Try to establish a connection with retry logic
                for retry in range(self._connection_retries):
                    try:
                        if retry > 0:
                            _LOGGER.info("Connection retry attempt %s/%s...", retry, self._connection_retries)
                            connection_retry = True

                        reader, writer = await self._connection_manager.async_connect()
                        connection_success = True
                        break
                    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                        if retry < self._connection_retries - 1:
                            _LOGGER.warning("Connection attempt failed: %s. Retrying in %s seconds...", e, retry_delay)
                            await asyncio.sleep(retry_delay)
                            retry_delay *= RETRY_BACKOFF_MULTIPLIER
                        else:
                            raise

                # Update connection statistics
                if connection_success:
                    self._last_successful_connection = time_lib.time()
                    self._connection_failure_count = 0
                    if connection_retry:
                        self._connection_retry_count += 1
                        _LOGGER.info("Successfully reconnected after %s attempts", retry)

                newly_polled_input_regs = {}
                newly_polled_hold_regs = {}
                newly_polled_battery_data = {}

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

                # Close the connection
                await self._connection_manager.async_close(writer)

            # Merge new data with the last known good data
            if len(newly_polled_input_regs):
                self._last_good_input_regs.update(newly_polled_input_regs)

            if len(newly_polled_battery_data):
                self._last_good_battery_data.update(newly_polled_battery_data)

            if len(newly_polled_hold_regs):
                self._last_good_hold_regs.update(newly_polled_hold_regs)

            # Always return a complete (though possibly stale) dataset
            return {"input": self._last_good_input_regs, "hold": self._last_good_hold_regs, "battery": self._last_good_battery_data}

        except Exception as ex:
            self._connection_failure_count += 1
            last_success_str = "never"
            if self._last_successful_connection:
                elapsed_time = time_lib.time() - self._last_successful_connection
                hours, remainder = divmod(elapsed_time, 3600)
                minutes, seconds = divmod(remainder, 60)
                last_success_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s ago"

            _LOGGER.error("Total polling failure: %s. Consecutive failures: %s. Last success: %s",
                          ex, self._connection_failure_count, last_success_str)

            if self._last_good_input_regs and self._last_good_hold_regs and self._connection_failure_count <= MAX_CACHED_DATA_FAILURES:
                _LOGGER.warning("Returning cached data due to temporary connection failure")
                return {"input": self._last_good_input_regs, "hold": self._last_good_hold_regs, "battery": self._last_good_battery_data}
            else:
                if self._connection_failure_count <= MAX_EMPTY_DATA_FAILURES:
                    _LOGGER.warning("No cached data available, returning empty data structure")
                    return {"input": {}, "hold": {}, "battery": {}}
                else:
                    raise UpdateFailed(f"Error communicating with inverter: {ex}")

    async def async_write_register(self, register: int, value: int) -> bool:
        """Write a single register value to the inverter with validation and retries."""
        for attempt in range(self._connection_retries):
            writer = None

            try:
                async with self._lock:
                    _LOGGER.debug("Write attempt %s/%s for register %s with value %s",
                                  attempt + 1, self._connection_retries, register, value)

                    try:
                        reader, writer = await self._connection_manager.async_connect()
                    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                        _LOGGER.warning("Connection attempt failed during write: %s", e)
                        await asyncio.sleep(WRITE_RETRY_DELAY)
                        continue

                    await self._connection_manager.async_discard_initial_data(reader)

                    req = LxpRequestBuilder.prepare_packet_for_write(
                        self._dongle_serial.encode(), self._inverter_serial.encode(), register, value
                    )
                    writer.write(req)
                    await writer.drain()

                    response_buf = await reader.read(WRITE_RESPONSE_LENGTH)

                    _LOGGER.debug(
                        "Modbus WRITE: Sent to reg %s, value %s, resp: %s",
                        register, value, response_buf.hex() if response_buf else "None"
                    )

                    # Close the connection
                    await self._connection_manager.async_close(writer)
                    writer = None  # Mark as closed to prevent double-close in exception handler

                    # --- Response Validation ---
                    if not response_buf:
                        _LOGGER.warning("Write attempt %d failed: Response not received", attempt + 1)
                        await asyncio.sleep(WRITE_RETRY_DELAY)
                        continue

                    response = LxpResponse(response_buf)
                    if response.packet_error:
                        _LOGGER.warning("Write attempt %s failed: Inverter returned a packet error. %s",
                                        attempt + 1, response.info)
                        await asyncio.sleep(WRITE_RETRY_DELAY)
                        continue

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

                    await asyncio.sleep(WRITE_RETRY_DELAY)

            except Exception as ex:
                _LOGGER.error("Exception during write attempt %d for register %s: %s", attempt + 1, register, ex)
                if writer:
                    await self._connection_manager.async_close(writer)
                await asyncio.sleep(WRITE_RETRY_DELAY)

        _LOGGER.error("Failed to write register %s after %d attempts.", register, self._connection_retries)
        return False
