#!/usr/bin/env python3
"""
Test script to connect to a real inverter using standard Modbus RTU protocol
and read the serial number from input registers 115-119.
"""

import asyncio
import struct
import sys
import os

# Add the project path to import our modules
sys.path.insert(0, '/Users/akramskyi/git/luxpower-modbus-hacs/custom_components/lxp_modbus')

from classes.standard_modbus_request_builder import StandardModbusRequestBuilder
from classes.standard_modbus_response import StandardModbusResponse
from classes.lxp_packet_utils import LxpPacketUtils


class ModbusRTUTester:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.device_addresses_to_try = [0, 1, 2, 3, 247, 255]  # Include broadcast and common addresses
    
    async def connect_and_test(self):
        """Connect to the inverter and test standard Modbus communication."""
        print(f"=== Modbus RTU Test ===")
        print(f"Connecting to {self.host}:{self.port}")
        print()
        
        try:
            # Connect to the inverter
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10
            )
            print("✓ Connection established successfully")
            
            # Try different device addresses
            for addr in self.device_addresses_to_try:
                print(f"\n--- Trying Device Address {addr} ---")
                
                # First try a simple register read (register 0)
                simple_success = await self.simple_register_test(reader, writer, addr)
                if simple_success:
                    print(f"✓ Device responds at address {addr}")
                    # Now try to read the serial number
                    serial_success = await self.read_serial_number(reader, writer, addr)
                    if serial_success:
                        print(f"✓ Successfully read serial number from address {addr}!")
                        break
                else:
                    print(f"✗ No response from device address {addr}")
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            print("\n✓ Connection closed")
            
        except asyncio.TimeoutError:
            print("✗ Connection timeout - could not connect to inverter")
        except ConnectionRefusedError:
            print("✗ Connection refused - inverter may be offline or port incorrect")
        except Exception as e:
            print(f"✗ Connection error: {str(e)}")
    
    async def simple_register_test(self, reader, writer, device_address: int) -> bool:
        """Test basic connectivity by reading different register types."""
        print(f"Testing basic connectivity with address {device_address}...")
        
        # Try both input registers (function 4) and holding registers (function 3)
        for function_code in [4, 3]:
            function_name = "Input" if function_code == 4 else "Holding"
            print(f"  Trying {function_name} registers (function {function_code})...")
            
            dummy_dongle = b"0000000000"
            dummy_inverter = bytes([device_address]) + b"000000000"
            
            # Try register 0 first, then register 1 if no response
            for reg in [0, 1]:
                request = StandardModbusRequestBuilder.prepare_packet_for_read(
                    dummy_dongle, dummy_inverter, reg, 1, function_code
                )
                
                print(f"    Register {reg} packet: {request.hex()}")
                
                writer.write(request)
                await writer.drain()
                
                try:
                    response_data = await asyncio.wait_for(reader.read(64), timeout=1)
                    if len(response_data) > 0:
                        print(f"    ✓ Got response from {function_name} register {reg}: {response_data.hex()}")
                        return True
                    else:
                        print(f"    ✗ Empty response from {function_name} register {reg}")
                except asyncio.TimeoutError:
                    print(f"    ✗ No response from {function_name} register {reg}")
                except Exception as e:
                    print(f"    ✗ Error reading {function_name} register {reg}: {str(e)}")
        
        return False

import asyncio
import struct
import sys
import os

# Add the project path to import our modules
sys.path.insert(0, '/Users/akramskyi/git/luxpower-modbus-hacs/custom_components/lxp_modbus')

from classes.standard_modbus_request_builder import StandardModbusRequestBuilder
from classes.standard_modbus_response import StandardModbusResponse
from classes.lxp_packet_utils import LxpPacketUtils


