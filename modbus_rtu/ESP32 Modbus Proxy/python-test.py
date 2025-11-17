#!/usr/bin/env python3
"""
LUX Modbus Client
Simple Python client for communicating with LUX inverters via ESP8266 Modbus proxy.
Supports both standard (8-byte) and non-standard (18-byte) LUX formats.
"""

import socket
import struct
import time
import json
from typing import Optional, List

class LuxModbusClient:
    def __init__(self, host: str = "10.0.0.51", port: int = 502, timeout: float = 5.0):
        """Initialize LUX Modbus client"""
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        
        # Default settings - modify these for your inverter
        self.inverter_serial = "3263632313"  # 10-digit serial number
        self.slave_address = 1               # Modbus slave address
        
        print(f"🔌 LUX Modbus Client initialized")
        print(f"   Target: {host}:{port}")
        print(f"   Serial: {self.inverter_serial}")
        print(f"   Slave:  {self.slave_address}")
    
    def set_inverter_serial(self, serial_number: str):
        """Set the inverter serial number (10 digits)"""
        if len(serial_number) != 10 or not serial_number.isdigit():
            raise ValueError("Serial number must be exactly 10 digits")
        self.inverter_serial = serial_number
        print(f"📝 Inverter serial updated: {self.inverter_serial}")
    
    def connect(self) -> bool:
        """Connect to the ESP8266 proxy"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            print(f"✅ Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the proxy"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("🔌 Disconnected")
    
    def calculate_crc16(self, data: bytes) -> int:
        """Calculate Modbus RTU CRC16 checksum"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc
    
    def send_request(self, frame: bytes, description: str = "") -> Optional[bytes]:
        """Send a Modbus request and receive response"""
        if not self.socket:
            print("❌ Not connected!")
            return None
        
        try:
            print(f"\n📤 Sending {description}:")
            print(f"   HEX: {frame.hex(' ').upper()}")
            print(f"   Length: {len(frame)} bytes")
            
            self.socket.sendall(frame)
            
            # Receive response
            response = b""
            start_time = time.time()
            
            while time.time() - start_time < self.timeout:
                try:
                    chunk = self.socket.recv(1024)
                    if chunk:
                        response += chunk
                        # Simple heuristic: wait for complete frame
                        self.socket.settimeout(0.2)
                    else:
                        break
                except socket.timeout:
                    if response:
                        break
                    continue
            
            # Restore timeout
            self.socket.settimeout(self.timeout)
            
            if response:
                print(f"📥 Response received:")
                print(f"   HEX: {response.hex(' ').upper()}")
                print(f"   Length: {len(response)} bytes")
                self.decode_response(response)
                return response
            else:
                print("⏰ No response received")
                return None
                
        except Exception as e:
            print(f"❌ Communication error: {e}")
            return None
    
    def decode_response(self, response: bytes):
        """Decode and display response information"""
        if len(response) < 3:
            print("   ❌ Response too short")
            return
        
        address = response[0]
        function_code = response[1]
        
        print(f"   Address: {address}")
        print(f"   Function: 0x{function_code:02X}", end="")
        
        # Check for error
        if function_code & 0x80:
            print(" (ERROR)")
            if len(response) >= 3:
                error_code = response[2]
                errors = {
                    0x01: "Illegal Function",
                    0x02: "Illegal Data Address", 
                    0x03: "Illegal Data Value",
                    0x04: "Server Device Failure"
                }
                print(f"   Error: 0x{error_code:02X} ({errors.get(error_code, 'Unknown')})")
            return
        
        # Normal response
        if function_code in [0x03, 0x04]:
            print(" (Read Registers)")
            if len(response) >= 3:
                byte_count = response[2]
                print(f"   Data bytes: {byte_count}")
                
                # Check if this could be non-standard format with serial number
                if byte_count >= 10 and len(response) >= 13:
                    # Try to decode as serial number
                    serial_data = response[3:13]
                    try:
                        serial_str = ''.join([chr(b) for b in serial_data if 32 <= b <= 126])
                        if len(serial_str) == 10 and serial_str.isalnum():
                            print(f"   Serial Number: {serial_str}")
                            print(f"   Format: Non-standard LUX response")
                            return
                    except:
                        pass
                
                # Standard format - show register values
                if len(response) >= 3 + byte_count:
                    print(f"   Registers:", end="")
                    for i in range(3, 3 + byte_count, 2):
                        if i + 1 < len(response):
                            reg_value = (response[i] << 8) | response[i + 1]
                            print(f" {reg_value}", end="")
                    print()
        else:
            print(" (Write Response)")
    
    def read_registers_standard(self, start_address: int, quantity: int, function_code: int = 0x04) -> Optional[bytes]:
        """
        Standard LUX format: 8 bytes total
        Format: [Address][Function][Start_Addr_H][Start_Addr_L][Quantity_H][Quantity_L][CRC_L][CRC_H]
        """
        # Build frame without CRC
        frame = struct.pack('>BBHH', 
                          self.slave_address, 
                          function_code,
                          start_address,  # High byte first
                          quantity)       # High byte first
        
        # Calculate and append CRC
        crc = self.calculate_crc16(frame)
        frame += struct.pack('<H', crc)  # Little-endian CRC
        
        description = f"Standard Read (Addr:{start_address}, Qty:{quantity})"
        return self.send_request(frame, description)
    
    def read_registers_nonstandard(self, start_address: int, quantity: int, function_code: int = 0x04, serial_number: str = None) -> Optional[bytes]:
        """
        Non-standard LUX format: 18 bytes total
        Format: [Address][Function][10-byte SN][Start_Addr_L][Start_Addr_H][Quantity_L][Quantity_H][CRC_L][CRC_H]
        """
        if serial_number is None:
            serial_number = self.inverter_serial
        
        # Build frame without CRC
        frame = struct.pack('BB', self.slave_address, function_code)
        
        # Add 10-byte serial number (or zeros for query)
        if serial_number == "0000000000":
            frame += b'\x00' * 10  # Query serial number
        else:
            frame += serial_number.encode('ascii')[:10].ljust(10, b'\x00')
        
        # Add address and quantity (little-endian for non-standard!)
        frame += struct.pack('<HH', start_address, quantity)  # Low byte first
        
        # Calculate and append CRC
        crc = self.calculate_crc16(frame)
        frame += struct.pack('<H', crc)  # Little-endian CRC
        
        sn_desc = "Query SN" if serial_number == "0000000000" else serial_number
        description = f"Non-standard Read (SN:{sn_desc}, Addr:{start_address}, Qty:{quantity})"
        return self.send_request(frame, description)
    
    def write_single_register_standard(self, address: int, value: int) -> Optional[bytes]:
        """Write single register - standard format"""
        frame = struct.pack('>BBHH', 
                          self.slave_address, 
                          0x06,
                          address,
                          value)
        
        crc = self.calculate_crc16(frame)
        frame += struct.pack('<H', crc)
        
        description = f"Standard Write Single (Addr:{address}, Value:{value})"
        return self.send_request(frame, description)
    
    def query_serial_number(self) -> Optional[str]:
        """Query inverter serial number using non-standard format"""
        print("\n🔍 Querying inverter serial number...")
        response = self.read_registers_nonstandard(0, 1, 0x04, "0000000000")
        
        if response and len(response) >= 13:
            # Try to extract serial number from response
            serial_data = response[3:13]
            try:
                serial_str = ''.join([chr(b) for b in serial_data if 32 <= b <= 126])
                if len(serial_str) == 10 and serial_str.isalnum():
                    print(f"✅ Inverter Serial Number: {serial_str}")
                    return serial_str
            except:
                pass
        
        print("❌ Could not determine serial number")
        return None


