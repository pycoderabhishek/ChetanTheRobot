# AMHR-PD Firmware - Generic ESP32 Template

## Overview

Complete, generic firmware template for ESP32 devices in the AMHR-PD system.

**No hardware-specific code** - Fully customizable for any ESP32 variant (ESP32, ESP32-S3, ESP32-CAM).

## What This Firmware Does

✓ Connects to Wi-Fi network  
✓ Establishes WebSocket connection to FastAPI backend  
✓ Automatically registers device (device_id, device_type)  
✓ Sends heartbeat every 5 seconds to stay online  
✓ Listens for commands and executes them  
✓ Sends command acknowledgments back to server  
✓ Reports hardware state in JSON format  
✓ Handles reconnection automatically  

## Quick Start (5 Minutes)

### 1. Install Arduino IDE & Board Support
```
1. Download Arduino IDE: https://www.arduino.cc/en/software
2. Install ESP32 board support:
   Arduino IDE → Preferences → Add this to "Boards Manager URLs":
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
3. Tools → Board Manager → Search "ESP32" → Install by Espressif
```

### 2. Install Libraries
```
Arduino IDE → Sketch → Include Library → Manage Libraries
Search for and install:
- WebSocketsClient (by  Markus Sattler)
- ArduinoJson (by Benoit Blanchon) - version 6.x
```

### 3. Configure Firmware
Edit these 6 lines in `amhrpd_firmware.ino`:
```cpp
const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* SERVER_HOST = "192.168.1.100";  // Your server IP
const int SERVER_PORT = 8000;
const char* DEVICE_ID = "esp32_001";
const char* DEVICE_TYPE = "ESP32";  // or "ESP32-S3", "ESP32-CAM"
```

### 4. Upload
```
1. Connect ESP32 via USB
2. Tools → Board → ESP32 Dev Module (or your variant)
3. Tools → Port → Select COM port
4. Sketch → Upload
5. Tools → Serial Monitor (set to 115200 baud)
```

### 5. Verify
```
Serial output should show:
[WiFi] Connected!
[WebSocket] Connected!
[Device] Registered: esp32_001 (ESP32)
[Heartbeat] Sent

Then from server terminal:
curl http://192.168.1.100:8000/devices
```

## File Structure

```
amhrpd-firmware/
├── amhrpd_firmware.ino      Main firmware (compile & upload this)
├── QUICKSTART.md            Quick setup guide (this file)
├── FIRMWARE_GUIDE.md        Detailed function reference
├── MESSAGE_FLOW.md          Message examples & flows
└── STEP4_SUMMARY.md         Complete overview
```

## Configuration

### Required Settings (Edit These!)

```cpp
// Wi-Fi
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";

// Server
const char* SERVER_HOST = "192.168.1.100";      // FastAPI server IP
const int SERVER_PORT = 8000;                    // FastAPI server port

// Device Identity
const char* DEVICE_ID = "esp32_001";             // Unique per device
const char* DEVICE_TYPE = "ESP32";               // ESP32, ESP32-S3, ESP32-CAM

// Timing
const unsigned long HEARTBEAT_INTERVAL = 5000;  // ms (5 seconds)
```

### Optional Hardware Pins

Add after configuration section:
```cpp
// Hardware Pins (customize for your setup)
const int LED_PIN = 2;
const int BUTTON_PIN = 4;
const int SENSOR_PIN = 32;  // ADC pin
const int MOTOR_PIN = 12;
```

## Message Protocol

All communication is **JSON over WebSocket**.

### Device → Server (Heartbeat)
```json
{
  "message_type": "heartbeat",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "timestamp": "1234567890"
}
```
Sent every 5 seconds to keep device marked as "online".

### Device → Server (State Update)
```json
{
  "message_type": "status",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "timestamp": "1234567890",
  "payload": {
    "temperature": 25.3,
    "humidity": 42.1,
    "battery": 85,
    "uptime_ms": 123456789
  }
}
```

### Server → Device (Command)
```json
{
  "message_type": "command",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "command_name": "test_hardware",
  "payload": {}
}
```

### Device → Server (Command ACK)
```json
{
  "message_type": "command_ack",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "timestamp": "1234567891"
}
```

## Built-In Commands

The firmware supports these commands from the server:

| Command | Effect | Status |
|---------|--------|--------|
| `test_hardware` | Run hardware test function | success/error |
| `reboot` | Restart ESP32 | success (then restart) |
| `blink` | Blink LED 3x | success/error |
| `get_status` | Return device status | success |

Send commands from server:
```bash
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=blink"
```

## Customization Guide

### Add a Sensor

1. Define pin:
```cpp
const int TEMP_SENSOR_PIN = 32;
```

