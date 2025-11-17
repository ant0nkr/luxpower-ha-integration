import asyncio
import logging
import time as time_lib
from contextlib import suppress

from homeassistant.helpers.update_coordinator import UpdateFailed

from ..const import *
from .lxp_request_builder import LxpRequestBuilder
from .lxp_response import LxpResponse
from .standard_modbus_request_builder import StandardModbusRequestBuilder
from .standard_modbus_response import StandardModbusResponse

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
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                _LOGGER.debug(f"Sanity check failed for {register_type} register {register} value: {value}: H={hour}, M={minute}")
                return False
    return True

class LxpModbusApiClient:
    """A client for communicating with a LuxPower inverter."""

    def __init__(self, host: str, port: int, dongle_serial: str, inverter_serial: str, lock: asyncio.Lock, 
                 block_size: int = 125, connection_retries: int = DEFAULT_CONNECTION_RETRIES,
                 skip_initial_data: bool = True, protocol_type: str = PROTOCOL_TYPE_LXP):
        """Initialize the API client."""
        self._host = host
        self._port = port
        self._dongle_serial = dongle_serial
        self._inverter_serial = inverter_serial
        self._lock = lock
        self._block_size = block_size
        self._connection_retries = connection_retries
        self._skip_initial_data = skip_initial_data
        self._protocol_type = protocol_type
        self._last_good_input_regs = {}
        self._last_good_hold_regs = {}
        self._connection_retry_count = 0
        self._last_successful_connection = None
        self._connection_failure_count = 0
        
        # Set request builder and response class based on protocol type
        if self._protocol_type == PROTOCOL_TYPE_DEFAULT:
            self._request_builder = StandardModbusRequestBuilder
            self._response_class = StandardModbusResponse
            # For standard Modbus, we don't need to skip initial data
            self._skip_initial_data = False
        else:
            self._request_builder = LxpRequestBuilder
            self._response_class = LxpResponse
        
        # Packet recovery statistics
        self._recovery_attempts_total = 0
        self._recovery_successes = 0
        self._recovery_failures = 0

    async def async_safe_packet_recovery(self, reader, response_buf: bytes, expected_length: int, request_type: str, function_code: int) -> LxpResponse:
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
            _LOGGER.debug(f"No recovery needed for {request_type}({function_code}): missing_bytes={missing_bytes}")
            return original_response
            
        if original_response.packet_length_calced > MAX_PACKET_SIZE:
            _LOGGER.warning(f"Packet too large for {request_type}({function_code}): {original_response.packet_length_calced} > {MAX_PACKET_SIZE}, skipping recovery")
            return original_response
            
        if missing_bytes > (MAX_PACKET_SIZE - expected_length):
            _LOGGER.warning(f"Missing bytes too large for {request_type}({function_code}): {missing_bytes}, skipping recovery")
            return original_response
        
        # Attempt packet recovery with retry limit
        recovery_attempts = 0
        accumulated_data = response_buf
        self._recovery_attempts_total += 1
        
        while recovery_attempts < MAX_PACKET_RECOVERY_ATTEMPTS:
            try:
                recovery_attempts += 1
                _LOGGER.debug(f"Attempting packet recovery #{recovery_attempts} for {request_type}({function_code}): need {missing_bytes} more bytes")
                
                # Read missing bytes with timeout
                new_data = await asyncio.wait_for(reader.read(missing_bytes), timeout=PACKET_RECOVERY_TIMEOUT)
                
                if not new_data:
                    _LOGGER.debug(f"No additional data received on recovery attempt #{recovery_attempts}")
                    break
                    
                accumulated_data += new_data
                recovered_response = LxpResponse(accumulated_data)
                
                # Check if recovery was successful
                if not recovered_response.packet_error:
                    _LOGGER.debug(f"Packet recovery successful on attempt #{recovery_attempts} for {request_type}({function_code})")
                    self._recovery_successes += 1
                    return recovered_response
                
                # If still in error but length changed, adjust missing bytes for next attempt
                if recovered_response.packet_length_calced != original_response.packet_length_calced:
                    new_missing = recovered_response.packet_length_calced - len(accumulated_data)
                    if new_missing > 0 and new_missing <= (MAX_PACKET_SIZE - len(accumulated_data)):
                        missing_bytes = new_missing
                        original_response = recovered_response
                        continue
                    
                _LOGGER.debug(f"Recovery attempt #{recovery_attempts} failed for {request_type}({function_code}): {recovered_response.error_type}")
                break
                
            except asyncio.TimeoutError:
                _LOGGER.debug(f"Timeout on recovery attempt #{recovery_attempts} for {request_type}({function_code})")
                break
            except Exception as e:
                _LOGGER.warning(f"Error during packet recovery attempt #{recovery_attempts} for {request_type}({function_code}): {e}")
                break
        
        _LOGGER.debug(f"Packet recovery failed after {recovery_attempts} attempts for {request_type}({function_code})")
        self._recovery_failures += 1
        return original_response

    async def async_request_registers(self, writer, reader, reg, request_type, function_code) -> dict:
        count = min(self._block_size, TOTAL_REGISTERS - reg)
        req = self._request_builder.prepare_packet_for_read(self._dongle_serial.encode(), self._inverter_serial.encode(), reg, count, function_code)
        
        # Calculate expected response length based on protocol type
        if self._protocol_type == PROTOCOL_TYPE_DEFAULT:
            # Standard Modbus: Address + Function + Byte Count + Data + CRC
            expected_length = 5 + (count * 2)  # 3 bytes header + data + 2 bytes CRC
        else:
            # LXP protocol
            expected_length = RESPONSE_OVERHEAD + (count * 2)
            
        writer.write(req)
        await writer.drain()
        response_buf = await asyncio.wait_for(reader.read(expected_length), timeout=3) 
                    
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

        if response_buf and len(response_buf) > (5 if self._protocol_type == PROTOCOL_TYPE_DEFAULT else RESPONSE_OVERHEAD):
            response = self._response_class(response_buf)

            # Attempt safe packet recovery if needed (only for LXP protocol)
            if (self._protocol_type == PROTOCOL_TYPE_LXP and response.packet_error 
                and hasattr(response, 'packet_length_calced') and response.packet_length_calced > expected_length):
                response = await self.async_safe_packet_recovery(reader, response_buf, expected_length, request_type, function_code)
               
            # Validate response based on protocol type
            if self._protocol_type == PROTOCOL_TYPE_DEFAULT:
                # Standard Modbus validation
                is_valid = (not response.packet_error 
                           and function_code == response.device_function
                           and _is_data_sane(response.parsed_values_dictionary, request_type))
                
                # For standard Modbus, we need to map the response registers to actual register addresses
                if is_valid and response.parsed_values_dictionary:
                    mapped_registers = {}
                    for i, value in response.parsed_values_dictionary.items():
                        mapped_registers[reg + i] = value
                    response.parsed_values_dictionary = mapped_registers
            else:
                # LXP protocol validation
                is_valid = (not response.packet_error 
                           and response.serial_number == self._inverter_serial.encode() 
                           and function_code == response.device_function
                           and reg == response.register 
                           and _is_data_sane(response.parsed_values_dictionary, request_type))
                           
            if is_valid:
               
                # We missed or received more registers but response appear to be valid
                # keeping this debug log can help on more strange cases
                if len(response.parsed_values_dictionary) != count:
                    _LOGGER.debug(f"{request_type}({function_code}) response has different register count ({len(response.parsed_values_dictionary)}) than requested ({count})")
                    
                return response.parsed_values_dictionary
            else:
                _LOGGER.debug(f"ignoring {request_type}({function_code}) packet for regs {reg}-{reg + count -1} : "
                              f"response={response.info}")

        return {}
    
    async def async_discard_initial_data(self, reader):
        # DG dongle is returning sometimes a packet after connection then flush the input buffer
        if not self._skip_initial_data:
           return
        with suppress(asyncio.TimeoutError):
            # if the dongle send data at start of connection probably 1 second is sufficient to ignore received data
            # for dongles that does not send data this will make an small 1s delay, without other problems
            ignored = await asyncio.wait_for(reader.read(300), timeout=1)
            if ignored:
                response = LxpResponse(ignored)
                # Debug to try to understand if we can get any usefull information from this data
                # in future we can just ignore if this is not usefull
                # data that came on initial tests with DG dongle is not fixed, apparently all are function 3, most of times with regs 0-79 other times only 7-8
                _LOGGER.debug(f"ignored start data from dongle response={response.info} {ignored.hex()}")
    
    def get_recovery_stats(self) -> dict:
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
                
                # TODO: check better this condition, apparently it will only arrive here with connection_success == True because on last retry it will raise the exception
                # Update connection statistics
                if connection_success:
                    self._last_successful_connection = time_lib.time()
                    self._connection_failure_count = 0
                    if connection_retry:
                        self._connection_retry_count += 1
                        _LOGGER.info(f"Successfully reconnected after {retry} attempts")
                
                newly_polled_input_regs = {}
                newly_polled_hold_regs = {}

                await self.async_discard_initial_data(reader)
                    
                try:
                    # Poll INPUT registers (expecting function code 4)
                    for reg in range(0, TOTAL_REGISTERS, self._block_size):
                        dict = await self.async_request_registers(writer, reader, reg, "input", 4)
                        if len(dict) > 0:
                            newly_polled_input_regs.update(dict)

                    # Poll HOLD registers (expecting function code 3)
                    for reg in range(0, TOTAL_REGISTERS, self._block_size):
                        dict = await self.async_request_registers(writer, reader, reg, "hold", 3)
                        if len(dict) > 0:
                            newly_polled_hold_regs.update(dict)

                except asyncio.TimeoutError as e:
                    # something is wrong as requests should be fast after connect
                    # better to try again next time, then skip all other requests for this time
                    _LOGGER.debug(f"Timeout requesting data from inverter")

                # Close the connection
                if writer:
                    try:
                        writer.close()
                        await asyncio.wait_for(writer.wait_closed(), timeout=5)
                    except (asyncio.TimeoutError, ConnectionError) as e:
                        _LOGGER.warning(f"Error closing connection: {str(e)}")
            
            # Merge new data with the last known good data
            if len(newly_polled_input_regs):
                self._last_good_input_regs.update(newly_polled_input_regs)

            if len(newly_polled_hold_regs):
                self._last_good_hold_regs.update(newly_polled_hold_regs)

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
            
            _LOGGER.error(f"Total polling failure: {ex}. Consecutive failures: {self._connection_failure_count}. Last success: {last_success_str}")
            
            # If we have previously successful data and this is not a persistent failure,
            # return the cached data instead of raising an exception
            if self._last_good_input_regs and self._last_good_hold_regs and self._connection_failure_count <= 5:
                _LOGGER.warning("Returning cached data due to temporary connection failure")
                return {"input": self._last_good_input_regs, "hold": self._last_good_hold_regs}
            else:
                # For initial failures or persistent failures, return empty but valid structure
                if self._connection_failure_count <= 3:
                    _LOGGER.warning("No cached data available, returning empty data structure")
                    return {"input": {}, "hold": {}}
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

                    await self.async_discard_initial_data(reader)
                    
                    req = self._request_builder.prepare_packet_for_write(
                        self._dongle_serial.encode(), self._inverter_serial.encode(), register, value
                    )
                    writer.write(req)
                    await writer.drain()

                    # Calculate expected response length based on protocol type
                    if self._protocol_type == PROTOCOL_TYPE_DEFAULT:
                        # Standard Modbus write response: Address + Function + Register + Value + CRC = 8 bytes
                        response_length = 8
                    else:
                        # LXP protocol
                        response_length = WRITE_RESPONSE_LENGTH
                        
                    response_buf = await reader.read(response_length)
                    
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

                    response = self._response_class(response_buf)
                    if response.packet_error:
                        _LOGGER.warning(f"Write attempt {attempt + 1} failed: Inverter returned a packet error. {response.info}")
                        await asyncio.sleep(1)
                        continue
                    
                    # Validation based on protocol type
                    if self._protocol_type == PROTOCOL_TYPE_DEFAULT:
                        # For standard Modbus, check if the response confirms the write
                        if (hasattr(response, 'register') and response.register == register):
                            _LOGGER.info("Successfully wrote register %s with value %s (standard Modbus).", register, value)
                            return True
                    else:
                        # LXP protocol validation
                        response_dict = response.parsed_values_dictionary
                        if register in response_dict:
                            received_value = response_dict.get(register)
                            if received_value == value:
                                _LOGGER.info("Successfully wrote register %s with value %s (LXP protocol).", register, value)
                                return True # Success!

                            _LOGGER.warning(f"Write attempt {attempt + 1} failed: Confirmation mismatch, sent={value} received={received_value}")
                        else:
                            _LOGGER.warning(f"Write attempt {attempt + 1} failed: Confirmation mismatch, written register {register} not received on confirmation. {response.info}")

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