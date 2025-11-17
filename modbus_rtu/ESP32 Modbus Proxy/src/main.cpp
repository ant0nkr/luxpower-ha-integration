#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WiFiServer.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include <ArduinoOTA.h>
#include <time.h>
//#include <SoftwareSerial.h>
#include "config.h"

// WiFi credentials
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// NTP Configuration
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0; // UTC offset in seconds (0 for UTC)
const int daylightOffset_sec = 0; // Daylight saving offset
bool timeInitialized = false;

// Web server for remote logging
ESP8266WebServer webServer(WEB_SERVER_PORT);
String webLog = "";
unsigned long bootTime = 0;

// Server for Modbus TCP connections
WiFiServer server(MODBUS_TCP_PORT);

// Use SoftwareSerial for Modbus RTU with TTL-to-RS485 converter
//SoftwareSerial modbusSerial(RS485_RX_PIN, RS485_TX_PIN);

// Client management
WiFiClient clients[MAX_CLIENTS];
bool wifiConnected = false;
unsigned long lastWiFiCheck = 0;

// Buffer for storing incoming data
uint8_t buffer[BUFFER_SIZE];
int bufferIndex = 0;

// Timing variables
unsigned long lastByteTime = 0;
bool frameInProgress = false;
unsigned long frameStartTime = 0;
const unsigned long MAX_FRAME_TIME = 500; // Increased for LUX inverter

// Continuous listening variables
bool waitingForTcpResponse = false;
unsigned long lastTcpRequestTime = 0;
unsigned long messageCounter = 0;

// Function prototypes
void setupOTA();
void setupWiFi();
void setupNTP();
String getCurrentTimestamp();
void handleWiFiClients();
void handleModbusRTU();
void processRTUResponse();
void blinkLED(int times, int delayMs = 100);
void addToLog(String message);
void setupWebServer();
void handleRoot();
void handleClear();
void handleStatus();
String bytesToHex(uint8_t* data, int length);
String decodeLuxModbusRequest(uint8_t* data, int length);
String decodeLuxModbusResponse(uint8_t* data, int length);

String bytesToHex(uint8_t* data, int length) {
  String hex = "";
  for (int i = 0; i < length; i++) {
    if (data[i] < 16) hex += "0";
    hex += String(data[i], HEX);
    if (i < length - 1) hex += " ";
  }
  hex.toUpperCase();
  return hex;
}

String decodeLuxModbusRequest(uint8_t* data, int length) {
  if (length < 6) return "❌ Frame too short for Modbus";
  
  uint8_t address = data[0];
  uint8_t functionCode = data[1];
  String result = "📋 LUX Modbus Request Analysis:\n";
  result += "   Address: " + String(address) + " (0x" + String(address, HEX) + ")\n";
  result += "   Function: 0x" + String(functionCode, HEX);
  
  // Decode function codes
  switch (functionCode) {
    case 0x03: result += " (Read Holding Registers)\n"; break;
    case 0x04: result += " (Read Input Registers)\n"; break;
    case 0x06: result += " (Write Single Register)\n"; break;
    case 0x10: result += " (Write Multiple Registers)\n"; break;
    default: result += " (Unknown Function)\n"; break;
  }
  
  // Detect LUX format type
  if (length == 8) {
    // Standard format: 01 04 00 00 00 01 31 CA
    result += "   Format: ✅ STANDARD LUX Format (8 bytes)\n";
    
    if (functionCode == 0x03 || functionCode == 0x04) {
      uint16_t startAddr = (data[2] << 8) | data[3]; // High byte first
      uint16_t quantity = (data[4] << 8) | data[5];  // High byte first
      result += "   Start Address: " + String(startAddr) + " (0x" + String(startAddr, HEX) + ")\n";
      result += "   Quantity: " + String(quantity) + " registers\n";
    }
  } 
  else if (length == 18) {
    // Non-standard format: 01 04 [10-byte SN] [addr] [qty] [CRC]
    result += "   Format: ✅ NON-STANDARD LUX Format (18 bytes)\n";
    
    // Extract serial number (bytes 2-11)
    String serialHex = "";
    bool allZeros = true;
    for (int i = 2; i < 12; i++) {
      if (data[i] < 16) serialHex += "0";
      serialHex += String(data[i], HEX);
      if (i < 11) serialHex += " ";
      if (data[i] != 0) allZeros = false;
    }
    
    if (allZeros) {
      result += "   Serial Number: 00 00 00 00 00 00 00 00 00 00 (Query SN)\n";
    } else {
      result += "   Serial Number: " + serialHex + "\n";
    }
    
    if (functionCode == 0x03 || functionCode == 0x04) {
      uint16_t startAddr = data[12] | (data[13] << 8); // Low byte first in non-standard!
      uint16_t quantity = data[14] | (data[15] << 8);  // Low byte first in non-standard!
      result += "   Start Address: " + String(startAddr) + " (0x" + String(startAddr, HEX) + ")\n";
      result += "   Quantity: " + String(quantity) + " registers\n";
    }
  }
  else {
    result += "   Format: ⚠️ Unknown LUX Format (" + String(length) + " bytes)\n";
    result += "   Expected: 8 bytes (standard) or 18 bytes (non-standard)\n";
  }
  
  // CRC information
  if (length >= 2) {
    uint16_t crc = data[length-2] | (data[length-1] << 8);
    result += "   CRC: 0x" + String(crc, HEX) + " (bytes " + String(length-2) + "-" + String(length-1) + ")";
  }
  
  return result;
}