2. Implement in `getHardwareState()`:
```cpp
JsonObject getHardwareState(JsonDocument& doc) {
  JsonObject state = doc.to<JsonObject>();
  
  // Read analog temperature sensor
  int rawValue = analogRead(TEMP_SENSOR_PIN);
  float voltage = (rawValue / 4095.0) * 3.3;
  float temperature = voltage * 100;  // LM35: 100mV per °C
  
  state["temperature"] = temperature;
  state["uptime_ms"] = millis();
  state["wifi_signal"] = WiFi.RSSI();
  
  return state;
}
```

3. Enable periodic updates in `loop()`:
```cpp
static unsigned long lastStateUpdate = 0;
if (isConnected && (millis() - lastStateUpdate > 10000)) {
  StaticJsonDocument<SEND_BUFFER_SIZE> stateDoc;
  JsonObject state = getHardwareState(stateDoc);
  sendStateUpdate(state);
  lastStateUpdate = millis();
}
```

### Add a Custom Command

1. Implement handler in `handleCommand()`:
```cpp
else if (commandName == "led_on") {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  sendCommandAck(commandId, "success");
}
else if (commandName == "led_off") {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  sendCommandAck(commandId, "success");
}
```

2. Send from server:
```bash
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=led_on"
```

### Add Motor Control

```cpp
// In handleCommand():
else if (commandName == "motor_start") {
  int speed = doc["payload"]["speed"] | 100;
  pinMode(MOTOR_PIN, OUTPUT);
  analogWrite(MOTOR_PIN, speed);
  sendCommandAck(commandId, "success");
}
else if (commandName == "motor_stop") {
  pinMode(MOTOR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, LOW);
  sendCommandAck(commandId, "success");
}
```

## Testing

### 1. Check Device Registration
```bash
curl http://192.168.1.100:8000/devices

# Response:
{
  "total": 1,
  "devices": [
    {
      "device_id": "esp32_001",
      "device_type": "ESP32",
      "is_online": true,
      "last_heartbeat": "2026-01-24T10:30:45.123456",
      "connected_at": "2026-01-24T10:15:00.000000"
    }
  ]
}
```

### 2. Send Test Command
```bash
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=test_hardware"

# Device serial output:
[Command] ID: ..., Name: test_hardware
[Hardware] Running test...
[Hardware] Test completed
[Command] ACK sent: success
```

### 3. Check Command Logs
```bash
curl "http://192.168.1.100:8000/command-logs?device_type=ESP32&limit=10"
```

### 4. View State History
```bash
curl "http://192.168.1.100:8000/state-history/esp32_001?limit=10"
```

## Debugging

### Serial Monitor Output

Open Tools → Serial Monitor (115200 baud) to see:

```
====================================
AMHR-PD ESP32 Firmware
====================================
Device ID: esp32_001
Device Type: ESP32
====================================

[WiFi] Connecting to: MyNetwork
......
[WiFi] Connected!
[WiFi] IP: 192.168.1.50
[WebSocket] Connecting to: ws://192.168.1.100:8000/ws/esp32_001
[WebSocket] Connected!
[Device] Registered: esp32_001 (ESP32)
[Heartbeat] Sent
[Heartbeat] Sent
[Command] ID: 550e8400-..., Name: blink
[LED] Blinking...
[Command] ACK sent: success
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Won't compile | Install WebSocketsClient & ArduinoJson libraries |
| Can't upload | Try different USB cable, select correct COM port |
| No Wi-Fi connection | Check SSID/password, verify 2.4GHz network |
| WebSocket won't connect | Check server IP/port, verify server is running |
| Device not in `/devices` | Check serial monitor, look for connection errors |
| Commands won't execute | Verify device is online, check command name spelling |

## Supported Boards

| Board | Variant | Setup |
|-------|---------|-------|
| ESP32 WROOM | Generic | Select "ESP32 Dev Module" |
| ESP32-S3 | Generic | Select "ESP32S3 Dev Module" |
| ESP32-CAM | AI Thinker | Select "AI Thinker ESP32-CAM" |

## Performance Notes

- **Heartbeat interval**: 5 seconds (configurable)
- **State update interval**: 10+ seconds (recommended)
- **Memory footprint**: ~100KB available after boot
- **JSON buffer size**: 200 bytes typical
- **WebSocket reconnect**: 5 seconds on disconnect

## Library Versions

- **WebSocketsClient**: 2.3.x or higher
- **ArduinoJson**: 6.18.x or higher
- **Arduino Core for ESP32**: 2.0.x or higher

## Next Steps

1. ✓ Upload firmware
2. ✓ Verify connection
3. → Customize hardware functions
4. → Add sensor support
5. → Implement custom commands
6. → Deploy to production

## Support

See detailed documentation:
- `QUICKSTART.md` - Setup guide
- `FIRMWARE_GUIDE.md` - Function reference
- `MESSAGE_FLOW.md` - Message examples
- `STEP4_SUMMARY.md` - Overview

Ready for STEP 5?
