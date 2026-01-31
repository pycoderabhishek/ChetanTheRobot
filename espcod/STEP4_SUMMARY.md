# STEP 4 Summary: ESP32 Generic Firmware Template

## Files Created

| File | Purpose |
|------|---------|
| [amhrpd_firmware.ino](amhrpd_firmware.ino) | Main firmware sketch (complete, ready to compile) |
| [FIRMWARE_GUIDE.md](FIRMWARE_GUIDE.md) | Detailed function reference & customization guide |
| [MESSAGE_FLOW.md](MESSAGE_FLOW.md) | Message sequences & practical examples |
| [QUICKSTART.md](QUICKSTART.md) | Setup & deployment in 5 steps |

---

## Key Features

### ✓ Configuration-Only Setup
Edit 6 constants and you're ready:
```cpp
WIFI_SSID, WIFI_PASSWORD
SERVER_HOST, SERVER_PORT
DEVICE_ID, DEVICE_TYPE
```

### ✓ Automatic Device Registration
First heartbeat registers device on server

### ✓ Heartbeat Every 5 Seconds
Keeps device marked as "online"

### ✓ Command Reception & Execution
Built-in commands:
- `test_hardware` → Hardware test
- `reboot` → ESP restart
- `blink` → LED feedback
- `get_status` → Device status

### ✓ JSON State Updates
Send periodic hardware state snapshots

### ✓ No Hardware-Specific Code
All hardware functions are placeholders

---

## Message Flow Summary

```
┌─ Boot ──────────────────┐
│ setup()                  │
│  → setupWiFi()          │
│  → connectWebSocket()    │
└─────────────────────────┘
          ↓
┌─ Loop (Every 10ms) ─────────────────┐
│ webSocket.loop()                     │
│ handleWiFiEvent()                    │
│ sendHeartbeat() [every 5 sec]        │
│ sendStateUpdate() [every 10+ sec]    │
└──────────────────────────────────────┘
          ↓
   ┌──────────────────┐
   │ Command Received │
   └──────────────────┘
          ↓
   handleCommand()
          ↓
   Execute action
          ↓
   sendCommandAck()
```

---

## JSON Message Examples

### Heartbeat (Registration & Keep-Alive)
```json
{
  "message_type": "heartbeat",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "timestamp": "1234567890"
}
```

### State Update
```json
{
  "message_type": "status",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "timestamp": "1234567891",
  "payload": {
    "temperature": 25.3,
    "humidity": 45.2,
    "battery": 87,
    "uptime_ms": 123456789
  }
}
```

### Command (Server → Device)
```json
{
  "message_type": "command",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "command_name": "test_hardware",
  "payload": {}
}
```

### Command ACK (Device → Server)
```json
{
  "message_type": "command_ack",
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "timestamp": "1234567892"
}
```

---

## Hardware Compatibility

| Board | Status | Setup |
|-------|--------|-------|
| ESP32 (WROOM) | ✓ Tested | Select "ESP32 Dev Module" |
| ESP32-S3 | ✓ Compatible | Select "ESP32S3 Dev Module" |
| ESP32-CAM | ✓ Compatible | Select "AI Thinker ESP32-CAM" |

---

## Customization Options

### 1. Add Sensor Reading
```cpp
// In getHardwareState():
int rawValue = analogRead(SENSOR_PIN);
float temperature = (rawValue / 4095.0) * 100;
state["temperature"] = temperature;
```

### 2. Add Custom Command
```cpp
// In handleCommand():
else if (commandName == "my_command") {
  doSomething();
  sendCommandAck(commandId, "success");
}
```

### 3. Enable State Updates
```cpp
// In loop():
if (isConnected && (millis() - lastStateUpdate > 10000)) {
  StaticJsonDocument<SEND_BUFFER_SIZE> stateDoc;
  JsonObject state = getHardwareState(stateDoc);
  sendStateUpdate(state);
  lastStateUpdate = millis();
}
```

---

## Quick Setup (5 Minutes)

1. **Install Arduino IDE & ESP32 board support**
   - Preferences → add ESP32 JSON URL
   - Boards Manager → install ESP32

2. **Install libraries**
   - WebSocketsClient (Markus Sattler)
   - ArduinoJson (Benoit Blanchon)

3. **Edit firmware configuration**
   ```cpp
   WIFI_SSID = "your_wifi"
   WIFI_PASSWORD = "your_password"
   SERVER_HOST = "your_server_ip"
   DEVICE_ID = "esp32_001"
   ```

4. **Upload**
   - Tools → Board → ESP32 Dev Module
   - Tools → Port → COM port
   - Sketch → Upload

5. **Verify**
   - Serial Monitor (115200 baud)
   - Check `/devices` endpoint on server
   - Test command: `curl http://server:8000/command?device_type=ESP32&command_name=blink`

---

## Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| WebSocketsClient | 2.3.x+ | WebSocket communication |
| ArduinoJson | 6.18.x+ | JSON parsing/serialization |
| WiFi | Built-in | Wi-Fi connectivity |

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `setupWiFi()` | Connect to Wi-Fi network |
| `connectWebSocket()` | Establish WebSocket connection |
| `registerDevice()` | Send initial device registration |
| `handleCommand()` | Route incoming commands |
| `sendHeartbeat()` | Periodic keep-alive message |
| `sendStateUpdate()` | Send hardware state snapshot |
| `testHardware()` | Hardware test placeholder |
| `getHardwareState()` | Read device state placeholder |

---

## Deployment Checklist

- [ ] Arduino IDE installed
- [ ] ESP32 board support installed
- [ ] WebSocketsClient library installed
- [ ] ArduinoJson library installed
- [ ] Wi-Fi credentials configured
- [ ] Server IP/port configured
- [ ] Device ID configured
- [ ] Sketch compiled without errors
- [ ] Device uploaded successfully
- [ ] Serial monitor shows connection
- [ ] Device appears in `/devices` endpoint
- [ ] Test command executes successfully

---

## Testing Commands

```bash
# Blink LED
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=blink"

# Run hardware test
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=test_hardware"

# List devices
curl "http://192.168.1.100:8000/devices"

# Get device status
curl "http://192.168.1.100:8000/devices/esp32_001"

# Get state history
curl "http://192.168.1.100:8000/state-history/esp32_001?limit=10"
```

---

## API Endpoints (FastAPI Server)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ws/{device_id}` | WebSocket | Device connection |
| `/devices` | GET | List all devices |
| `/devices/{device_id}` | GET | Get device details |
| `/command` | POST | Send command to devices |
| `/state-history/{device_id}` | GET | Get state snapshots |
| `/command-logs` | GET | Get command execution logs |
| `/device-connection-history/{device_id}` | GET | Get connection events |
| `/health` | GET | Server health check |

---

## Serial Output Example

```
====================================
AMHR-PD ESP32 Firmware
====================================
Device ID: esp32_001
Device Type: ESP32
====================================

[WiFi] Connecting to: HomeNetwork
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
[Heartbeat] Sent
```

---

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Won't compile | Missing libraries | Check Arduino → Manage Libraries |
| Upload fails | Wrong board selected | Tools → Board → ESP32 Dev Module |
| No Wi-Fi connection | Wrong SSID/password | Edit firmware constants |
| WebSocket won't connect | Wrong server IP | Edit SERVER_HOST constant |
| Device not in `/devices` | Not receiving heartbeat | Check serial monitor for errors |
| Commands don't execute | Device offline | Check last_heartbeat in response |

Ready for **STEP 5**?