String decodeLuxModbusResponse(uint8_t* data, int length) {
  if (length < 3) return "❌ Response too short";
  
  uint8_t address = data[0];
  uint8_t functionCode = data[1];
  String result = "📤 LUX Modbus Response Analysis:\n";
  result += "   Address: " + String(address) + " (0x" + String(address, HEX) + ")\n";
  result += "   Function: 0x" + String(functionCode, HEX);
  
  // Check for error response
  if (functionCode & 0x80) {
    result += " (ERROR RESPONSE)\n";
    if (length >= 3) {
      uint8_t errorCode = data[2];
      result += "   Error Code: 0x" + String(errorCode, HEX);
      switch (errorCode) {
        case 0x01: result += " (Illegal Function)"; break;
        case 0x02: result += " (Illegal Data Address)"; break;
        case 0x03: result += " (Illegal Data Value)"; break;
        case 0x04: result += " (Server Device Failure)"; break;
        default: result += " (Unknown Error)"; break;
      }
    }
    return result;
  }
  
  // Normal response
  switch (functionCode) {
    case 0x03:
    case 0x04:
      result += " (Read Registers Response)\n";
      if (length >= 3) {
        uint8_t byteCount = data[2];
        result += "   Data Length: " + String(byteCount) + " bytes\n";
        
        // Check if this looks like LUX non-standard response
        if (length >= 13 && byteCount >= 10) {
          // Check if first 10 bytes could be serial number
          String serialNumber = "";
          bool couldBeSN = true;
          for (int i = 3; i < 13; i++) {
            if (data[i] >= 0x30 && data[i] <= 0x39) { // ASCII digits
              serialNumber += char(data[i]);
            } else if (data[i] >= 0x41 && data[i] <= 0x46) { // ASCII A-F
              serialNumber += char(data[i]);
            } else if (data[i] >= 0x61 && data[i] <= 0x66) { // ASCII a-f  
              serialNumber += char(data[i]);
            } else {
              couldBeSN = false;
              break;
            }
          }
          
          if (couldBeSN && serialNumber.length() == 10) {
            result += "   Serial Number: " + serialNumber + " (ASCII)\n";
            result += "   Format: ✅ NON-STANDARD LUX Response\n";
            
            if (length >= 15) {
              uint16_t regAddr = data[13] | (data[14] << 8);
              result += "   Register Address: " + String(regAddr) + "\n";
            }
            if (length >= 17) {
              uint16_t dataLen = data[15] | (data[16] << 8);
              result += "   Data Count: " + String(dataLen) + " registers\n";
            }
          } else {
            result += "   Format: ✅ STANDARD LUX Response\n";
          }
        } else {
          result += "   Format: ✅ STANDARD LUX Response\n";
        }
        
        // Show register data
        if (length > 3 + byteCount) {
          result += "   Register Data: ";
          for (int i = 3; i < 3 + byteCount; i += 2) {
            if (i + 1 < 3 + byteCount) {
              uint16_t regValue = (data[i] << 8) | data[i + 1];
              result += String(regValue) + " ";
            }
          }
          result += "\n";
        }
      }
      break;
      
    case 0x06:
      result += " (Write Single Register Response)\n";
      break;
      
    case 0x10:
      result += " (Write Multiple Registers Response)\n";
      break;
      
    default:
      result += " (Unknown Response)\n";
      break;
  }
  
  // CRC information
  if (length >= 2) {
    uint16_t crc = data[length-2] | (data[length-1] << 8);
    result += "   CRC: 0x" + String(crc, HEX);
  }
  
  return result;
}

