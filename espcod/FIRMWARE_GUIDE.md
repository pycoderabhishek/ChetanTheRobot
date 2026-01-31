# AMHR-PD ESP32 Firmware Template

## Overview

Generic firmware template for all ESP32 variants (ESP32, ESP32-S3, ESP32-CAM).

**No hardware-specific pin logic** - customizable via function placeholders.

## Configuration

Edit these constants in the sketch:

```cpp
// Wi-Fi
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";

// Server
const char* SERVER_HOST = "192.168.1.100";
const int SERVER_PORT = 8000;

// Device
const char* DEVICE_ID = "esp32_001";
const char* DEVICE_TYPE = "ESP32";  // or "ESP32-S3", "ESP32-CAM"

// Heartbeat
const unsigned long HEARTBEAT_INTERVAL = 5000;  // milliseconds
```

## Dependencies

Add these libraries via Arduino IDE Library Manager:

1. **WebSocketsClient** by Markus Sattler
2. **ArduinoJson** by Benoit Blanchon (version 6.x)

Installation:
```
Sketch → Include Library → Manage Libraries
Search and install each library
```

## Message Flow

### 1. Boot Sequence
```
ESP32 boots
  ↓
Connect to Wi-Fi
  ↓
Establish WebSocket connection to server
  ↓
Send first heartbeat (device registration)
  ↓
Server registers device
```

### 2. Runtime - Heartbeat Loop
```
Every 5 seconds:
  ESP32 sends heartbeat message
  ↓
Server updates last_heartbeat timestamp
  ↓
Device remains marked as "online"
```

### 3. Server-to-Device - Command Reception
```
Server sends command (POST /command)
  ↓
WebSocket delivers command JSON
  ↓
ESP32 parses command_name
  ↓
Routes to appropriate handler (test_hardware, reboot, blink, etc.)
  ↓
Executes action
  ↓
Sends command_ack with status (success/error)
  ↓
Server logs completion
```

### 4. Device-to-Server - State Update
```
ESP32 periodically reads hardware state
  ↓
Packages state into JSON payload
  ↓
Sends status message (message_type="status")
  ↓
Server stores state snapshot in database
```

### 5. Disconnection
```
Device loses power / network / manual reset
  ↓
WebSocket disconnects
  ↓
Server detects disconnect (no heartbeat > timeout)
  ↓
Device marked as "offline"
  ↓
Connection event logged
```

## JSON Message Examples

### Device Registration (First Heartbeat)
```json
{
  "message_type": "heartbeat",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "timestamp": "1234567890"
}
```

### Periodic Heartbeat
```json
{
  "message_type": "heartbeat",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "timestamp": "1234567891"
}
```

### State Update
```json
{
  "message_type": "status",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "timestamp": "1234567892",
  "payload": {
    "temperature": 25.3,
    "humidity": 45.2,
    "battery": 87,
    "uptime_ms": 123456789
  }
}
```

### Incoming Command
```json
{
  "message_type": "command",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "command_name": "test_hardware",
  "payload": {}
}
```

### Command Acknowledgment
```json
{
  "message_type": "command_ack",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "timestamp": "1234567893"
}
```

## Function Reference

### Core Functions

#### `setupWiFi()`
- Connects to Wi-Fi network
- Displays IP address on success
- Retries for 30 attempts
- Used in `setup()`

#### `connectWebSocket()`
- Initiates WebSocket connection to server
- Registers event handler
- Sets auto-reconnect interval (5 seconds)
- Called from `setup()` and Wi-Fi recovery

#### `handleWebSocketEvent(WStype_t type, uint8_t* payload, size_t length)`
- Callback for all WebSocket events
- Handles: CONNECTED, DISCONNECTED, TEXT, ERROR
- Calls `registerDevice()` on connection
- Routes to `handleWebSocketMessage()` on text received

#### `handleWebSocketMessage(char* payload, size_t length)`
- Parses incoming JSON message
- Routes by `message_type`
- Calls `handleCommand()` for commands

### Command Handlers

#### `handleCommand(JsonDocument& doc)`
- Routes commands by `command_name`
- Supported built-in commands:
  - `test_hardware` → calls `testHardware()`
  - `reboot` → triggers ESP.restart()
  - `blink` → calls `blinkLED()`
  - `get_status` → returns current state

#### `testHardware()`
- **PLACEHOLDER** - Customize with your hardware tests
- Examples:
  ```cpp
  // Test LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  
  // Test sensor
  float temp = readTemperatureSensor();
  
  // Test motor
  runMotorTest();
  ```
- Return `true` if passed, `false` if failed

