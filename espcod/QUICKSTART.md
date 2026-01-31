# Quick Start - ESP32 Firmware Setup

## Prerequisites

- Arduino IDE (version 1.8.x or higher)
- ESP32 board support installed
- USB cable for device programming

## Step 1: Install Dependencies

### 1.1 Add ESP32 Board Support
```
Arduino IDE → Preferences
Boards Manager URLs (add to list):
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

Then:
```
Tools → Board → Boards Manager
Search: esp32
Install "ESP32 by Espressif Systems"
```

### 1.2 Install Required Libraries
```
Sketch → Include Library → Manage Libraries

Search for and install:
1. "WebSocketsClient" by Markus Sattler
2. "ArduinoJson" by Benoit Blanchon (version 6.x)

Check versions are compatible:
- WebSocketsClient: 2.3.x or higher
- ArduinoJson: 6.18.x or higher
```

## Step 2: Configure Firmware

Edit these constants in `amhrpd_firmware.ino`:

```cpp
// Your Wi-Fi credentials
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";

// Your server IP and port
const char* SERVER_HOST = "192.168.1.100";  // Change to your server IP
const int SERVER_PORT = 8000;

// Unique device identifier
const char* DEVICE_ID = "esp32_001";
const char* DEVICE_TYPE = "ESP32";  // or ESP32-S3, ESP32-CAM
```

## Step 3: Upload to Device

### 3.1 Connect Device
- Plug ESP32 into USB port
- Wait for driver to install (may take 30 seconds)

### 3.2 Select Board and Port
```
Tools → Board → ESP32 Arduino → Select your board type
Tools → Port → Select COM port

For different boards:
- ESP32-WROOM → "ESP32 Dev Module"
- ESP32-S3 → "ESP32S3 Dev Module"
- ESP32-CAM → "AI Thinker ESP32-CAM"
```

### 3.3 Upload
```
Sketch → Upload
(Or press Ctrl+U)

Wait for "Uploading..." to complete
Should show "Hard resetting via RTS pin..."
```

### 3.4 Monitor Serial Output
```
Tools → Serial Monitor
Set baud rate to 115200

You should see:
====================================
AMHR-PD ESP32 Firmware
====================================
Device ID: esp32_001
Device Type: ESP32
====================================

[WiFi] Connecting to: YOUR_SSID
...
[WiFi] Connected!
[WiFi] IP: 192.168.x.x
[WebSocket] Connecting to: ws://192.168.1.100:8000/ws/esp32_001
[WebSocket] Connected!
[Device] Registered: esp32_001 (ESP32)
[Heartbeat] Sent
```

## Step 4: Verify Backend Connection

### 4.1 Check if Server is Running
```
In a terminal with Python:
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 Verify Device Registration
```
In another terminal:
curl http://192.168.1.100:8000/devices

Response should include your device:
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

## Step 5: Test Commands

### 5.1 Blink LED
```
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=blink"

Device serial monitor should show:
[Command] ID: ..., Name: blink
[Command] ACK sent: success
```

### 5.2 Run Hardware Test
```
curl -X POST "http://192.168.1.100:8000/command?device_type=ESP32&command_name=test_hardware"

Device serial monitor should show:
[Command] ID: ..., Name: test_hardware
[Hardware] Running test...
[Hardware] Test completed
[Command] ACK sent: success
```

## Customization

### Add Temperature Sensor Support

1. Add pin definition:
```cpp
const int TEMP_SENSOR_PIN = 32;
```

2. Implement `getHardwareState()`:
```cpp
JsonObject getHardwareState(JsonDocument& doc) {
  JsonObject state = doc.to<JsonObject>();
  
  int rawValue = analogRead(TEMP_SENSOR_PIN);
  float voltage = (rawValue / 4095.0) * 3.3;
  float temperature = voltage * 100;  // LM35: 100mV per °C
  
  state["temperature"] = temperature;
  state["uptime_ms"] = millis();
  
  return state;
}
```

3. Enable state updates in `loop()`:
```cpp
static unsigned long lastStateUpdate = 0;
if (isConnected && (millis() - lastStateUpdate > 10000)) {
  StaticJsonDocument<SEND_BUFFER_SIZE> stateDoc;
  JsonObject state = getHardwareState(stateDoc);
  sendStateUpdate(state);
  lastStateUpdate = millis();
}
```

### Add Custom LED Blink

1. Add pin definition:
```cpp
const int LED_PIN = 2;
```

2. Implement `blinkLED()`:
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

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't connect to Wi-Fi | Check SSID/password, verify 2.4GHz band selected |
| WebSocket won't connect | Check server IP/port are correct, verify server running |
| Serial monitor shows garbage | Change baud rate to 115200 |
| Device not appearing in /devices endpoint | Check last heartbeat in serial, verify network connectivity |
| Commands not executing | Check command name spelling, verify device is online |
| Upload fails | Try different USB cable, check COM port selection |

## Next Steps

1. ✓ Firmware uploaded
2. ✓ Device connected to server
3. ✓ Heartbeat working
4. → Customize hardware functions
5. → Add sensor readings
6. → Implement custom commands

See `FIRMWARE_GUIDE.md` for detailed documentation.
See `MESSAGE_FLOW.md` for message examples.

Ready for STEP 5?