void handleWiFiClients() {
  // Accept new clients
  WiFiClient newClient = server.accept();
  if (newClient) {
    for (int i = 0; i < MAX_CLIENTS; i++) {
      if (!clients[i] || !clients[i].connected()) {
        if (clients[i]) {
          clients[i].stop();
        }
        clients[i] = newClient;
        // Set minimal timeout for immediate response
        clients[i].setTimeout(10); // 10ms timeout instead of default 1000ms
        addToLog("🔗 Client connected: " + newClient.remoteIP().toString() + ":" + String(newClient.remotePort()));
        break;
      }
    }
  }
  
  // Handle existing clients - process immediately when data arrives
  for (int i = 0; i < MAX_CLIENTS; i++) {
    if (clients[i] && clients[i].connected()) {
      if (clients[i].available()) {
        // Read data immediately as it arrives
        uint8_t tcpBuffer[BUFFER_SIZE];
        int bytesAvailable = clients[i].available();
        int bytesToRead = min(bytesAvailable, (int)BUFFER_SIZE);
        int bytesRead = clients[i].readBytes(tcpBuffer, bytesToRead);
        
        if (bytesRead > 0) {
          String hexData = bytesToHex(tcpBuffer, bytesRead);
          addToLog("📥 TCP Request from " + clients[i].remoteIP().toString() + ":" + String(clients[i].remotePort()));
          addToLog("   Length: " + String(bytesRead) + " bytes (available: " + String(bytesAvailable) + ")");
          addToLog("   HEX: " + hexData);
          addToLog(decodeLuxModbusRequest(tcpBuffer, bytesRead));
          
          // Forward data immediately to RTU via hardware Serial
          addToLog("📡 Transmitting to LUX inverter via RS485...");
          unsigned long transmitStart = millis();
          Serial.write(tcpBuffer, bytesRead);
          Serial.flush();
          unsigned long transmitEnd = millis();
          addToLog("✅ Transmitted to RS485 (" + String(transmitEnd - transmitStart) + "ms)");
          
          // Set frame tracking for response
          frameInProgress = true;
          frameStartTime = millis();
          bufferIndex = 0;
          waitingForTcpResponse = true;
          lastTcpRequestTime = millis();
          addToLog("⏳ Waiting for LUX inverter response...");
        }
      }
    } else if (clients[i]) {
      String clientInfo = clients[i].remoteIP().toString() + ":" + String(clients[i].remotePort());
      addToLog("🔌 Client " + clientInfo + " disconnected");
      clients[i].stop();
      clients[i] = WiFiClient();
    }
  }
}

