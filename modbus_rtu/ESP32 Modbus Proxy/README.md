# WiFi-Enabled Modbus RTU/TCP Proxy for D1 Mini ESP8266

This project implements a WiFi-enabled Modbus proxy using a D1 Mini ESP8266 controller. The proxy can:
- Receive Modbus TCP requests via WiFi and forward them as Modbus RTU to connected devices
- Convert between Modbus TCP and RTU protocols transparently
- Support multiple simultaneous TCP client connections

## Features

- **WiFi Connectivity**: Connect to your local WiFi network
- **Modbus TCP Server**: Acts as a Modbus TCP server on port 502
- **Protocol Conversion**: Automatically converts between Modbus TCP and RTU
- **Multiple Clients**: Supports up to 4 simultaneous TCP connections
- **Transparent Proxy**: Forwards Modbus requests/responses with protocol conversion
- **Status Indication**: LED blinks indicate WiFi status and client connections
- **Hardware Serial**: Uses ESP8266 hardware UART for reliable RTU communication

## Hardware Requirements

- D1 Mini ESP8266 board
- RS485 to TTL converter module (e.g., MAX485, SN65HVD485)
- Modbus RTU device to communicate with

## Pin Connections

## Pin Connections

| D1 Mini Pin | GPIO | Function | Connect To |
|-------------|------|----------|------------|
| TX | GPIO1 | Modbus TX | RS485 module RX |
| RX | GPIO3 | Modbus RX | RS485 module TX |
| D7 | GPIO13 | DE/RE Control | RS485 module DE/RE |

**Note**: The D1 Mini uses GPIO1 (TX) and GPIO3 (RX) as the hardware UART pins for reliable serial communication.

## RS485 Module Connections

| RS485 Module Pin | Connect To |
|------------------|------------|
| VCC | D1 Mini 3.3V |
| GND | D1 Mini GND |
| A+ | Modbus Device A+ |
| B- | Modbus Device B- |

## Software Setup

### Prerequisites

1. Install [PlatformIO](https://platformio.org/install)
2. Install [VS Code with PlatformIO extension](https://platformio.org/install/ide?install=vscode) (recommended)

### Building and Uploading

1. Clone or download this project
2. Open the project in VS Code with PlatformIO
3. Connect your D1 Mini via USB
4. Build and upload:
   ```bash
   platformio run --target upload
   ```

### Configuration

### Configuration

1. **Update WiFi credentials** in `include/config.h`:
   ```cpp
   #define WIFI_SSID "Your_WiFi_Network"
   #define WIFI_PASSWORD "Your_WiFi_Password"
   ```

2. **Adjust Modbus settings** if needed in `include/config.h`:
   ```cpp
   #define SERIAL_BAUD_RATE 9600    // Match your Modbus device
   #define MODBUS_TCP_PORT 502      // Standard Modbus TCP port
   #define MAX_CLIENTS 4            // Maximum simultaneous connections
   ```

## Usage

### WiFi Setup
1. Configure your WiFi credentials in `include/config.h`
2. Upload the firmware to your D1 Mini
3. The device will attempt to connect to WiFi automatically
4. LED blink patterns indicate status:
   - Single blinks during connection attempt
   - 2 slow blinks = WiFi connected successfully
   - 5 fast blinks = WiFi connection lost
   - Continuous slow blinks = WiFi connection failed

### Modbus TCP Client Connection
Once connected to WiFi, you can connect Modbus TCP clients to the D1 Mini's IP address on port 502.

### Example with Python (pymodbus)

```python
from pymodbus.client.sync import ModbusTcpClient
import time

# Connect to the D1 Mini proxy (replace with actual IP)
client = ModbusTcpClient('192.168.1.100', port=502)

if client.connect():
    # Read holding registers
    result = client.read_holding_registers(0, 10, unit=1)
    if not result.isError():
        print(f"Register values: {result.registers}")
    
    # Write a register
    client.write_register(0, 123, unit=1)
    
    client.close()
else:
    print("Failed to connect to Modbus proxy")
```

## Troubleshooting

## Troubleshooting

### Common Issues

1. **WiFi connection fails**:
   - Check SSID and password in `include/config.h`
   - Ensure WiFi network is 2.4GHz (ESP8266 doesn't support 5GHz)
   - Check signal strength - move closer to router

2. **No response from Modbus device**:
   - Check wiring connections (TX/RX might be swapped)
   - Verify baud rate matches device settings
   - Ensure correct Modbus device address

3. **Compilation errors**:
   - Make sure PlatformIO is installed correctly
   - Check that the ESP8266 platform is installed: `platformio platform install espressif8266`
   - Verify all include files are present

4. **TCP clients can't connect**:
   - Check firewall settings
   - Verify the D1 Mini's IP address
   - Ensure port 502 is not blocked

### LED Status Indicators

| LED Pattern | Meaning |
|-------------|---------|
| LED on during boot | Connecting to WiFi |
| Single fast blinks | WiFi connection in progress |
| 2 slow blinks | WiFi connected successfully |
| 5 fast blinks | WiFi connection lost |
| Continuous slow blinks | WiFi connection failed |
| Single blink | New TCP client connected |

### Debug Information

The device doesn't output debug information via Serial (since Serial is used for Modbus RTU). To add debug output:

1. Use `Serial1` for debugging (GPIO2 = TX only)
2. Connect a USB-Serial adapter to GPIO2 for debug output
3. Uncomment the debug lines in `setupWiFi()` function

## Customization

### Removing Debug Output

To disable debug output and use the USB Serial purely for Modbus communication, comment out the debug print statements in `main.cpp`:

```cpp
// Comment out these lines to disable debug output
// Serial.print("TX: 0x");
// Serial.println(data, HEX);
```

### Different Pin Assignment

You can use different GPIO pins by modifying the pin definitions at the top of `main.cpp`. Make sure to avoid pins used by the ESP8266's internal functions.

## License

This project is open source and available under the MIT License.