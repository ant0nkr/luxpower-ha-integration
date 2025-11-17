import struct
import logging
from .lxp_packet_utils import LxpPacketUtils

_LOGGER = logging.getLogger(__name__)


class StandardModbusResponse:
    """
    Standard Modbus RTU response parser that handles responses according to 
    the official Modbus protocol as described in the documentation images.
    
    Standard Modbus response format:
    - Address (1 byte)
    - Function Code (1 byte) or Exception Code (1 byte with high bit set)
    - Data (N bytes) or Exception Code (1 byte for exceptions)
    - CRC (2 bytes)
    """

    def __init__(self, response_data: bytes):
        """Initialize the response parser with raw response data."""
        self.response_data = response_data
        self.packet_error = True
        self.error_type = "unknown"
        self.parsed_values_dictionary = {}
        self.device_function = None
        self.register = None
        self.address = None
        self.exception_code = None
        self.info = "No info available"
        
        if len(response_data) >= 5:  # Minimum valid response length
            self._parse_response()
    
    def _parse_response(self):
        """Parse the standard Modbus response."""
        try:
            # Extract basic fields
            self.address = self.response_data[0]
            function_code_byte = self.response_data[1]
            
            # Check for exception response
            if function_code_byte & 0x80:
                self._parse_exception_response(function_code_byte)
                return
            
            self.device_function = function_code_byte
            
            # Verify CRC
            if not self._verify_crc():
                self.error_type = "crc_error"
                self.info = f"CRC verification failed for address {self.address}, function {self.device_function}"
                return
            
            # Parse based on function code
            if self.device_function in [3, 4]:  # Read holding/input registers
                self._parse_read_response()
            elif self.device_function == 6:  # Write single register
                self._parse_write_single_response()
            elif self.device_function == 16:  # Write multiple registers
                self._parse_write_multiple_response()
            else:
                self.error_type = "unsupported_function"
                self.info = f"Unsupported function code: {self.device_function}"
                
        except Exception as e:
            self.error_type = "parse_error"
            self.info = f"Error parsing response: {str(e)}"
            _LOGGER.debug(f"StandardModbusResponse parse error: {e}")
    
    def _parse_exception_response(self, function_code_byte):
        """Parse a Modbus exception response."""
        self.device_function = function_code_byte & 0x7F  # Remove exception bit
        if len(self.response_data) >= 5:
            self.exception_code = self.response_data[2]
            if self._verify_crc():
                self.error_type = "modbus_exception"
                self.info = f"Modbus exception {self.exception_code} for function {self.device_function}"
            else:
                self.error_type = "crc_error"
                self.info = "CRC error in exception response"
        else:
            self.error_type = "incomplete_exception"
            self.info = "Incomplete exception response"
    
    def _parse_read_response(self):
        """Parse read registers response."""
        if len(self.response_data) < 5:
            self.error_type = "incomplete_response"
            self.info = "Response too short for read operation"
            return
        
        byte_count = self.response_data[2]
        expected_length = 3 + byte_count + 2  # Address + Function + Byte Count + Data + CRC
        
        if len(self.response_data) < expected_length:
            self.error_type = "incomplete_response"
            self.info = f"Expected {expected_length} bytes, got {len(self.response_data)}"
            return
        
        # Extract register values (big endian as per Modbus standard)
        data_start = 3
        data_end = 3 + byte_count
        register_data = self.response_data[data_start:data_end]
        
        register_count = byte_count // 2
        self.parsed_values_dictionary = {}
        
        # For standard Modbus read response, we need to map the data to register addresses
        # Since we don't know the starting register from the response, we'll store by index
        # and let the calling code map them to the correct registers
        for i in range(register_count):
            value = struct.unpack('>H', register_data[i*2:(i+1)*2])[0]
            self.parsed_values_dictionary[i] = value
        
        self.packet_error = False
        self.error_type = None
        self.info = f"Read {register_count} registers successfully"
    
    def _parse_write_single_response(self):
        """Parse write single register response."""
        if len(self.response_data) < 8:
            self.error_type = "incomplete_response"
            self.info = "Response too short for write single operation"
            return
        
        # Extract register address and value from echo response
        self.register = struct.unpack('>H', self.response_data[2:4])[0]
        written_value = struct.unpack('>H', self.response_data[4:6])[0]
        
        self.packet_error = False
        self.error_type = None
        self.info = f"Write to register {self.register} value {written_value} successful"
    
    def _parse_write_multiple_response(self):
        """Parse write multiple registers response."""
        if len(self.response_data) < 8:
            self.error_type = "incomplete_response"
            self.info = "Response too short for write multiple operation"
            return
        
        # Extract starting register and number of registers written
        self.register = struct.unpack('>H', self.response_data[2:4])[0]
        register_count = struct.unpack('>H', self.response_data[4:6])[0]
        
        self.packet_error = False
        self.error_type = None
        self.info = f"Write to {register_count} registers starting at {self.register} successful"
    
    def _verify_crc(self):
        """Verify the CRC of the response."""
        if len(self.response_data) < 4:
            return False
        
        # Extract CRC from response (last 2 bytes, little endian)
        received_crc = struct.unpack('<H', self.response_data[-2:])[0]
        
        # Calculate CRC for the data (everything except the CRC)
        data_for_crc = self.response_data[:-2]
        calculated_crc = LxpPacketUtils.compute_crc(data_for_crc)
        
        return received_crc == calculated_crc

    @property
    def serial_number(self):
        """Return the device address as a bytes object for compatibility."""
        if self.address is not None:
            return bytes([self.address] + [0] * 9)  # Pad to 10 bytes for compatibility
        return b'\x00' * 10

    @property
    def packet_length_calced(self):
        """Return the actual packet length for compatibility."""
        return len(self.response_data)