void handleModbusRTU() {
  // Continuously monitor incoming RTU responses (TTL-to-RS485 converter receives only)
  while (Serial.available()) {

    addToLog("🔄 Receiving byte from RS485...");

    uint8_t receivedByte = Serial.read();
    
    if (bufferIndex < BUFFER_SIZE) {
      buffer[bufferIndex++] = receivedByte;
      lastByteTime = millis();
      
      if (!frameInProgress) {
        frameInProgress = true;
        frameStartTime = millis();
        messageCounter++;
        
        // Determine message type based on context
        if (waitingForTcpResponse && (millis() - lastTcpRequestTime) < 5000) {
          addToLog("📞 RTU Response to TCP request (Msg #" + String(messageCounter) + ")");
        } else {
          addToLog("💓 RTU Heartbeat/Status message detected (Msg #" + String(messageCounter) + ")");
        }
      }
    }
  }
  
  // Process complete frames
  if (frameInProgress && bufferIndex > 0) {
    unsigned long timeSinceLastByte = millis() - lastByteTime;
    unsigned long totalFrameTime = millis() - frameStartTime;
    
    if (timeSinceLastByte >= MODBUS_TIMEOUT_MS || totalFrameTime >= MAX_FRAME_TIME) {
      processRTUResponse();
    }
  }
  
  // Check for timeout only when waiting for TCP response
  if (waitingForTcpResponse && frameInProgress && millis() - frameStartTime > MAX_FRAME_TIME && bufferIndex == 0) {
    addToLog("⚠️ TIMEOUT: No RTU response to TCP request after " + String(MAX_FRAME_TIME) + "ms");
    addToLog("   Note: TTL-RS485 converter only receives RTU responses");
    addToLog("   Check if inverter received the TCP request properly");
    frameInProgress = false;
    bufferIndex = 0;
    waitingForTcpResponse = false;
  }
}

void processRTUResponse() {
  if (bufferIndex > 0) {
    String hexResponse = bytesToHex(buffer, bufferIndex);
    
    // Determine message type and handle accordingly
    bool isHeartbeat = !waitingForTcpResponse || (millis() - lastTcpRequestTime) > 5000;
    
    if (isHeartbeat) {
      // This is a heartbeat/status message from the inverter
      addToLog("💓 RTU Heartbeat/Status Message (Msg #" + String(messageCounter) + "):");
      addToLog("   Length: " + String(bufferIndex) + " bytes");
      addToLog("   HEX: " + hexResponse);
      addToLog("   Source: RS485 bus → TTL converter → ESP8266");
      addToLog(decodeLuxModbusResponse(buffer, bufferIndex));
      
      // Optionally forward heartbeat to interested TCP clients
      int clientsSent = 0;
      for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i] && clients[i].connected()) {
          clients[i].write(buffer, bufferIndex);
          clientsSent++;
        }
      }
      
      if (clientsSent > 0) {
        addToLog("📡 Heartbeat forwarded to " + String(clientsSent) + " TCP client(s)");
      }
      
    } else {
      // This is a response to a TCP request
      addToLog("📤 RTU Response to TCP Request (Msg #" + String(messageCounter) + "):");
      addToLog("   Length: " + String(bufferIndex) + " bytes");
      addToLog("   HEX: " + hexResponse);
      addToLog("   Response time: " + String(millis() - lastTcpRequestTime) + "ms");
      addToLog("   Path: RS485 → TTL converter → ESP8266 → TCP");
      addToLog(decodeLuxModbusResponse(buffer, bufferIndex));
      
      // Forward response immediately to all connected TCP clients
      int clientsSent = 0;
      int clientsActual = 0;
      unsigned long forwardStart = millis();
      
      for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i] && clients[i].connected()) {
          size_t bytesWritten = clients[i].write(buffer, bufferIndex);
          clients[i].flush(); // Ensure data is actually sent immediately
          
          if (bytesWritten == (size_t)bufferIndex) {
            clientsSent++;
            addToLog("   ✅ Client " + String(i) + " (" + clients[i].remoteIP().toString() + "): " + String(bytesWritten) + " bytes sent");
          } else {
            addToLog("   ⚠️ Client " + String(i) + " (" + clients[i].remoteIP().toString() + "): Only " + String(bytesWritten) + "/" + String(bufferIndex) + " bytes sent");
          }
          clientsActual++;
        }
      }
      
      unsigned long forwardEnd = millis();
      
      if (clientsSent > 0) {
        addToLog("✅ TCP Response successfully sent to " + String(clientsSent) + "/" + String(clientsActual) + " client(s) (" + String(forwardEnd - forwardStart) + "ms)");
      } else if (clientsActual > 0) {
        addToLog("❌ Failed to send to all " + String(clientsActual) + " connected client(s)");
      } else {
        addToLog("⚠️ No TCP clients to forward response");
      }
      
      // Clear TCP response waiting flag
      waitingForTcpResponse = false;
    }
  }
  
  // Reset frame tracking
  frameInProgress = false;
  bufferIndex = 0;
}

