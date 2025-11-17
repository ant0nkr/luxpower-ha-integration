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


class ModbusRTUOverTCPTester:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.device_address = 1  # Standard Modbus device address for the inverter
    
    async def connect_and_test(self):
        """Connect to the ESP32/D1 Mini bridge and test Modbus RTU communication."""
        print(f"=== Modbus RTU over TCP Test ===")
        print(f"Connecting to {self.host}:{self.port}")
        print(f"Target: ESP D1 Mini TCP-to-RS485 bridge → Inverter")
        print(f"Protocol: Modbus RTU over TCP/IP")
        print(f"Inverter Address: {self.device_address}")
        print()
        
        try:
            # Connect to the ESP bridge
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10
            )
            print("✓ Connection to ESP bridge established successfully")
            
            # Test basic communication first
            print("\n--- Testing Basic Communication ---")
            
            # Try multiple approaches to break out of echo mode
            approaches = [
                ("Standard approach", 0, 1, 4),
                ("Try different register", 1, 1, 4),  
                ("Try holding registers", 0, 1, 3),
                ("Try multiple registers", 0, 2, 4),
                ("Try higher register", 100, 1, 4),
            ]
            
            basic_success = False
            for approach_name, reg, count, func in approaches:
                print(f"\n  → {approach_name}:")
                success = await self.test_register_read(reader, writer, reg, count, func)
                if success:
                    print(f"  ✓ {approach_name} worked!")
                    basic_success = True
                    break
                else:
                    print(f"  ✗ {approach_name} failed")
            
            if basic_success:
                print(f"\n✓ Basic Modbus communication working!")
                # Now try to read the serial number
                print("\n--- Reading Inverter Serial Number ---")
                serial_success = await self.read_serial_number(reader, writer)
                if serial_success:
                    print(f"✓ Successfully read serial number!")
                else:
                    print(f"✗ Failed to read serial number")
            else:
                print(f"\n✗ All communication approaches failed")
                print(f"   The ESP bridge appears to be in echo/loopback mode")
                print(f"   Possible solutions:")
                print(f"   1. Check ESP bridge firmware/configuration")
                print(f"   2. Verify RS485 connections to inverter") 
                print(f"   3. Check if inverter is powered and responding")
                print(f"   4. Verify inverter Modbus address (currently trying address 1)")
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            print("\n✓ Connection closed")
            
        except asyncio.TimeoutError:
            print("✗ Connection timeout - could not connect to ESP bridge")
        except ConnectionRefusedError:
            print("✗ Connection refused - ESP bridge may be offline or port incorrect")
        except Exception as e:
            print(f"✗ Connection error: {str(e)}")
    
    async def test_basic_registers(self, reader, writer) -> bool:
        """Test basic communication by reading a simple register."""
        print(f"Testing basic register read with device address {self.device_address}...")
        
        # Try reading input register 0 first
        dummy_dongle = b"0000000000"
        dummy_inverter = bytes([self.device_address]) + b"000000000"
        
        request = StandardModbusRequestBuilder.prepare_packet_for_read(
            dummy_dongle, dummy_inverter, 0, 1, 4  # Read 1 input register starting at 0
        )
        
        print(f"Basic test packet: {request.hex()}")
        print(f"  Address: {self.device_address}")
        print(f"  Function: 4 (Read Input Registers)")
        print(f"  Register: 0")
        print(f"  Count: 1")
        
        writer.write(request)
        await writer.drain()
        
        # Give device time to process
        await asyncio.sleep(0.5)
        
        try:
            response_data = await asyncio.wait_for(reader.read(64), timeout=3)
            if len(response_data) > 0:
                print(f"✓ Response received ({len(response_data)} bytes): {response_data.hex()}")
                
                # Check if it's an echo
                if response_data == request:
                    print("⚠️  Echo detected - ESP bridge might be echoing requests")
                    print("   This could mean:")
                    print("   1. ESP bridge is not connected to inverter")
                    print("   2. ESP bridge is in test/echo mode")
                    print("   3. Inverter is not responding")
                    print("   Let's try a different approach...")
                    
                    # Try waiting longer and reading more data
                    print("\n  Trying to read additional data...")
                    await asyncio.sleep(1)  # Wait longer
                    
                    try:
                        additional_data = await asyncio.wait_for(reader.read(64), timeout=2)
                        if additional_data and additional_data != response_data:
                            print(f"  ✓ Additional data received: {additional_data.hex()}")
                            # Combine and analyze
                            total_data = response_data + additional_data
                            print(f"  Total response: {total_data.hex()}")
                            return self.analyze_response(total_data)
                        else:
                            print("  ✗ No additional data or same echo")
                    except asyncio.TimeoutError:
                        print("  ✗ No additional data received")
                    
                    return False
                
                # Parse the response
                if len(response_data) >= 5:
                    addr = response_data[0]
                    func = response_data[1]
                    byte_count = response_data[2] if len(response_data) > 2 else 0
                    
                    print(f"Response analysis:")
                    print(f"  Address: {addr}")
                    print(f"  Function: {func}")
                    print(f"  Byte count: {byte_count}")
                    
                    # Check for valid response
                    if func == 4 and byte_count > 0:
                        print("✓ Valid Modbus response received!")
                        return True
                    elif func == 0x84:  # Exception response
                        exception_code = response_data[2] if len(response_data) > 2 else 0
                        print(f"✗ Modbus exception: {exception_code}")
                        return False
                
                return True  # Some response received, could be valid
            else:
                print("✗ No response")
                return False
                
        except asyncio.TimeoutError:
            print("✗ Response timeout")
            return False
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return False
    
    def analyze_response(self, response_data: bytes) -> bool:
        """Analyze response data to determine if it's valid Modbus."""
        print(f"\n=== Analyzing Response ({len(response_data)} bytes) ===")
        print(f"Data: {response_data.hex()}")
        
        if len(response_data) >= 5:
            addr = response_data[0]
            func = response_data[1]
            
            print(f"Address: {addr}")
            print(f"Function: 0x{func:02X}")
            
            if func == 4:  # Read Input Registers
                byte_count = response_data[2] if len(response_data) > 2 else 0
                print(f"Byte count: {byte_count}")
                
                if byte_count > 0 and len(response_data) >= 3 + byte_count + 2:
                    data = response_data[3:3+byte_count]
                    print(f"Register data: {data.hex()}")
                    print("✓ Valid Modbus response structure detected!")
                    return True
            elif func == 0x84:  # Exception response for function 4
                exception_code = response_data[2] if len(response_data) > 2 else 0
                print(f"✗ Modbus exception: {exception_code}")
            
            print("⚠️  Response structure unclear")
        else:
            print("✗ Response too short for valid Modbus")
        
        return False
    
    async def test_register_read(self, reader, writer, register: int, count: int, function: int) -> bool:
        """Test reading specific registers with given function code."""
        dummy_dongle = b"0000000000"
        dummy_inverter = bytes([self.device_address]) + b"000000000"
        
        request = StandardModbusRequestBuilder.prepare_packet_for_read(
            dummy_dongle, dummy_inverter, register, count, function
        )
        
        func_name = {3: "Hold", 4: "Input"}.get(function, str(function))
        print(f"    Testing {func_name} reg {register}, count {count}: {request.hex()}")
        
        writer.write(request)
        await writer.drain()
        await asyncio.sleep(0.3)
        
        try:
            response_data = await asyncio.wait_for(reader.read(64), timeout=2)
            if response_data and response_data != request:
                print(f"    ✓ Non-echo response: {response_data.hex()}")
                return self.analyze_response(response_data)
            elif response_data == request:
                print(f"    ⚠️  Echo response")
                return False
            else:
                print(f"    ✗ No response")
                return False
        except asyncio.TimeoutError:
            print(f"    ✗ Timeout")
            return False
    
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
                
                # Give the device time to process the request
                await asyncio.sleep(1)
                
                try:
                    response_data = await asyncio.wait_for(reader.read(64), timeout=2)
                    if len(response_data) > 0:
                        # Check if response is identical to request (echo mode)
                        if response_data == request:
                            print(f"    ⚠️  Echo detected from {function_name} register {reg}: {response_data.hex()}")
                            print(f"    ⚠️  Device is echoing requests - not processing Modbus properly!")
                            return False  # This is not a valid Modbus response
                        else:
                            print(f"    ✓ Got valid response from {function_name} register {reg}: {response_data.hex()}")
                            return True
                    else:
                        print(f"    ✗ Empty response from {function_name} register {reg}")
                except asyncio.TimeoutError:
                    print(f"    ✗ No response from {function_name} register {reg}")
                except Exception as e:
                    print(f"    ✗ Error reading {function_name} register {reg}: {str(e)}")
        
        return False
    
    async def read_serial_number(self, reader, writer) -> bool:
        """Read the inverter serial number from input registers 115-119."""
        print(f"📍 Reading serial number from device {self.device_address}...")
        print("Target: INPUT registers 115-119")
        print("Expected: 10-digit ASCII serial number (5 registers × 2 bytes each)")
        print()
        
        dummy_dongle = b"0000000000"
        dummy_inverter = bytes([self.device_address]) + b"000000000"
        
        # Read 5 input registers starting at register 115 (function code 4)
        request = StandardModbusRequestBuilder.prepare_packet_for_read(
            dummy_dongle, dummy_inverter, 115, 5, 4
        )
        
        print(f"Serial number request: {request.hex()}")
        print(f"  Address: {self.device_address}")
        print(f"  Function: 4 (Read Input Registers)")
        print(f"  Start Register: 115")
        print(f"  Register Count: 5")
        print()
        
        writer.write(request)
        await writer.drain()
        
        # Give device time to process
        await asyncio.sleep(0.5)
        
        try:
            # For 5 registers (10 bytes) + header (3 bytes) + CRC (2 bytes) = 15 bytes expected
            response_data = await asyncio.wait_for(reader.read(64), timeout=5)
            if len(response_data) > 0:
                print(f"✓ Serial number response received ({len(response_data)} bytes)")
                print(f"Raw response: {response_data.hex()}")
                print(f"Original request: {request.hex()}")
                
                # Check if this is an echo (response identical to request)
                if response_data == request:
                    print("⚠️  WARNING: Response is identical to request - device may be in echo/loopback mode!")
                    print("This suggests the device is not processing Modbus requests properly.")
                    return False
                
                print()
                success = await self.parse_serial_number_response(response_data)
                return success
            else:
                print("✗ Empty serial number response")
                return False
        except asyncio.TimeoutError:
            print("✗ Serial number response timeout")
            return False
        except Exception as e:
            print(f"✗ Serial number read error: {str(e)}")
            return False
    
    async def parse_serial_number_response(self, response_data: bytes) -> bool:
        """Parse the serial number response according to LuxPower documentation."""
        print("=== Serial Number Response Analysis ===")
        
        if len(response_data) < 5:
            print(f"✗ Response too short: {len(response_data)} bytes (minimum 5 expected)")
            return False
        
        # Parse Modbus response header
        address = response_data[0]
        function_code = response_data[1]
        
        print(f"Device Address: {address}")
        print(f"Function Code: {function_code}")
        
        # Check for Modbus exception
        if function_code & 0x80:
            print(f"✗ Modbus Exception Response!")
            if len(response_data) >= 3:
                exception_code = response_data[2]
                exception_names = {
                    1: "Illegal Function",
                    2: "Illegal Data Address", 
                    3: "Illegal Data Value",
                    4: "Slave Device Failure",
                    5: "Acknowledge",
                    6: "Slave Device Busy"
                }
                exception_name = exception_names.get(exception_code, f"Unknown ({exception_code})")
                print(f"Exception Code: {exception_code} - {exception_name}")
            return False
        
        # Parse successful response (function code 4 - Read Input Registers)
        if function_code != 4:
            print(f"✗ Unexpected function code: {function_code} (expected 4)")
            return False
        
        if len(response_data) < 3:
            print("✗ Response missing byte count")
            return False
        
        byte_count = response_data[2]
        print(f"Byte Count: {byte_count}")
        
        # Expect 10 bytes (5 registers × 2 bytes each)
        if byte_count != 10:
            print(f"✗ Unexpected byte count: {byte_count} (expected 10 for 5 registers)")
            return False
        
        # Extract data payload
        expected_total_length = 3 + byte_count + 2  # Header + Data + CRC
        if len(response_data) < expected_total_length:
            print(f"✗ Response too short: {len(response_data)} bytes (expected {expected_total_length})")
            return False
        
        serial_data = response_data[3:13]  # 10 bytes of serial number data
        crc_received = struct.unpack('<H', response_data[13:15])[0]
        
        print(f"Serial Data: {serial_data.hex()}")
        print(f"CRC: 0x{crc_received:04X}")
        
        # Verify CRC
        data_for_crc = response_data[:-2]
        calculated_crc = LxpPacketUtils.compute_crc(data_for_crc)
        
        if crc_received == calculated_crc:
            print("✓ CRC verification passed")
        else:
            print(f"⚠️  CRC verification failed (calculated: 0x{calculated_crc:04X})")
        
        print("\n=== Serial Number Decoding ===")
        
        # Decode serial number according to LuxPower format
        # Each register (2 bytes) contains 2 ASCII characters
        # Registers 115-119 = SN[0] through SN[9]
        serial_chars = []
        
        for i in range(5):  # 5 registers
            register_num = 115 + i
            byte_offset = i * 2
            
            if byte_offset + 1 < len(serial_data):
                # Each register contains 2 bytes (big endian format)
                char1_code = serial_data[byte_offset]
                char2_code = serial_data[byte_offset + 1]
                
                # Convert to ASCII characters
                char1 = chr(char1_code) if 32 <= char1_code <= 126 else '?'
                char2 = chr(char2_code) if 32 <= char2_code <= 126 else '?'
                
                print(f"Register {register_num}: 0x{char1_code:02X}{char2_code:02X} → SN[{i*2}]='{char1}' (0x{char1_code:02X}), SN[{i*2+1}]='{char2}' (0x{char2_code:02X})")
                
                serial_chars.append(char1)
                serial_chars.append(char2)
        
        # Construct the complete serial number
        serial_number = ''.join(serial_chars)
        
        print()
        print("🎯" + "="*50)
        print(f"🎯 INVERTER SERIAL NUMBER: '{serial_number}'")
        print("🎯" + "="*50)
        
        # Decode the serial number meaning according to LuxPower documentation
        print("\n=== Serial Number Analysis ===")
        if len(serial_number) >= 10:
            sn0_year = serial_number[0]
            sn1_week = serial_number[1] 
            sn2_week = serial_number[2]
            sn3_factory = serial_number[3]
            remaining = serial_number[4:10]
            
            print(f"SN[0] - Year: '{sn0_year}' (Year indicator)")
            print(f"SN[1] - Week: '{sn1_week}' (Week indicator 1)")  
            print(f"SN[2] - Week: '{sn2_week}' (Week indicator 2)")
            print(f"SN[3] - Factory: '{sn3_factory}' (Factory code)")
            print(f"SN[4-9] - Sequence: '{remaining}' (Production sequence)")
            
            # Validate format
            if serial_number.replace('?', '').isalnum():
                print("✓ Serial number format appears valid")
                return True
            else:
                print("⚠️  Serial number contains invalid characters")
                return False
        else:
            print("✗ Serial number too short")
            return False


async def main():
    # Test parameters
    host = "10.0.0.51"
    port = 502
    
    print("Modbus RTU over TCP/IP Test")
    print("=" * 50)
    print(f"Target: {host}:{port}")
    print("Setup: ESP D1 Mini TCP-to-RS485 bridge → Inverter")
    print("Protocol: Standard Modbus RTU over TCP/IP")
    print("Goal: Read serial number from input registers 115-119")
    print()
    
    tester = ModbusRTUOverTCPTester(host, port)
    await tester.connect_and_test()
    
    print("\n" + "=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(main())