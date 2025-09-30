import asyncio
import logging
import time as time_lib

from homeassistant.helpers.update_coordinator import UpdateFailed

from ..const import *
from .lxp_request_builder import LxpRequestBuilder
from .lxp_response import LxpResponse

from ..constants.hold_registers import (
    H_AC_CHARGE_START_TIME, H_AC_CHARGE_END_TIME, H_AC_CHARGE_START_TIME_1, H_AC_CHARGE_END_TIME_1,
    H_AC_CHARGE_START_TIME_2, H_AC_CHARGE_END_TIME_2, H_AC_FIRST_START_TIME, H_AC_FIRST_END_TIME,
    H_AC_FIRST_START_TIME_1, H_AC_FIRST_END_TIME_1, H_PEAK_SHAVING_START_TIME, H_PEAK_SHAVING_END_TIME,
    H_PEAK_SHAVING_START_TIME_1, H_PEAK_SHAVING_END_TIME_1
)

_LOGGER = logging.getLogger(__name__)

HOLD_TIME_REGISTERS = {
    H_AC_CHARGE_START_TIME,
    H_AC_CHARGE_END_TIME,
    H_AC_CHARGE_START_TIME_1,
    H_AC_CHARGE_END_TIME_1,
    H_AC_CHARGE_START_TIME_2,
    H_AC_CHARGE_END_TIME_2,
    H_AC_FIRST_START_TIME,
    H_AC_FIRST_END_TIME,
    H_AC_FIRST_START_TIME_1,
    H_AC_FIRST_END_TIME_1,
    H_PEAK_SHAVING_START_TIME,
    H_PEAK_SHAVING_END_TIME,
    H_PEAK_SHAVING_START_TIME_1,
    H_PEAK_SHAVING_END_TIME_1,
}
INPUT_TIME_REGISTERS = set()


def _is_data_sane(registers: dict, register_type: str) -> bool:
    """Performs a sanity check on key values to detect data corruption."""
    time_registers = HOLD_TIME_REGISTERS if register_type == "hold" else INPUT_TIME_REGISTERS
    
    for register, value in registers.items():
        if register in time_registers:
            # The value is packed as Hour | (Minute << 8)
            hour = value & 0xFF
            minute = (value >> 8) & 0xFF
            _LOGGER.debug(f"Sanity check for {register_type} register {register} value: {value}: H={hour}, M={minute}")
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return False
    return True