void addToLog(String message) {
  String timestamp = getCurrentTimestamp();
  String logEntry = timestamp + ": " + message + "\n";
  
  // Add to web log buffer
  webLog += logEntry;
  
  // Keep buffer size manageable
  if (webLog.length() > MAX_LOG_SIZE) {
    int firstNewline = webLog.indexOf('\n');
    if (firstNewline > 0) {
      webLog = webLog.substring(firstNewline + 1);
    }
  }
}

void blinkLED(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, LOW);
    delay(delayMs);
    digitalWrite(LED_PIN, HIGH);
    delay(delayMs);
  }
}


void handleRoot() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<meta charset='UTF-8'>";
  html += "<title>LUX Modbus RTU/TCP Proxy</title>";
  // Remove the meta refresh tag - we'll handle refresh with JavaScript only
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body { font-family: 'Courier New', monospace; background: #000; color: #0f0; padding: 10px; margin: 0; }";
  html += "h1 { color: #ff0; text-align: center; }";
  html += "h2 { color: #0ff; border-bottom: 1px solid #0ff; padding-bottom: 5px; }";
  html += ".status { background: #111; padding: 10px; margin: 10px 0; border-left: 3px solid #0f0; }";
  html += ".logs { background: #111; padding: 10px; max-height: 400px; overflow-y: scroll; border: 1px solid #333; }";
  html += "pre { white-space: pre-wrap; word-wrap: break-word; margin: 0; }";
  html += ".button { background: #0f0; color: #000; padding: 8px 16px; text-decoration: none; margin: 5px; display: inline-block; cursor: pointer; border: none; font-family: inherit; }";
  html += ".button:hover { background: #0c0; }";
  html += ".button.disabled { background: #666; color: #999; }";
  html += ".button.refresh-off { background: #f80; color: #000; }";
  html += ".controls { margin: 10px 0; }";
  html += ".countdown { margin-left: 15px; color: #888; }";
  html += ".countdown.paused { color: #f80; }";
  html += "</style>";
  
  // JavaScript for refresh control
  html += "<script>";
  html += "var autoRefresh = true;";
  html += "var refreshInterval;";
  html += "var countdownInterval;";
  html += "var countdown = 5;";
  
  html += "function toggleRefresh() {";
  html += "  var button = document.getElementById('refresh-toggle');";
  html += "  var countdownSpan = document.getElementById('countdown-container');";
  html += "  if (autoRefresh) {";
  html += "    autoRefresh = false;";
  html += "    button.textContent = 'Enable Auto-Refresh';";
  html += "    button.className = 'button refresh-off';";
  html += "    countdownSpan.className = 'countdown paused';";
  html += "    clearInterval(refreshInterval);";
  html += "    clearInterval(countdownInterval);";
  html += "    document.getElementById('countdown').textContent = 'PAUSED';";
  html += "  } else {";
  html += "    autoRefresh = true;";
  html += "    button.textContent = 'Disable Auto-Refresh';";
  html += "    button.className = 'button';";
  html += "    countdownSpan.className = 'countdown';";
  html += "    startRefreshCountdown();";
  html += "  }";
  html += "}";
  
  html += "function manualRefresh() {";
  html += "  window.location.reload();";
  html += "}";
  
  html += "function startRefreshCountdown() {";
  html += "  countdown = 5;";
  html += "  document.getElementById('countdown').textContent = countdown;";
  html += "  ";
  html += "  refreshInterval = setTimeout(function() {";
  html += "    if (autoRefresh) {";
  html += "      window.location.reload();";
  html += "    }";
  html += "  }, 5000);";
  html += "  ";
  html += "  countdownInterval = setInterval(function() {";
  html += "    if (autoRefresh) {";
  html += "      countdown--;";
  html += "      document.getElementById('countdown').textContent = countdown;";
  html += "      if (countdown <= 0) {";
  html += "        clearInterval(countdownInterval);";
  html += "      }";
  html += "    }";
  html += "  }, 1000);";
  html += "}";
  
  html += "window.onload = function() {";
  html += "  startRefreshCountdown();";
  html += "};";
  
  html += "window.onbeforeunload = function() {";
  html += "  clearInterval(refreshInterval);";
  html += "  clearInterval(countdownInterval);";
  html += "};";
  
  html += "</script>";
  
  html += "</head><body>";
  
  html += "<h1>LUX Modbus RTU/TCP Proxy</h1>";
  
  html += "<div class='status'>";
  html += "<h2>System Status</h2>";
  html += "<p><strong>WiFi:</strong> " + String(WiFi.SSID()) + " (IP: " + WiFi.localIP().toString() + ", RSSI: " + String(WiFi.RSSI()) + " dBm)</p>";
  html += "<p><strong>Modbus TCP Port:</strong> " + String(MODBUS_TCP_PORT) + "</p>";
  html += "<p><strong>RS485 Baud Rate:</strong> " + String(SERIAL_BAUD_RATE) + " bps (19200 for LUX inverters)</p>";
  html += "<p><strong>Uptime:</strong> " + String(millis() / 1000) + " seconds</p>";
  html += "<p><strong>Free Memory:</strong> " + String(ESP.getFreeHeap()) + " bytes</p>";
  html += "<p><strong>Protocol:</strong> LUX Modbus RTU (Standard & Non-standard formats)</p>";
  html += "</div>";
  
  html += "<div class='status'>";
  html += "<h2>Connection Info</h2>";
  html += "<p><strong>TCP Clients:</strong> ";
  int activeClients = 0;
  for (int i = 0; i < MAX_CLIENTS; i++) {
    if (clients[i] && clients[i].connected()) {
      if (activeClients > 0) html += ", ";
      html += clients[i].remoteIP().toString();
      activeClients++;
    }
  }
  if (activeClients == 0) html += "None";
  html += " (" + String(activeClients) + "/" + String(MAX_CLIENTS) + ")</p>";
  html += "<p><strong>Messages Received:</strong> " + String(messageCounter) + " total</p>";
  html += "<p><strong>Monitoring Mode:</strong> RTU Response Listener (TTL→RS485 converter)</p>";
  html += "<p><strong>Data Flow:</strong> RS485 Bus → TTL Converter → ESP8266 → TCP Clients</p>";
  html += "</div>";
  
  html += "<div class='controls'>";
  html += "<button id='refresh-toggle' class='button' onclick='toggleRefresh()'>Disable Auto-Refresh</button>";
  html += "<button class='button' onclick='manualRefresh()'>Manual Refresh</button>";
  html += "<a href='/clear' class='button'>Clear Logs</a>";
  html += "<a href='/status' class='button'>JSON Status</a>";
  html += "<span id='countdown-container' class='countdown'>Next refresh in: <span id='countdown'>5</span>s</span>";
  html += "</div>";
  
  html += "<div class='logs'>";
  html += "<h2>Live Communication Logs</h2>";
  html += "<pre>" + webLog + "</pre>";
  html += "</div>";
  
  html += "</body></html>";
  
  webServer.send(200, "text/html; charset=UTF-8", html);
}
void handleClear() {
  webLog = "";
  addToLog("🧹 Log buffer cleared via web interface");
  webServer.send(200, "text/plain", "Logs cleared successfully");
}

