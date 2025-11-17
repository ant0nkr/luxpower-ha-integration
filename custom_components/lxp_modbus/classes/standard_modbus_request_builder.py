import struct
from .lxp_packet_utils import LxpPacketUtils


class StandardModbusRequestBuilder:
    """
    Standard Modbus RTU request builder that follows the official Modbus protocol
    as described in the documentation images.
    
    This builder creates packets according to the standard Modbus format:
    - Address (1 byte)
    - Function Code (1 byte)  
    - Data (N bytes)
    - CRC (2 bytes)
    """

    @staticmethod
    def prepare_packet_for_read(
        dongle_serial: bytes, serial_number: bytes,
        start_register: int, register_count: int = 1, function_code: int = 3
    ) -> bytes:
        """
        Prepare a standard Modbus read request packet.
        
        Args:
            dongle_serial: Dongle serial (unused in standard Modbus but kept for compatibility)
            serial_number: Inverter serial converted to address (first byte used as address)
            start_register: Starting register address
            register_count: Number of registers to read
            function_code: Modbus function code (3 for hold, 4 for input registers)
            
        Returns:
            bytes: Standard Modbus RTU packet
        """
        # Use first byte of serial number as device address, or default to 1
        if len(serial_number) > 0:
            address = serial_number[0] if serial_number[0] != 0 else 1
        else:
            address = 1
            
        # Build the packet: Address + Function Code + Start Address + Register Count
        packet = bytearray()
        packet.append(address)
        packet.append(function_code)
        packet.extend(struct.pack('>H', start_register))  # Big endian for standard Modbus
        packet.extend(struct.pack('>H', register_count))
        
        # Calculate CRC16 for the packet
        crc = LxpPacketUtils.compute_crc(bytes(packet))
        packet.extend(struct.pack('<H', crc))  # Little endian CRC as in original implementation
        
        return bytes(packet)

    @staticmethod
    def prepare_packet_for_write(
        dongle_serial: bytes, serial_number: bytes, register: int, value: int
    ) -> bytes:
        """
        Prepare a standard Modbus write single register request packet.
        
        Args:
            dongle_serial: Dongle serial (unused in standard Modbus but kept for compatibility)
            serial_number: Inverter serial converted to address (first byte used as address)
            register: Register address to write
            value: Value to write to the register
            
        Returns:
            bytes: Standard Modbus RTU packet for write single register (function code 6)
        """
        # Use first byte of serial number as device address, or default to 1
        if len(serial_number) > 0:
            address = serial_number[0] if serial_number[0] != 0 else 1
        else:
            address = 1
            
        # Build the packet: Address + Function Code (6) + Register Address + Value
        packet = bytearray()
        packet.append(address)
        packet.append(6)  # Function code 6 for write single register
        packet.extend(struct.pack('>H', register))  # Big endian for standard Modbus
        packet.extend(struct.pack('>H', value))
        
        # Calculate CRC16 for the packet
        crc = LxpPacketUtils.compute_crc(bytes(packet))
        packet.extend(struct.pack('<H', crc))  # Little endian CRC as in original implementation
        
        return bytes(packet)

    @staticmethod
    def prepare_packet_for_write_multiple(
        dongle_serial: bytes, serial_number: bytes, start_register: int, values: list
    ) -> bytes:
        """
        Prepare a standard Modbus write multiple registers request packet.
        
        Args:
            dongle_serial: Dongle serial (unused in standard Modbus but kept for compatibility)
            serial_number: Inverter serial converted to address (first byte used as address)
            start_register: Starting register address
            values: List of values to write
            
        Returns:
            bytes: Standard Modbus RTU packet for write multiple registers (function code 16)
        """
        # Use first byte of serial number as device address, or default to 1
        if len(serial_number) > 0:
            address = serial_number[0] if serial_number[0] != 0 else 1
        else:
            address = 1
            
        register_count = len(values)
        byte_count = register_count * 2
        
        # Build the packet: Address + Function Code (16) + Start Address + Register Count + Byte Count + Data
        packet = bytearray()
        packet.append(address)
        packet.append(16)  # Function code 16 for write multiple registers
        packet.extend(struct.pack('>H', start_register))  # Big endian for standard Modbus
        packet.extend(struct.pack('>H', register_count))
        packet.append(byte_count)
        
        # Add register values in big endian format
        for value in values:
            packet.extend(struct.pack('>H', value))
        
        # Calculate CRC16 for the packet
        crc = LxpPacketUtils.compute_crc(bytes(packet))
        packet.extend(struct.pack('<H', crc))  # Little endian CRC as in original implementation
        
        return bytes(packet)