class LxpModbusApiClient:
    """A client for communicating with a LuxPower inverter."""

    def __init__(self, host: str, port: int, dongle_serial: str, inverter_serial: str, lock: asyncio.Lock, block_size: int = 125, connection_retries: int = DEFAULT_CONNECTION_RETRIES):
        """Initialize the API client."""
        self._host = host
        self._port = port
        self._dongle_serial = dongle_serial
        self._inverter_serial = inverter_serial
        self._lock = lock
        self._block_size = block_size
        self._connection_retries = connection_retries
        self._last_good_input_regs = {}
        self._last_good_hold_regs = {}
        self._connection_retry_count = 0
        self._last_successful_connection = None
        self._connection_failure_count = 0


    async def async_get_data(self) -> dict:
        """Fetch data from the inverter, backfilling with old data on partial failure."""
        _LOGGER.debug("API Client: Polling the inverter for new data...")
        
        # Initialize connection state for this attempt
        connection_success = False
        connection_retry = False
        retry_delay = 30  # Seconds between retry attempts
        reader = None
        writer = None
        
        try:
            async with self._lock:
                # Try to establish a connection with retry logic
                for retry in range(self._connection_retries):
                    try:
                        if retry > 0:
                            _LOGGER.info(f"Connection retry attempt {retry}/{self._connection_retries}...")
                            connection_retry = True
                        
                        reader, writer = await asyncio.wait_for(
                            asyncio.open_connection(self._host, self._port),
                            timeout=10  # Connection timeout in seconds
                        )
                        connection_success = True
                        break
                    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                        if retry < self._connection_retries - 1:
                            _LOGGER.warning(f"Connection attempt failed: {str(e)}. Retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            # Increase delay for next retry if needed
                            retry_delay *= 1.5
                        else:
                            raise  # Re-raise the exception if we've exhausted retries
                
                # Update connection statistics
                if connection_success:
                    self._last_successful_connection = time_lib.time()
                    self._connection_failure_count = 0
                    if connection_retry:
                        self._connection_retry_count += 1
                        _LOGGER.info(f"Successfully reconnected after {retry} attempts")
                
                newly_polled_input_regs = {}
                newly_polled_hold_regs = {}
                input_read_success = True
                hold_read_success = True

                # Poll INPUT registers (expecting function code 4)
                for reg in range(0, TOTAL_REGISTERS, self._block_size):
                    count = min(self._block_size, TOTAL_REGISTERS - reg)
                    req = LxpRequestBuilder.prepare_packet_for_read(self._dongle_serial.encode(), self._inverter_serial.encode(), reg, count, 4)
                    expected_length = RESPONSE_OVERHEAD + (count * 2)
                    writer.write(req)
                    await writer.drain()
                    response_buf = await reader.read(expected_length)
                    
                    _LOGGER.debug(
                        "Polling INPUT %d-%d: Req[%d]: %s, Resp[%d/%d]: %s",
                        reg, reg + count - 1,
                        len(req),
                        req.hex(),
                        len(response_buf) if response_buf else 0,
                        expected_length,
                        response_buf.hex() if response_buf else "None"
                    )

                    if response_buf and len(response_buf) > RESPONSE_OVERHEAD:
                        response = LxpResponse(response_buf)
                        _LOGGER.debug(f"input_response {len(response.parsed_values_dictionary)}/{count} dict={response.parsed_values_dictionary}")
                        if len(response.parsed_values_dictionary) == count:
                            sane = _is_data_sane(response.parsed_values_dictionary, "input")
                            if not response.packet_error and response.serial_number == self._inverter_serial.encode() and sane:
                                newly_polled_input_regs.update(response.parsed_values_dictionary)
                            else:
                                _LOGGER.error(f"Invalid INPUT response packet_error={response.packet_error} sane={sane}")
                                input_read_success = False # Mark as failed
                        else:
                            _LOGGER.error("Invalid INPUT registers response expected=%d received=%d response[%d] %s:",
                                count,
                                len(response.parsed_values_dictionary),
                                len(response_buf) if response_buf else 0,
                                response_buf.hex() if response_buf else "None"
                            )
                            input_read_success = False # Mark as failed
                    else:
                        _LOGGER.error("Invalid INPUT response[%d] %s:", 
                            len(response_buf) if response_buf else 0,
                            response_buf.hex() if response_buf else "None"
                        )
                        input_read_success = False # Mark as failed

                    if not input_read_success:
                       break

                # Poll HOLD registers (expecting function code 3)
                for reg in range(0, TOTAL_REGISTERS, self._block_size):
                    count = min(self._block_size, TOTAL_REGISTERS - reg)
                    req = LxpRequestBuilder.prepare_packet_for_read(self._dongle_serial.encode(), self._inverter_serial.encode(), reg, count, 3)
                    expected_length = RESPONSE_OVERHEAD + (count * 2)
                    writer.write(req)
                    await writer.drain()
                    response_buf = await reader.read(expected_length)
                    
                    _LOGGER.debug(
                        "Polling HOLD %d-%d: Req[%d]: %s, Resp[%d/%d]: %s",
                        reg, reg + count - 1,
                        len(req),
                        req.hex(),
                        len(response_buf) if response_buf else 0,
                        expected_length,
                        response_buf.hex() if response_buf else "None"
                    )
                    
                    if response_buf and len(response_buf) > RESPONSE_OVERHEAD:
                        response = LxpResponse(response_buf)
                        _LOGGER.debug(f"hold_response {len(response.parsed_values_dictionary)}/{count} dict={response.parsed_values_dictionary}")
                        if len(response.parsed_values_dictionary) == count:
                            sane = _is_data_sane(response.parsed_values_dictionary, "hold")
                            if not response.packet_error and response.serial_number == self._inverter_serial.encode() and sane:
                                newly_polled_hold_regs.update(response.parsed_values_dictionary)
                            else:
                                _LOGGER.error(f"Invalid HOLD response packet_error={response.packet_error} sane={sane}")
                                hold_read_success = False # Mark as failed                                
                        else:
                            _LOGGER.error("Invalid HOLD registers response expected=%d received=%d response[%d] %s:",
                                count,
                                len(response.parsed_values_dictionary),
                                len(response_buf) if response_buf else 0,
                                response_buf.hex() if response_buf else "None"
                            )
                            hold_read_success = False # Mark as failed
                    else:
                        _LOGGER.error("Invalid HOLD response[%d] %s:", 
                            len(response_buf) if response_buf else 0,
                            response_buf.hex() if response_buf else "None"
                        )
                        hold_read_success = False # Mark as failed

                    if not hold_read_success:
                       break

                # Close the connection
                if writer:
                    try:
                        writer.close()
                        await asyncio.wait_for(writer.wait_closed(), timeout=5)
                    except (asyncio.TimeoutError, ConnectionError) as e:
                        _LOGGER.warning(f"Error closing connection: {str(e)}")
            
            # Merge new data with the last known good data
            if input_read_success:
                _LOGGER.debug(f"input = {newly_polled_input_regs}")
                self._last_good_input_regs = newly_polled_input_regs

            if hold_read_success:
                _LOGGER.debug(f"hold = {newly_polled_hold_regs}")
                self._last_good_hold_regs = newly_polled_hold_regs

            # Always return a complete (though possibly stale) dataset
            return {"input": self._last_good_input_regs, "hold": self._last_good_hold_regs}

        except Exception as ex:
            self._connection_failure_count += 1
            last_success_str = "never"
            if self._last_successful_connection:
                elapsed_time = time_lib.time() - self._last_successful_connection
                hours, remainder = divmod(elapsed_time, 3600)
                minutes, seconds = divmod(remainder, 60)
                last_success_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s ago"
            
            _LOGGER.exception(f"Total polling failure: {ex}. Consecutive failures: {self._connection_failure_count}. Last success: {last_success_str}")
            
            # If we have previously successful data and this is not a persistent failure,
            # return the cached data instead of raising an exception
            if self._last_good_input_regs and self._last_good_hold_regs and self._connection_failure_count <= 5:
                _LOGGER.warning("Returning cached data due to temporary connection failure")
                return {"input": self._last_good_input_regs, "hold": self._last_good_hold_regs}
            else:
                raise UpdateFailed(f"Error communicating with inverter: {ex}")


    async def async_write_register(self, register: int, value: int) -> bool:
        """Write a single register value to the inverter with validation and retries."""
        for attempt in range(self._connection_retries):
            reader = None
            writer = None
            connection_success = False
            
            try:
                # Use the shared lock to ensure atomicity
                async with self._lock:
                    _LOGGER.debug(f"Write attempt {attempt + 1}/{self._connection_retries} for register {register} with value {value}")

                    # Try to establish connection with timeout
                    try:
                        reader, writer = await asyncio.wait_for(
                            asyncio.open_connection(self._host, self._port),
                            timeout=10  # Connection timeout in seconds
                        )
                        connection_success = True
                    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                        _LOGGER.warning(f"Connection attempt failed during write: {str(e)}")
                        await asyncio.sleep(1)
                        continue

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

                    # Close the connection with timeout protection
                    try:
                        writer.close()
                        await asyncio.wait_for(writer.wait_closed(), timeout=5)
                    except (asyncio.TimeoutError, ConnectionError) as e:
                        _LOGGER.warning(f"Error closing write connection: {str(e)}")
                    
                    # --- Response Validation ---
                    if not response_buf:
                        _LOGGER.warning("Write attempt %d failed: Response not received", attempt + 1)
                        await asyncio.sleep(1)
                        continue

                    response = LxpResponse(response_buf)
                    if response.packet_error:
                        _LOGGER.warning("Write attempt %d failed: Inverter returned a packet error.", attempt + 1)
                        await asyncio.sleep(1)
                        continue
                    
                    response_dict = response.parsed_values_dictionary
                    if response_dict.get(register) == value:
                        _LOGGER.info("Successfully wrote register %s with value %s.", register, value)
                        return True # Success!

                    _LOGGER.warning("Write attempt %d failed: Confirmation mismatch.", attempt + 1)
                    await asyncio.sleep(1)

            except Exception as ex:
                _LOGGER.error("Exception during write attempt %d for register %s: %s", attempt + 1, register, ex)
                # Clean up the connection if it was opened
                if writer:
                    try:
                        writer.close()
                        await asyncio.wait_for(writer.wait_closed(), timeout=2)
                    except (asyncio.TimeoutError, ConnectionError):
                        pass  # Already in an exception handler, just ignore
                await asyncio.sleep(1)

        _LOGGER.error("Failed to write register %s after %d attempts.", register, self._connection_retries)
        return False