void handleStatus() {
  String json = "{";
  json += "\"wifi_ssid\":\"" + String(WiFi.SSID()) + "\",";
  json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
  json += "\"rssi\":" + String(WiFi.RSSI()) + ",";
  json += "\"uptime\":" + String(millis() / 1000) + ",";
  json += "\"free_heap\":" + String(ESP.getFreeHeap()) + ",";
  json += "\"modbus_port\":" + String(MODBUS_TCP_PORT) + ",";
  json += "\"rs485_baud\":" + String(SERIAL_BAUD_RATE) + ",";
  json += "\"active_clients\":" + String(0) + ","; // Count active clients
  json += "\"protocol\":\"LUX Modbus RTU\"";
  json += "}";
  
  webServer.send(200, "application/json", json);
}

void setupWebServer() {
  webServer.on("/", handleRoot);
  webServer.on("/clear", handleClear);
  webServer.on("/status", handleStatus);
  webServer.begin();
  addToLog("🌐 Web server started: http://" + WiFi.localIP().toString());
}

void setupOTA() {
  ArduinoOTA.setHostname(OTA_HOSTNAME);
  ArduinoOTA.setPort(8266);
  
  ArduinoOTA.onStart([]() {
    String type;
    if (ArduinoOTA.getCommand() == U_FLASH) {
      type = "sketch";
    } else {
      type = "filesystem";
    }
    addToLog("🔄 OTA Update started: " + type);
    server.stop(); // Stop Modbus server during OTA
  });
  
  ArduinoOTA.onEnd([]() {
    addToLog("✅ OTA Update completed successfully");
    blinkLED(5, 50);
  });
  
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    static unsigned long lastLog = 0;
    if (millis() - lastLog > 1000) {
      addToLog("📊 OTA Progress: " + String(progress / (total / 100)) + "%");
      lastLog = millis();
      blinkLED(1, 50);
    }
  });
  
  ArduinoOTA.onError([](ota_error_t error) {
    String errorMsg = "❌ OTA Error: ";
    if (error == OTA_AUTH_ERROR) errorMsg += "Auth Failed";
    else if (error == OTA_BEGIN_ERROR) errorMsg += "Begin Failed";
    else if (error == OTA_CONNECT_ERROR) errorMsg += "Connect Failed";
    else if (error == OTA_RECEIVE_ERROR) errorMsg += "Receive Failed";
    else if (error == OTA_END_ERROR) errorMsg += "End Failed";
    addToLog(errorMsg);
    blinkLED(10, 100);
  });
  
  ArduinoOTA.begin();
  addToLog("🔄 OTA ready: " + String(OTA_HOSTNAME));
}

