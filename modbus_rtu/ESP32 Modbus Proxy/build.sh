#!/bin/bash

# ESP8266 Modbus Proxy Build and Upload Script

# Set PlatformIO path
PLATFORMIO_PATH="$HOME/.platformio/penv/bin/platformio"

# Project directory
PROJECT_DIR="$(dirname "$0")"

echo "ESP8266 Modbus Proxy - PlatformIO Helper"
echo "========================================"

case "$1" in
    build)
        echo "Building project..."
        cd "$PROJECT_DIR" && "$PLATFORMIO_PATH" run
        ;;
    upload)
        echo "Building and uploading to ESP8266..."
        cd "$PROJECT_DIR" && "$PLATFORMIO_PATH" run --target upload
        ;;
    monitor)
        echo "Opening serial monitor..."
        cd "$PROJECT_DIR" && "$PLATFORMIO_PATH" device monitor
        ;;
    clean)
        echo "Cleaning project..."
        cd "$PROJECT_DIR" && "$PLATFORMIO_PATH" run --target clean
        ;;
    devices)
        echo "Available devices:"
        "$PLATFORMIO_PATH" device list
        ;;
    deploy|all)
        echo "Building, uploading, and monitoring ESP8266..."
        cd "$PROJECT_DIR" && "$PLATFORMIO_PATH" run --target upload && "$PLATFORMIO_PATH" device monitor
        ;;
    *)
        echo "Usage: $0 {build|upload|monitor|clean|devices|deploy}"
        echo ""
        echo "Commands:"
        echo "  build    - Build the project"
        echo "  upload   - Build and upload to ESP8266"
        echo "  monitor  - Open serial monitor"
        echo "  deploy   - Build, upload, and monitor (all-in-one)"
        echo "  clean    - Clean build files"
        echo "  devices  - List available serial devices"
        echo ""
        echo "Make sure to:"
        echo "1. Update WiFi credentials in include/config.h"
        echo "2. Connect your D1 Mini via USB"
        echo "3. Wire the RS485 module correctly"
        exit 1
        ;;
esac