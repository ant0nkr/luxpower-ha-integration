#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration
// IMPORTANT: Update these with your WiFi credentials!
#define WIFI_SSID "smart_devices"
#define WIFI_PASSWORD "j5qknFyPKzNfsUmAXhEYdv"

// Network Settings
#define MODBUS_TCP_PORT 502
#define MAX_CLIENTS 4

// Serial Settings
#define SERIAL_BAUD_RATE 19200  // Modbus RTU baud rate (updated to match device spec)
#define DEBUG_BAUD_RATE 115200 // Debug output baud rate

// Pin Definitions for D1 Mini ESP8266 with TTL-to-RS485 converter
//#define RS485_RX_PIN 12      // GPIO12 (D6)
//#define RS485_TX_PIN 14      // GPIO14 (D5)
#define LED_PIN LED_BUILTIN

// Timing Settings
#define MODBUS_TIMEOUT_MS 2      // Inter-frame timeout (1.75ms for 19200 bps, rounded up)
#define WIFI_CHECK_INTERVAL_MS 10000  // WiFi status check interval
#define BUFFER_SIZE 256          // Maximum frame size

// Remote Logging Configuration
#define WEB_SERVER_PORT 80       // Web server port for remote logs
#define MAX_LOG_SIZE 2000        // Maximum log buffer size
#define LOG_AUTO_REFRESH 5       // Web page auto-refresh interval in seconds

// OTA Update Configuration
#define OTA_HOSTNAME "ESP8266-Modbus-Proxy"  // OTA hostname
#define OTA_PORT 8266                        // OTA port (default)
// #define OTA_PASSWORD "your-ota-password"  // Uncomment and set password for security

// Hardware Configuration
// TTL-to-RS485 converter connection:
// GPIO3 (RX) - Connect to RS485 converter TX
// GPIO1 (TX) - Connect to RS485 converter RX
// The converter handles DE/RE switching automatically
// Using hardware UART pins for better performance

#endif