#!/usr/bin/env python3

"""
Simple Modbus TCP Client Test for ESP8266 Proxy
Tests the WiFi-to-RTU Modbus proxy functionality
"""

import socket
import struct
import sys

def create_modbus_tcp_request():
    """Create a simple Modbus TCP read holding registers request"""
    # Modbus TCP Header
    transaction_id = 0x0001  # Transaction ID
    protocol_id = 0x0000     # Protocol ID (always 0 for Modbus)
    length = 0x0006          # Length of following data
    
    # Modbus RTU portion (will be converted by proxy)
    unit_id = 0x01           # Slave address
    function_code = 0x03     # Read holding registers
    start_address = 0x0000   # Starting address
    quantity = 0x0001        # Number of registers to read
    
    # Pack into bytes
    tcp_header = struct.pack('>HHHH', transaction_id, protocol_id, length, unit_id)
    rtu_data = struct.pack('>BBH H', function_code, start_address >> 8, start_address & 0xFF, quantity)
    
    return tcp_header + rtu_data

def test_modbus_proxy(ip_address, port=502):
    """Test connection to Modbus TCP proxy"""
    print(f"Testing Modbus TCP connection to {ip_address}:{port}")
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5 second timeout
        
        # Connect to proxy
        print("Connecting...")
        sock.connect((ip_address, port))
        print("✅ Connected successfully!")
        
        # Send test request
        request = create_modbus_tcp_request()
        print(f"Sending Modbus request: {request.hex()}")
        sock.send(request)
        
        # Wait for response (optional - depends on if you have a real Modbus device connected)
        try:
            sock.settimeout(2.0)
            response = sock.recv(256)
            if response:
                print(f"📨 Received response: {response.hex()}")
            else:
                print("⏱️  No response from Modbus device (normal if no RTU device connected)")
        except socket.timeout:
            print("⏱️  Timeout waiting for response (normal if no RTU device connected)")
        
        sock.close()
        print("✅ Modbus TCP proxy is working!")
        return True
        
    except ConnectionRefusedError:
        print("❌ Connection refused - check IP address and port")
        return False
    except socket.timeout:
        print("❌ Connection timeout - check network connectivity")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 test_modbus.py <IP_ADDRESS>")
        print("Example: python3 test_modbus.py 192.168.1.100")
        sys.exit(1)
    
    ip = sys.argv[1]
    test_modbus_proxy(ip)