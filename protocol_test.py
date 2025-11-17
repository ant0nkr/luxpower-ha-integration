#!/usr/bin/env python3
"""
Test to check what protocol the inverter at 10.0.0.51:502 expects.
"""

import asyncio
import sys

# Add the project path to import our modules
sys.path.insert(0, '/Users/akramskyi/git/luxpower-modbus-hacs/custom_components/lxp_modbus')

from classes.lxp_request_builder import LxpRequestBuilder
from classes.lxp_response import LxpResponse


async def test_protocol_discovery():
    """Test different protocols to see which one the inverter responds to."""
    host = "10.0.0.51"
    port = 502
    
    print("Protocol Discovery Test")
    print("=" * 40)
    print(f"Target: {host}:{port}")
    print()
    
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=10
        )
        print("✓ Connection established")
        
        # Test 1: Try LuxPower protocol
        print("\n--- Testing LuxPower Protocol ---")
        await test_lxp_protocol(reader, writer)
        
        # Test 2: Send raw data to see if we get any response
        print("\n--- Testing Raw Communication ---")
        await test_raw_communication(reader, writer)
        
        writer.close()
        await writer.wait_closed()
        print("\n✓ Connection closed")
        
    except Exception as e:
        print(f"✗ Connection error: {str(e)}")


async def test_lxp_protocol(reader, writer):
    """Test if the device responds to LuxPower protocol packets."""
    # Use dummy serial numbers that might work
    dongle_serial = "1234567890"
    inverter_serial = "0987654321"
    
    # Try to read register 7-8 (model information) using LXP protocol
    try:
        req = LxpRequestBuilder.prepare_packet_for_read(
            dongle_serial.encode(), inverter_serial.encode(), 7, 2, 3
        )
        
        print(f"LXP request packet: {req.hex()}")
        
        writer.write(req)
        await writer.drain()
        
        response_buf = await asyncio.wait_for(reader.read(512), timeout=3)
        
        if response_buf:
            print(f"✓ LXP response received: {response_buf.hex()}")
            
            # Try to parse with LXP response parser
            response = LxpResponse(response_buf)
            print(f"LXP response info: {response.info}")
            print(f"LXP packet error: {response.packet_error}")
            
            if not response.packet_error:
                print(f"✓ Valid LXP response! Parsed values: {response.parsed_values_dictionary}")
                return True
        else:
            print("✗ No LXP response")
            
    except asyncio.TimeoutError:
        print("✗ LXP response timeout")
    except Exception as e:
        print(f"✗ LXP error: {str(e)}")
    
    return False


async def test_raw_communication(reader, writer):
    """Send various test packets to see what the device responds to."""
    
    test_packets = [
        # Simple ping/hello
        b"\x00\x01\x02\x03",
        # Modbus TCP read holding registers (MBAP header + Modbus PDU)
        b"\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x01",
        # Simple Modbus RTU for comparison  
        b"\x01\x03\x00\x00\x00\x01\x84\x0A",
    ]
    
    for i, packet in enumerate(test_packets):
        print(f"Test packet {i+1}: {packet.hex()}")
        
        try:
            writer.write(packet)
            await writer.drain()
            
            response = await asyncio.wait_for(reader.read(512), timeout=2)
            if response:
                print(f"  ✓ Response: {response.hex()}")
            else:
                print(f"  ✗ No response")
                
        except asyncio.TimeoutError:
            print(f"  ✗ Timeout")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_protocol_discovery())