class ModbusRTUTester:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.device_addresses_to_try = [0, 1, 2, 3, 247, 255]  # Include broadcast and common addresses
    
    async def connect_and_test(self):
        """Connect to the inverter and test standard Modbus communication."""
        print(f"=== Modbus RTU Test ===")
        print(f"Connecting to {self.host}:{self.port}")
        print()
        
        try:
            # Connect to the inverter
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10
            )
            print("✓ Connection established successfully")
            
            # Try different device addresses
            for addr in self.device_addresses_to_try:
                print(f"\n--- Trying Device Address {addr} ---")
                
                # First try a simple register read (register 0)
                simple_success = await self.simple_register_test(reader, writer, addr)
                if simple_success:
                    print(f"✓ Device responds at address {addr}")
                    # Now try to read the serial number
                    serial_success = await self.read_serial_number(reader, writer, addr)
                    if serial_success:
                        print(f"✓ Successfully read serial number from address {addr}!")
                        break
                else:
                    print(f"✗ No response from device address {addr}")
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            print("\n✓ Connection closed")
            
        except asyncio.TimeoutError:
            print("✗ Connection timeout - could not connect to inverter")
        except ConnectionRefusedError:
            print("✗ Connection refused - inverter may be offline or port incorrect")
        except Exception as e:
            print(f"✗ Connection error: {str(e)}")
    
    async def simple_register_test(self, reader, writer, device_address: int) -> bool:
        """Test basic connectivity by reading different register types."""
        print(f"Testing basic connectivity with address {device_address}...")
        
        # Try both input registers (function 4) and holding registers (function 3)
        for function_code in [4, 3]:
            function_name = "Input" if function_code == 4 else "Holding"
            print(f"  Trying {function_name} registers (function {function_code})...")
            
            dummy_dongle = b"0000000000"
            dummy_inverter = bytes([device_address]) + b"000000000"
            
            # Try register 0 first, then register 1 if no response
            for reg in [0, 1]:
                request = StandardModbusRequestBuilder.prepare_packet_for_read(
                    dummy_dongle, dummy_inverter, reg, 1, function_code
                )
                
                print(f"    Register {reg} packet: {request.hex()}")
                
                writer.write(request)
                await writer.drain()
                
                try:
                    response_data = await asyncio.wait_for(reader.read(64), timeout=1)
                    if len(response_data) > 0:
                        print(f"    ✓ Got response from {function_name} register {reg}: {response_data.hex()}")
                        return True
                    else:
                        print(f"    ✗ Empty response from {function_name} register {reg}")
                except asyncio.TimeoutError:
                    print(f"    ✗ No response from {function_name} register {reg}")
                except Exception as e:
                    print(f"    ✗ Error reading {function_name} register {reg}: {str(e)}")
        
        return False
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            print("\n✓ Connection closed")
            
        except asyncio.TimeoutError:
            print("✗ Connection timeout - could not connect to inverter")
        except ConnectionRefusedError:
            print("✗ Connection refused - inverter may be offline or port incorrect")
        except Exception as e:
            print(f"✗ Connection error: {str(e)}")
    
    async def read_serial_number(self, reader, writer, device_address: int) -> bool:
        """Read the inverter serial number from input registers 115-119."""
        print(f"Device Address: {device_address}")
        print("Registers: 115-119 (INPUT registers)")
        print("Expected: 10-digit ASCII serial number (5 registers × 2 bytes each)")
        
        # Create standard Modbus request
        # Function 4 = Read Input Registers
        # Start register: 115
        # Count: 5 registers (10 bytes for 10 ASCII characters)
        
        # Use dummy serial numbers for compatibility with our builder
        dummy_dongle = b"0000000000"
        dummy_inverter = bytes([device_address]) + b"000000000"
        
        request = StandardModbusRequestBuilder.prepare_packet_for_read(
            dummy_dongle, dummy_inverter, 115, 5, 4  # Function 4 for input registers
        )
        
        print(f"Request packet: {request.hex()}")
        print(f"Request breakdown:")
        print(f"  Address: 0x{request[0]:02X}")
        print(f"  Function: 0x{request[1]:02X} (Read Input Registers)")
        print(f"  Start Register: {struct.unpack('>H', request[2:4])[0]}")
        print(f"  Register Count: {struct.unpack('>H', request[4:6])[0]}")
        print(f"  CRC: 0x{struct.unpack('<H', request[6:8])[0]:04X}")
        
        # Send request
        writer.write(request)
        await writer.drain()
        print("✓ Request sent")
        
        # Read response with shorter timeout for faster address scanning
        expected_response_length = 3 + 10 + 2  # Header + Data + CRC
        
        try:
            response_data = await asyncio.wait_for(reader.read(expected_response_length), timeout=2)
            print(f"✓ Response received: {len(response_data)} bytes")
            print(f"Response packet: {response_data.hex()}")
            
            if len(response_data) > 0:
                await self.parse_serial_response(response_data)
                return True  # Success
            else:
                print("✗ Empty response received")
                return False
                
        except asyncio.TimeoutError:
            print("✗ Response timeout - no data received")
            return False
        except Exception as e:
            print(f"✗ Error reading response: {str(e)}")
            return False
    
    async def parse_serial_response(self, response_data: bytes):
        """Parse the serial number response."""
        print()
        print("--- Parsing Response ---")
        
        if len(response_data) < 5:
            print(f"✗ Response too short: {len(response_data)} bytes")
            return
        
        # Parse response manually for detailed analysis
        address = response_data[0]
        function = response_data[1]
        
        print(f"Address: 0x{address:02X}")
        print(f"Function: 0x{function:02X}")
        
        # Check for exception response
        if function & 0x80:
            print(f"✗ Modbus Exception Response!")
            if len(response_data) >= 3:
                exception_code = response_data[2]
                exception_codes = {
                    1: "Illegal Function",
                    2: "Illegal Data Address", 
                    3: "Illegal Data Value",
                    4: "Slave Device Failure",
                    5: "Acknowledge",
                    6: "Slave Device Busy"
                }
                exception_name = exception_codes.get(exception_code, f"Unknown ({exception_code})")
                print(f"Exception Code: {exception_code} - {exception_name}")
            return
        
        if function == 4:  # Read Input Registers response
            if len(response_data) >= 3:
                byte_count = response_data[2]
                print(f"Byte Count: {byte_count}")
                
                if len(response_data) >= 3 + byte_count + 2:
                    # Extract data
                    data = response_data[3:3+byte_count]
                    crc_received = struct.unpack('<H', response_data[-2:])[0]
                    
                    print(f"Data: {data.hex()}")
                    print(f"CRC: 0x{crc_received:04X}")
                    
                    # Verify CRC
                    data_for_crc = response_data[:-2]
                    calculated_crc = LxpPacketUtils.compute_crc(data_for_crc)
                    
                    if crc_received == calculated_crc:
                        print("✓ CRC verification passed")
                    else:
                        print(f"✗ CRC verification failed (calculated: 0x{calculated_crc:04X})")
                    
                    # Parse serial number
                    if byte_count == 10:  # 5 registers × 2 bytes = 10 bytes
                        print()
                        print("--- Serial Number Parsing ---")
                        
                        # Convert data to ASCII characters
                        serial_chars = []
                        for i in range(0, len(data), 2):
                            if i + 1 < len(data):
                                # Each register contains 2 ASCII characters (big endian)
                                char1 = data[i]
                                char2 = data[i + 1]
                                
                                print(f"Register {115 + i//2}: 0x{char1:02X}{char2:02X} -> '{chr(char1) if 32 <= char1 <= 126 else '?'}{chr(char2) if 32 <= char2 <= 126 else '?'}'")
                                
                                serial_chars.append(chr(char1) if 32 <= char1 <= 126 else '?')
                                serial_chars.append(chr(char2) if 32 <= char2 <= 126 else '?')
                        
                        serial_number = ''.join(serial_chars)
                        print()
                        print(f"🎯 Serial Number: '{serial_number}'")
                        
                        # Validate serial number format
                        if len(serial_number) == 10 and serial_number.replace('?', '').isalnum():
                            print("✓ Serial number format appears valid")
                        else:
                            print("⚠️  Serial number format may be unusual")
                    else:
                        print(f"⚠️  Unexpected data length: {byte_count} bytes (expected 10)")
                else:
                    print("✗ Response packet too short for data")
        else:
            print(f"✗ Unexpected function code in response: {function}")
        
        # Also try parsing with our StandardModbusResponse class
        print()
        print("--- Using StandardModbusResponse Parser ---")
        response_obj = StandardModbusResponse(response_data)
        print(f"Packet Error: {response_obj.packet_error}")
        print(f"Info: {response_obj.info}")
        if not response_obj.packet_error:
            print(f"Parsed Values: {response_obj.parsed_values_dictionary}")


async def main():
    # Test parameters
    host = "10.0.0.51"
    port = 502
    
    print("Standard Modbus RTU Inverter Test")
    print("=" * 50)
    print(f"Target: {host}:{port}")
    print("Goal: Read serial number from input registers 115-119")
    print()
    
    tester = ModbusRTUTester(host, port)
    await tester.connect_and_test()
    
    print()
    print("=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(main())