#### `blinkLED()`
- **PLACEHOLDER** - Customize with your LED pin
- Example:
  ```cpp
  const int LED_PIN = 2;
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);
    delay(200);
  }
  ```

#### `getHardwareState(JsonDocument& doc)`
- **PLACEHOLDER** - Return your device's actual state
- Called during state update
- Example:
  ```cpp
  JsonObject state = doc.to<JsonObject>();
  state["temperature"] = readTemperature();
  state["humidity"] = readHumidity();
  state["battery"] = readBatteryVoltage();
  state["uptime_ms"] = millis();
  return state;
  ```

### State & Messages

#### `sendStateUpdate(JsonObject& stateData)`
- Packages state JSON into message
- Sends via WebSocket
- Include message_type, device_id, timestamp

#### `sendCommandAck(String commandId, String status)`
- Sends command acknowledgment
- Status: "success" or "error"
- Triggered automatically by `handleCommand()`

#### `sendHeartbeat()`
- Called every 5 seconds (configurable)
- Maintains server connection
- Device registration on first call

### Utility

#### `getTimestamp()`
- Returns current timestamp (currently millis())
- Can be replaced with NTP for real time

## Customization Guide

### 1. Add Custom Command Handler

```cpp
void handleCommand(JsonDocument& doc) {
  String commandName = doc["command_name"] | "";
  
  // ... existing handlers ...
  
  else if (commandName == "my_custom_command") {
    bool success = myCustomFunction();
    sendCommandAck(commandId, success ? "success" : "error");
  }
}
```

### 2. Add Periodic State Updates

Uncomment in `loop()`:
```cpp
static unsigned long lastStateUpdate = 0;
if (isConnected && (millis() - lastStateUpdate > 10000)) {
  StaticJsonDocument<SEND_BUFFER_SIZE> stateDoc;
  JsonObject state = getHardwareState(stateDoc);
  sendStateUpdate(state);
  lastStateUpdate = millis();
}
```

### 3. Add Hardware-Specific Pins

Add pin definitions near top:
```cpp
// Hardware Pins
const int LED_PIN = 2;
const int BUTTON_PIN = 4;
const int SENSOR_PIN = 32;  // ADC pin
```

Then use in hardware functions:
```cpp
bool blinkLED() {
  pinMode(LED_PIN, OUTPUT);
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);
    delay(200);
  }
  return true;
}
```

### 4. Reading Sensors

Implement in `getHardwareState()`:
```cpp
JsonObject getHardwareState(JsonDocument& doc) {
  JsonObject state = doc.to<JsonObject>();
  
  // Read ADC sensor
  int rawValue = analogRead(SENSOR_PIN);
  float voltage = (rawValue / 4095.0) * 3.3;
  
  state["sensor_voltage"] = voltage;
  state["uptime_ms"] = millis();
  state["wifi_signal"] = WiFi.RSSI();
  state["free_heap"] = ESP.getFreeHeap();
  
  return state;
}
```

## Debugging

### Serial Monitor Output

```
====================================
AMHR-PD ESP32 Firmware
====================================
Device ID: esp32_001
Device Type: ESP32
====================================

[WiFi] Connecting to: MyWiFi
....................
[WiFi] Connected!
[WiFi] IP: 192.168.1.50
[WebSocket] Connecting to: ws://192.168.1.100:8000/ws/esp32_001
[WebSocket] Connected!
[Device] Registered: esp32_001 (ESP32)
[Heartbeat] Sent
[Heartbeat] Sent
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Can't connect to Wi-Fi | Check SSID/password, verify 2.4GHz band |
| WebSocket won't connect | Check server IP/port, verify server is running |
| Commands not received | Check device is online in server dashboard |
| Memory issues | Reduce JSON buffer sizes or enable serial debugging off |

## Performance Notes

- **Heartbeat**: 5 seconds (minimum 1 second recommended)
- **State updates**: 10+ seconds (reduce load on device)
- **JSON buffers**: 200 bytes typical
- **Memory**: ~100KB available after boot

## Hardware Compatibility

| Board | Status | Notes |
|-------|--------|-------|
| ESP32 | ✓ Tested | Standard boards |
| ESP32-S3 | ✓ Compatible | Faster processor |
| ESP32-CAM | ✓ Compatible | Lower RAM available |

## Uploading to Device

1. Install ESP32 board definitions in Arduino IDE
2. Select board: Tools → Board → ESP32
3. Select port: Tools → Port
4. Click Upload
5. Monitor serial output at 115200 baud

## Next Steps

1. Customize Wi-Fi credentials
2. Implement `getHardwareState()` for your hardware
3. Add custom commands in `handleCommand()`
4. Test with FastAPI server running
5. Monitor logs in server dashboard

Ready for STEP 5?