def main():
    """Main function with example usage"""
    print("🌟 LUX Modbus Client v1.0")
    print("=" * 50)
    
    # Configuration
    PROXY_IP = "10.0.0.51"
    PROXY_PORT = 502
    
    # Create client
    client = LuxModbusClient(PROXY_IP, PROXY_PORT)
    
    # You can set your inverter's serial number here
    # client.set_inverter_serial("1234567890")
    
    if not client.connect():
        return
    
    try:
        print("\n🧪 Testing LUX Modbus Communication")
        print("-" * 40)
        
        # Test 1: Query serial number (non-standard format)
        print("\n1️⃣ Querying Serial Number")
        serial = client.query_serial_number()
        if serial:
            client.set_inverter_serial(serial)
        
        time.sleep(2)
        
        # Test 2: Read input registers - standard format
        print("\n2️⃣ Reading Input Registers (Standard Format)")
        client.read_registers_standard(start_address=0, quantity=1, function_code=0x04)
        
        time.sleep(2)
        
        # Test 3: Read input registers - non-standard format
        print("\n3️⃣ Reading Input Registers (Non-standard Format)")
        client.read_registers_nonstandard(start_address=0, quantity=1, function_code=0x04)
        
        time.sleep(2)
        
        # Test 4: Read holding registers - standard format  
        print("\n4️⃣ Reading Holding Registers (Standard Format)")
        client.read_registers_standard(start_address=0, quantity=5, function_code=0x03)
        
        time.sleep(2)
        
        # Test 5: Read multiple registers - non-standard format
        print("\n5️⃣ Reading Multiple Registers (Non-standard Format)")
        client.read_registers_nonstandard(start_address=100, quantity=10, function_code=0x04)
        
        print("\n✅ Test sequence completed!")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()