void setupWiFi() {
  addToLog("🔄 Starting WiFi connection...");
  addToLog("⚙️ LED will blink during connection");
  
  // 5-second startup delay with LED blinking
  for (int i = 0; i < 50; i++) {
    blinkLED(1, 50);
    delay(50);
  }
  
  WiFi.mode(WIFI_STA);
  addToLog("📡 WiFi mode set to station");
  
  WiFi.begin(ssid, password);
  addToLog("🔗 Connecting to: " + String(ssid));
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 60) {
    delay(1000);
    attempts++;
    blinkLED(1, 100);
    
    if (attempts % 5 == 0) {
      addToLog("🔄 Connection attempt " + String(attempts) + "/60...");
    }
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    addToLog("✅ WiFi connected successfully!");
    addToLog("📍 IP Address: " + WiFi.localIP().toString());
    addToLog("📍 Gateway: " + WiFi.gatewayIP().toString());
    addToLog("📍 DNS: " + WiFi.dnsIP().toString());
    addToLog("📶 Signal Strength: " + String(WiFi.RSSI()) + " dBm");
    
    // Initialize NTP time synchronization
    setupNTP();
    
    blinkLED(2, 200);
  } else {
    addToLog("❌ WiFi connection failed!");
    blinkLED(5, 100);
  }
}

void setupNTP() {
  addToLog("🕐 Configuring NTP time synchronization...");
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  
  // Wait for time to be set
  int attempts = 0;
  while (!time(nullptr) && attempts < 30) {
    delay(1000);
    attempts++;
    if (attempts % 5 == 0) {
      addToLog("⏳ Waiting for NTP sync... (" + String(attempts) + "/30)");
    }
  }
  
  if (time(nullptr)) {
    timeInitialized = true;
    addToLog("✅ NTP time synchronized successfully");
    addToLog("📅 Current UTC time: " + getCurrentTimestamp());
  } else {
    addToLog("❌ Failed to synchronize NTP time, using relative timestamps");
    timeInitialized = false;
  }
}

