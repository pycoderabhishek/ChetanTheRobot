# AMHR-PD Firmware - Message Flow & Examples

## Complete Message Flow Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│                     ESP32 Boot Sequence                         │
└─────────────────────────────────────────────────────────────────┘
              ↓
         setup() called
              ↓
        setupWiFi()
        Connect to WiFi SSID
        Wait for WL_CONNECTED
              ↓
        connectWebSocket()
        Establish WebSocket /ws/esp32_001
              ↓
        loop() begins


┌─────────────────────────────────────────────────────────────────┐
│                  Continuous Loop (Every 10ms)                   │
└─────────────────────────────────────────────────────────────────┘
         ↓
    webSocket.loop()
    Check for incoming messages
         ↓
    handleWiFiEvent()
    Monitor Wi-Fi status
         ↓
    sendHeartbeat()
    Every 5 seconds:
      - Package JSON with device_id, device_type
      - Send via WebSocket
      - Server updates last_heartbeat
      - Device stays marked "online"
         ↓
    [Optional] sendStateUpdate()
    Every 10+ seconds:
      - Read hardware state
      - Package state_data as JSON payload
      - Send "status" message
      - Server stores in database
         ↓
    delay(10ms)
    Back to webSocket.loop()


┌─────────────────────────────────────────────────────────────────┐
│            Command Reception & Execution Flow                   │
└─────────────────────────────────────────────────────────────────┘

[Server sends command]
        ↓
[WebSocket delivers JSON]
        ↓
handleWebSocketEvent(WStype_TEXT)
        ↓
handleWebSocketMessage()
        ↓
deserializeJson(payload)
        ↓
if (messageType == "command")
        ↓
handleCommand()
        ↓
    ├─ if commandName == "test_hardware"
    │      ↓
    │   testHardware()
    │      ↓
    │   return success/fail
    │
    ├─ if commandName == "reboot"
    │      ↓
    │   sendCommandAck()
    │      ↓
    │   delay(1000)
    │      ↓
    │   ESP.restart()
    │
    ├─ if commandName == "blink"
    │      ↓
    │   blinkLED()
    │      ↓
    │   return success/fail
    │
    └─ else
           ↓
        status = "error"
         ↓
sendCommandAck()
        ↓
Package JSON with:
  - command_id
  - status (success/error)
  - device_id
  - timestamp
        ↓
webSocket.sendTXT()
        ↓
[Server receives ACK]
        ↓
Server updates command_logs table
```

## Practical Examples

### Example 1: Basic Setup (Default)

```cpp
// Configuration
const char* WIFI_SSID = "HomeNetwork";
const char* WIFI_PASSWORD = "password123";
const char* SERVER_HOST = "192.168.1.100";
const int SERVER_PORT = 8000;
const char* DEVICE_ID = "esp32_001";
const char* DEVICE_TYPE = "ESP32";

// This is all that's needed for basic operation
// Device will:
// 1. Connect to Wi-Fi
// 2. Connect to WebSocket
// 3. Send heartbeat every 5 seconds
// 4. Receive and execute commands
// 5. Send command ACKs
```

### Example 2: Add Temperature Sensor

```cpp
// Add pin definition
const int TEMP_SENSOR_PIN = 32;  // ADC pin

// Implement state reading
JsonObject getHardwareState(JsonDocument& doc) {
  JsonObject state = doc.to<JsonObject>();
  
  // Read analog temperature sensor (LM35 example)
  int rawValue = analogRead(TEMP_SENSOR_PIN);
  float voltage = (rawValue / 4095.0) * 3.3;  // Convert to voltage
  float temperature = voltage * 100;            // LM35: 100mV per °C
  
  state["temperature"] = temperature;
  state["uptime_ms"] = millis();
  state["wifi_signal"] = WiFi.RSSI();
  
  return state;
}

// Enable periodic state updates in loop()
static unsigned long lastStateUpdate = 0;
if (isConnected && (millis() - lastStateUpdate > 10000)) {
  StaticJsonDocument<SEND_BUFFER_SIZE> stateDoc;
  JsonObject state = getHardwareState(stateDoc);
  sendStateUpdate(state);
  lastStateUpdate = millis();
}

// Now server will receive:
// {
//   "message_type": "status",
//   "device_id": "esp32_001",
//   "timestamp": "1234567890",
//   "payload": {
//     "temperature": 25.3,
//     "uptime_ms": 123456789,
//     "wifi_signal": -45
//   }
// }
```

### Example 3: Custom Command - Control LED

```cpp
// Add pin definition at top
const int LED_PIN = 2;

// Implement LED control in handleCommand()
void handleCommand(JsonDocument& doc) {
  String commandId = doc["command_id"] | "";
  String commandName = doc["command_name"] | "";
  JsonObject payload = doc["payload"];
  
  bool success = false;
  String status = "success";
  
  if (commandName == "test_hardware") {
    success = testHardware();
  }
  else if (commandName == "led_on") {
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);
    success = true;
  }
  else if (commandName == "led_off") {
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    success = true;
  }
  else if (commandName == "led_blink") {
    int blinks = payload["blinks"] | 3;
    int delay_ms = payload["delay_ms"] | 200;
    
    pinMode(LED_PIN, OUTPUT);
    for (int i = 0; i < blinks; i++) {
      digitalWrite(LED_PIN, HIGH);
      delay(delay_ms);
      digitalWrite(LED_PIN, LOW);
      delay(delay_ms);
    }
    success = true;
  }
  else {
    status = "error";
  }
  
  sendCommandAck(commandId, success ? status : "error");
}

