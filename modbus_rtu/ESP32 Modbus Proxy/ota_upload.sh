#!/bin/bash

# ESP8266 Modbus Proxy - OTA Upload Helper
# This script uploads firmware over-the-air to your ESP8266

echo "ESP8266 Modbus Proxy - OTA Upload Helper"
echo "========================================"

# Function to display usage
usage() {
    echo "Usage: $0 [device_ip]"
    echo "  device_ip: IP address of your ESP8266 (required)"
    echo ""
    echo "Examples:"
    echo "  $0 192.168.1.100      # Upload to specific IP"
    echo "  $0 10.0.0.51          # Upload to your device"
    exit 1
}

# Check if help was requested
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
fi

DEVICE_IP="$1"

# Require IP address
if [ -z "$DEVICE_IP" ]; then
    echo "❌ Device IP address is required"
    usage
fi

echo "Target device: $DEVICE_IP"

# Verify device is reachable
echo "Verifying device connectivity..."
if ! ping -c 1 -W 3000 "$DEVICE_IP" > /dev/null 2>&1; then
    echo "❌ Cannot ping device at $DEVICE_IP"
    echo "   Make sure the device is powered on and connected to WiFi"
    exit 1
fi

# Check if it's our device by checking the web interface
if curl -s --connect-timeout 5 "http://$DEVICE_IP/" | grep -q "Modbus.*Proxy" 2>/dev/null; then
    echo "✅ Device confirmed as ESP8266 Modbus Proxy"
else
    echo "⚠️  Device at $DEVICE_IP may not be the Modbus Proxy (continuing anyway)"
fi

# Build firmware first
echo ""
echo "Building firmware..."
if ! ~/.platformio/penv/bin/pio run -e d1_mini; then
    echo "❌ Build failed"
    exit 1
fi

echo "✅ Build successful"

# Upload via OTA using the dedicated environment
echo ""
echo "Uploading firmware over-the-air..."
echo "📡 Target: $DEVICE_IP:8266"

# Method 1: Try using the OTA environment with IP override
echo "Attempting OTA upload method 1..."
if ~/.platformio/penv/bin/pio run -e d1_mini_ota --target upload --upload-port "$DEVICE_IP"; then
    echo ""
    echo "✅ OTA upload successful!"
    echo "🔄 Device is rebooting with new firmware..."
    sleep 3
    echo ""
    echo "💡 Access your device at: http://$DEVICE_IP/"
    exit 0
fi

# Method 2: Try using espota.py directly
echo ""
echo "Method 1 failed, trying direct espota.py..."
FIRMWARE_PATH=".pio/build/d1_mini/firmware.bin"

if [ -f "$FIRMWARE_PATH" ]; then
    # Find espota.py
    ESPOTA_PATH=$(find ~/.platformio -name "espota.py" 2>/dev/null | head -1)
    if [ ! -z "$ESPOTA_PATH" ]; then
        echo "Using espota.py at: $ESPOTA_PATH"
        if python3 "$ESPOTA_PATH" -i "$DEVICE_IP" -p 8266 -f "$FIRMWARE_PATH"; then
            echo ""
            echo "✅ OTA upload successful!"
            echo "🔄 Device is rebooting with new firmware..."
            echo ""
            echo "💡 Access your device at: http://$DEVICE_IP/"
            exit 0
        fi
    else
        echo "❌ Could not find espota.py"
    fi
else
    echo "❌ Firmware file not found: $FIRMWARE_PATH"
fi

echo ""
echo "❌ All OTA upload methods failed"
echo "   Possible reasons:"
echo "   - Device is not running ArduinoOTA"
echo "   - OTA is disabled or password protected"
echo "   - Network connectivity issues"
echo "   - Device is busy or unresponsive"
echo ""
echo "💡 Fallback options:"
echo "   1. Upload via USB cable: ./build.sh upload"
echo "   2. Check device web interface: http://$DEVICE_IP/"
echo "   3. Power cycle the device and try again"
exit 1