String getCurrentTimestamp() {
  if (!timeInitialized || !time(nullptr)) {
    // Fallback to relative time
    unsigned long currentTime = millis();
    return String(currentTime / 1000) + "." + String((currentTime % 1000) / 10, 2) + "s";
  }
  
  time_t now = time(nullptr);
  struct tm* utcTime = gmtime(&now);
  
  char timeStr[25];
  snprintf(timeStr, sizeof(timeStr), "%04d-%02d-%02d %02d:%02d:%02d UTC",
           utcTime->tm_year + 1900,
           utcTime->tm_mon + 1,
           utcTime->tm_mday,
           utcTime->tm_hour,
           utcTime->tm_min,
           utcTime->tm_sec);
  
  return String(timeStr);
}

void setup() {
  bootTime = millis();
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  
  // Initialize SoftwareSerial for RS485 communication
  Serial.begin(SERIAL_BAUD_RATE);
  //Serial.swap();

  addToLog("🚀 LUX Modbus RTU Monitor/TCP Proxy Starting...");
  addToLog("⚙️ Hardware: ESP8266 D1 Mini");
  //addToLog("⚙️ RS485 Connection: RX=" + String(RS485_RX_PIN) + " (TTL-to-RS485 converter)");
  addToLog("⚙️ Mode: RTU Response Monitor + TCP-to-RTU Proxy");
  addToLog("⚙️ Baud Rate: " + String(SERIAL_BAUD_RATE) + " bps (LUX Standard)");
  addToLog("⚙️ Protocol: LUX Modbus RTU (Standard & Non-standard)");
  
  setupWiFi();
  
  if (wifiConnected) {
    setupWebServer();
    setupOTA();
    server.begin();
    addToLog("🔌 Modbus TCP server started on port " + String(MODBUS_TCP_PORT));
    addToLog("✅ Ready for LUX inverter communication");
  }
  
  addToLog("🎯 Setup completed - Proxy ready!");
}

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 2000; // 2 seconds
unsigned long lastTimeSync = 0;
const unsigned long timeSyncInterval = 3600000; // 1 hour in milliseconds

void loop() {
  if (wifiConnected) {
    // Handle time-critical operations first
    handleWiFiClients(); // Process TCP requests immediately
    handleModbusRTU();   // Process RTU responses immediately
    
    // Handle less critical operations
    ArduinoOTA.handle();
    webServer.handleClient();
    
    // Periodic checks (only when needed)
    static unsigned long lastPeriodicCheck = 0;
    if (millis() - lastPeriodicCheck > 1000) { // Check every 1 second instead of 10
      // WiFi status check
      if (millis() - lastWiFiCheck > WIFI_CHECK_INTERVAL_MS) {
        if (WiFi.status() != WL_CONNECTED) {
          addToLog("⚠️ WiFi connection lost, attempting reconnection...");
          wifiConnected = false;
          timeInitialized = false; // Reset time sync when WiFi is lost
          setupWiFi();
        }
        lastWiFiCheck = millis();
      }
      
      // Periodic time synchronization (every hour)
      if (timeInitialized && (millis() - lastTimeSync > timeSyncInterval)) {
        addToLog("🔄 Periodic NTP time resync...");
        setupNTP();
        lastTimeSync = millis();
      }
      
      lastPeriodicCheck = millis();
    }
  } else {
    setupWiFi();
  }
  
  // Minimal yield to prevent watchdog timeout
  yield();
}

// Old loop function - commented out for reference
// void loop() {
//   if (wifiConnected) {
//     ArduinoOTA.handle();
//     webServer.handleClient();
//     handleWiFiClients();
//     handleModbusRTU();
//     
//     // WiFi status check
//     if (millis() - lastWiFiCheck > WIFI_CHECK_INTERVAL_MS) {
//       if (WiFi.status() != WL_CONNECTED) {
//         addToLog("⚠️ WiFi connection lost, attempting reconnection...");
//         wifiConnected = false;
//         setupWiFi();
//       }
//       lastWiFiCheck = millis();
//     }
//   } else {
//     setupWiFi();
//   }
//   
//   yield();
// }