// Commands from server:
// POST /command?device_type=ESP32&command_name=led_on
// POST /command?device_type=ESP32&command_name=led_blink&payload={"blinks":5,"delay_ms":500}
```

### Example 4: Motor Control with Feedback

```cpp
// Pin definitions
const int MOTOR_PIN = 12;
const int MOTOR_FEEDBACK_PIN = 35;

// Implement motor state
JsonObject getHardwareState(JsonDocument& doc) {
  JsonObject state = doc.to<JsonObject>();
  
  int feedbackValue = analogRead(MOTOR_FEEDBACK_PIN);
  float feedbackPercent = (feedbackValue / 4095.0) * 100;
  
  state["motor_feedback"] = feedbackPercent;
  state["is_running"] = (digitalRead(MOTOR_PIN) == HIGH);
  state["uptime_ms"] = millis();
  
  return state;
}

// Motor control commands
void handleCommand(JsonDocument& doc) {
  String commandName = doc["command_name"] | "";
  JsonObject payload = doc["payload"];
  
  if (commandName == "motor_start") {
    int speed = payload["speed"] | 100;  // 0-100
    ledcWrite(0, speed * 255 / 100);
    digitalWrite(MOTOR_PIN, HIGH);
    sendCommandAck(doc["command_id"], "success");
  }
  else if (commandName == "motor_stop") {
    digitalWrite(MOTOR_PIN, LOW);
    sendCommandAck(doc["command_id"], "success");
  }
  // ... other commands
}

// Server receives state updates:
// {
//   "payload": {
//     "motor_feedback": 75.3,
//     "is_running": true,
//     "uptime_ms": 234567890
//   }
// }
```

### Example 5: Multiple Sensors with Advanced State

```cpp
// Multiple sensor pins
const int TEMP_PIN = 32;
const int HUMIDITY_PIN = 33;
const int BATTERY_PIN = 34;
const int LED_PIN = 2;

// Rich state reporting
JsonObject getHardwareState(JsonDocument& doc) {
  JsonObject state = doc.to<JsonObject>();
  
  // Temperature (ADC)
  int tempRaw = analogRead(TEMP_PIN);
  float tempVoltage = (tempRaw / 4095.0) * 3.3;
  float temperature = tempVoltage * 100;
  
  // Humidity (simulated)
  int humidityRaw = analogRead(HUMIDITY_PIN);
  float humidity = (humidityRaw / 4095.0) * 100;
  
  // Battery voltage
  int batteryRaw = analogRead(BATTERY_PIN);
  float batteryVoltage = (batteryRaw / 4095.0) * 3.3 * 2;  // With voltage divider
  
  // Calculate battery percentage (example)
  float batteryPercent = ((batteryVoltage - 3.0) / (4.2 - 3.0)) * 100;
  batteryPercent = max(0.0, min(100.0, batteryPercent));
  
  // Build state
  state["temperature"] = temperature;
  state["humidity"] = humidity;
  state["battery_voltage"] = batteryVoltage;
  state["battery_percent"] = batteryPercent;
  state["uptime_ms"] = millis();
  state["wifi_signal"] = WiFi.RSSI();
  state["free_heap"] = ESP.getFreeHeap();
  state["chip_temperature"] = (tempsensor_get_celsius());  // ESP32 internal temp
  
  return state;
}

// Server receives comprehensive state:
// {
//   "payload": {
//     "temperature": 24.5,
//     "humidity": 42.1,
//     "battery_voltage": 3.85,
//     "battery_percent": 85.0,
//     "uptime_ms": 567890123,
//     "wifi_signal": -52,
//     "free_heap": 87456,
//     "chip_temperature": 45.2
//   }
// }
```

## Testing Commands via Server

### Test with curl or HTTP client:

```bash
# Start device in offline mode to test server routes
# Then send command to all ESP32 devices

# Test hardware
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=test_hardware&payload={}"

# Reboot all devices of type
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=reboot&payload={}"

# Blink LED
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=blink&payload={}"

# Custom command with parameters
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=led_blink&payload={\"blinks\":5,\"delay_ms\":500}"
```

## Debugging Workflow

### 1. Check Serial Output
```
Open Serial Monitor (Tools → Serial Monitor)
Set baud rate to 115200
Watch for connection messages
```

### 2. Verify Server Connection
```
In server terminal:
- Check if device appears in "GET /devices"
- Watch for WebSocket connection logs
- Check last_heartbeat timestamp
```

### 3. Test Command Reception
```
Server terminal:
curl -X POST "http://localhost:8000/command?device_type=ESP32&command_name=blink"

Device terminal should show:
[Command] ID: ..., Name: blink
[Command] ACK sent: success
```

### 4. Check State Updates
```
Verify state in database:
GET /state-history/esp32_001?limit=10

Should show recent state snapshots with timestamps
```

Ready for STEP 5?
