# STEP 3 — ESP32-S3 + PCA9685 FIRMWARE

**Status:** COMPLETE  
**Date:** January 26, 2026

---

## Overview

STEP 3 delivers a **production-grade Arduino firmware** for ESP32-S3 that:

- **Initializes I2C** to PCA9685 PWM driver (GPIO 8/9, 400 kHz)
- **Connects to Wi-Fi** with configurable SSID/password
- **Establishes WebSocket** connection to FastAPI backend (`/servo/ws/servo`)
- **Registers device** as "servoscontroller" with device type "esp32s3"
- **Receives servo commands** from backend (channel + angle)
- **Converts angle → PCA9685 ticks** using STEP 1 conversion logic
- **Drives 10 MG996R servos** (channels 0–9 only)
- **Sends state feedback** (current angles) back to backend
- **Handles errors** gracefully (I2C failures, disconnections)
- **Recovers automatically** with exponential backoff on connection loss

---

## Hardware Setup

### ESP32-S3 Pin Configuration

| Function | GPIO | Standard Use |
|----------|------|--------------|
| I2C SDA (PCA9685) | 8 | Serial data |
| I2C SCL (PCA9685) | 9 | Serial clock |
| UART TX | 43 | Serial debug |
| UART RX | 44 | Serial debug |
| Power | 3V3 | 3.3V logic level |
| GND | GND | Ground reference |

### PCA9685 Configuration

- **I2C Address**: 0x40 (default)
- **PWM Frequency**: 50 Hz (servo standard)
- **Clock**: 400 kHz I2C
- **Channels**: 0–9 active (10–15 unused)
- **Resolution**: 12-bit (0–4095 ticks)

### Servo Motor Connections

```
PCA9685 Signal Outputs (channels 0–9)
↓
Servo connectors (3-wire)
├─ Signal (red PCB) → PCA9685 PWM output
├─ Power (brown/black PCB) → External 6V supply
└─ Ground (brown) → Common ground with ESP32
```

**CRITICAL**: Servos powered from **external 6V supply**, NOT ESP32 GPIO.

---

## Firmware Architecture

```
┌─────────────────────────────────────────────┐
│ setup()                                     │
├─────────────────────────────────────────────┤
│ 1. Serial init (115200 baud)                │
│ 2. Servo config setup (STEP 1 module)       │
│ 3. I2C init (GPIO 8/9, 400 kHz)             │
│ 4. PCA9685 init (50 Hz, home position)      │
│ 5. Wi-Fi connect                            │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│ loop() — Main execution every 10 ms         │
├─────────────────────────────────────────────┤
│ 1. loop_wifi()      – Check Wi-Fi state     │
│ 2. loop_websocket() – Poll WebSocket        │
│ 3. send_heartbeat() – Periodic ping (5s)    │
│ 4. delay(10)        – CPU relief            │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│ State Machine                               │
├─────────────────────────────────────────────┤
│ STATE_WIFI_CONNECTING                       │
│   → STATE_WIFI_CONNECTED                    │
│   → STATE_WEBSOCKET_CONNECTING              │
│   → STATE_WEBSOCKET_CONNECTED ←→ STATE_ERROR│
│                                             │
│ On error: Reconnect with exponential backoff│
└─────────────────────────────────────────────┘
```

---

## Configuration (Edit Before Upload)

**File**: `amhrpd-firmware/amhrpd_firmware.ino` (lines 29–46)

```cpp
// Wi-Fi Credentials
const char WIFI_SSID[] = "YOUR_SSID";
const char WIFI_PASSWORD[] = "YOUR_PASSWORD";

// Backend Server
const char BACKEND_HOST[] = "192.168.1.100";  // IP address
const uint16_t BACKEND_PORT = 8000;

// Device Identity (do NOT change)
const char DEVICE_ID[] = "servoscontroller";
const char DEVICE_TYPE[] = "esp32s3";
const char FIRMWARE_VERSION[] = "1.0.0";

// I2C Pins for PCA9685 (typically fixed)
const int I2C_SDA_PIN = 8;
const int I2C_SCL_PIN = 9;
```

**Before uploading**:
1. Change `WIFI_SSID` and `WIFI_PASSWORD` to your network
2. Set `BACKEND_HOST` to the IP address of your FastAPI backend
3. Keep `DEVICE_ID = "servoscontroller"` (required by backend)

---

## Key Modules

### Module 1: Servo Configuration

```cpp
#include "servo_config.h"  // From STEP 1

ServoConfig servos[10];
ServoController servo_controller;

// In setup():
createDefaultServoConfig(servos);
servo_controller.begin(servos, 10);
```

All angle-to-PWM conversions handled by `servo_controller` (identical logic to STEP 1 Python backend).

### Module 2: I2C & PCA9685

```cpp
Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
Wire.setClock(400000);  // 400 kHz

pca9685.begin();
pca9685.setPWMFreq(50);  // 50 Hz

// Drive servo on channel 0 to 90 degrees
uint16_t ticks = servo_controller.angleToPca9685Ticks(0, 90.0);
pca9685.setPWM(0, 0, ticks);  // setPWM(channel, ON, OFF)
```

### Module 3: Wi-Fi Connection

**State Flow**:
```
WIFI_CONNECTING
  ↓ (WiFi.begin())
  → Poll WiFi.status() every 2 seconds
  ↓
WIFI_CONNECTED
  ↓ (setup_websocket())
  → Launch WebSocket connection
```

**Retry Logic**:
- Retry every 2 seconds
- Give up after 60 attempts (2 minutes)
- If timeout, call `ESP.restart()`

### Module 4: WebSocket Connection

**State Flow**:
```
WEBSOCKET_CONNECTING
  ↓ (webSocket.begin())
  → Poll webSocket.loop() every 10 ms
  ↓ (webSocket event fires)
WStype_CONNECTED
  ↓ (send registration message)
  → Wait for ACK with servo configs
  ↓
WEBSOCKET_CONNECTED
  ↓ (receive commands)
  → Process servo control messages
  ↓ (on disconnect)
WEBSOCKET_CONNECTING
  → Retry connection
```

### Module 5: Message Handler

**Incoming Message Types**:

1. **"ack"** – Registration acknowledgement with servo config
   ```json
   {"type": "ack", "data": {"0": {...}, "1": {...}, ...}}
   ```
   Action: Set `system_state = STATE_WEBSOCKET_CONNECTED`

2. **"command"** – Servo control command
   ```json
   {"type": "command", "data": {"channel": 0, "angle": 120.0}}
   ```
   Action: Call `handle_servo_command(channel, angle)`

3. **"ping"** – Heartbeat from backend
   ```json
   {"type": "ping"}
   ```
   Action: Send "pong" response

**Outgoing Message Types**:

1. **"register"** – Initial device registration
   ```json
   {
     "type": "register",
     "data": {
       "device_id": "servoscontroller",
       "device_type": "esp32s3",
       "firmware_version": "1.0.0"
     }
   }
   ```

2. **"feedback"** – Servo state update (continuous)
   ```json
   {
     "type": "feedback",
     "data": {
       "channel": 0,
       "current_angle": 120.0,
       "pulse_width_us": 1610,
       "pca9685_ticks": 330
     }
   }
   ```

3. **"error"** – Error report
   ```json
   {
     "type": "error",
     "data": {
       "channel": 0,
       "error": "Invalid channel"
     }
   }
   ```

4. **"pong"** – Response to backend ping
   ```json
   {"type": "pong"}
   ```

---

## Servo Control Flow

### Receiving a Command

```cpp
// Backend sends:
{
  "type": "command",
  "data": {"channel": 0, "angle": 120.0}
}

// 1. handle_websocket_message() receives JSON
// 2. Parses: channel=0, angle=120.0
// 3. Validates: channel in [0–9]? YES
// 4. Calls: handle_servo_command(0, 120.0)
//
// In handle_servo_command():
// 5. Clamp angle: 120.0 (already in range)
// 6. Update target: servo_state.target_angle[0] = 120.0
// 7. Convert: angle → 1610 µs → 330 ticks
// 8. Write: pca9685.setPWM(0, 0, 330)
// 9. Servo begins moving
//
// 10. Periodically call send_servo_feedback(0):
//     - Simulate motion (2° per feedback)
//     - Send: {"type": "feedback", "data": {...}}
//     - Backend updates local state
```

### Error Handling

**Invalid Channel**:
```cpp
if (channel < 0 || channel > 9) {
  send_error_report(channel, "Channel out of range [0-9]");
  return;
}
```
Sends error message to backend; servo not moved.

**PCA9685 I2C Failure**:
```cpp
if (error != 0) {  // Wire.endTransmission() != 0
  Serial.println("[PCA9685] ERROR: Device not found!");
  system_state = STATE_ERROR;
}
```
System enters ERROR state; WebSocket can still send error reports.

**WebSocket Disconnection**:
```cpp
case WStype_DISCONNECTED:
  system_state = STATE_WIFI_CONNECTED;
  setup_websocket();  // Reconnect
```
Automatically attempts reconnection.

---

## Feedback Simulation

The firmware includes simulated servo feedback (for development/testing without sensors):

```cpp
void send_servo_feedback(int channel) {
  float current = servo_state.current_angle[channel];
  float target = servo_state.target_angle[channel];
  
  // Move 2 degrees per feedback cycle toward target
  float diff = target - current;
  if (abs(diff) > 2.0) {
    current += (diff > 0) ? 2.0 : -2.0;
    servo_state.is_moving[channel] = true;
  } else {
    servo_state.current_angle[channel] = target;
    servo_state.is_moving[channel] = false;
  }
}
```

**In production**: Replace with actual servo position sensor (e.g., potentiometer on servo output shaft).

---

## Libraries Required

Install via Arduino IDE: **Sketch → Include Library → Manage Libraries**

| Library | Author | Purpose |
|---------|--------|---------|
| ArduinoWebSockets | Links2004 | WebSocket client |
| ArduinoJson | bblanchon | JSON serialization |
| Adafruit PWM Servo Driver | Adafruit | PCA9685 interface |
| Wire | Arduino | I2C communication |
| WiFi | Arduino | ESP32 Wi-Fi |

**Recommended versions**:
- ArduinoWebSockets: 2.3.6+
- ArduinoJson: 6.20.0+
- Adafruit PWM Servo Driver: 2.4.0+

---

## Compilation & Upload

### Arduino IDE Setup

1. **Install ESP32 Board**:
   - File → Preferences
   - Paste URL: `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
   - Board Manager → Search "esp32" → Install "esp32 by Espressif Systems"

2. **Select Board**:
   - Tools → Board → esp32 → "ESP32-S3 Dev Module"

3. **Configure Settings**:
   - USB CDC On Boot: Enabled
   - Upload Speed: 921600
   - Port: COM3 (or your USB port)

4. **Compile & Upload**:
   - Sketch → Upload (or Ctrl+U)
   - Monitor output in Serial Monitor (115200 baud)

### Expected Serial Output

```
========================================
AMHR-PD Professional Servo Controller
========================================
Firmware Version: 1.0.0
Device ID: servoscontroller
Device Type: esp32s3

[INIT] Initializing servo configuration...
[INIT] Servo configuration loaded
[INIT] Initializing I2C...
[INIT] Initializing PCA9685 PWM driver...
[PCA9685] Device found at address 0x40
[PCA9685] Initialized at 50 Hz
[PCA9685] All channels set to 90 degrees (home)
[INIT] Connecting to Wi-Fi...
[WiFi] SSID: YOUR_SSID
[WiFi] Connected! IP: 192.168.1.123

[INIT] Setup complete!
========================================

[WS] Connecting to WebSocket...
[WS] Host: 192.168.1.100:8000
[WS] Connected!
[WS] Registration message sent
[WS] Registration ACK received
[CMD] Channel 0 -> 90.0 degrees
[PCA9685] CH0 = 307 ticks
```

---

## Debugging

### Serial Monitor

Open **Tools → Serial Monitor** (115200 baud) to see:

- [WiFi] messages – Wi-Fi connection status
- [WS] messages – WebSocket events
- [CMD] messages – Servo commands received
- [PCA9685] messages – PWM writes
- [ERROR] messages – Fault conditions

### Typical Debug Session

```
[WiFi] Connecting...
[WiFi] .....
[WiFi] Connected! IP: 192.168.1.123
[WS] Connecting to WebSocket...
[WS] Host: 192.168.1.100:8000
[WS] Connected!
[WS] Registration message sent
[WS] Registration ACK received
[CMD] Channel 0 -> 120.0 degrees
[PCA9685] CH0 = 330 ticks
[WS] Sending feedback: CH0 = 119.5°
[WS] Sending feedback: CH0 = 120.0°
[PCA9685] All servos idle
```

---

## Files Created/Modified

| File | Type | Lines | Purpose |
|------|------|-------|---------|
| [`amhrpd-firmware/amhrpd_firmware.ino`](amhrpd-firmware/amhrpd_firmware.ino) | Complete | 500 | Main firmware |
| [`amhrpd-firmware/servo_config.h`](amhrpd-firmware/servo_config.h) | Existing | 250 | STEP 1 header (included) |

---

## Important Notes

### Power Considerations

- **ESP32**: 5V USB power (or 3.3V regulation)
- **PCA9685**: 5V logic supply (from same USB power)
- **Servos**: **SEPARATE 6V, ≥20A power supply** (NOT from ESP32)
- **Common Ground**: All GND pins connected together

```
USB 5V ──→ PCA9685 VCC
       └→ ESP32 5V (via onboard regulator → 3.3V logic)

External 6V ──→ Servo power rail
           └→ Servo GND ←──── (common to ESP32 GND)
```

### I2C Reliability

- Use **short wires** (< 1 meter) for I2C
- **Pull-up resistors**: 4.7 kΩ typical (check PCA9685 board)
- **No 5V logic**: ESP32 I2C is 3.3V (PCA9685 should tolerate)

---

## Safety Rules Implemented

✅ **Angle Clamping**: All angles clamped to [0, 180] before conversion  
✅ **Channel Validation**: Commands for channels 0–9 only  
✅ **PWM Saturation**: Ticks clamped to [0, 4095]  
✅ **Error Tracking**: Errors reported to backend  
✅ **Graceful Disconnect**: Auto-reconnect on WebSocket failure  
✅ **No GPIO PWM**: All PWM through PCA9685 (I2C)  

---

## Next Steps

**STEP 4**: Create web dashboard with 10 sliders  
**STEP 5**: Define message contracts (JSON schema)

---

## Status Summary

| Component | Status | Lines | Language |
|-----------|--------|-------|----------|
| Arduino Firmware | ✅ Complete | 500 | C++11/Arduino |
| Servo Config Header | ✅ Included | (STEP 1) | C++ |
| WebSocket Handler | ✅ Complete | 150 | C++/JSON |
| PCA9685 Driver | ✅ Complete | 50 | C++ |
| I2C Manager | ✅ Complete | 30 | C++ |
| State Machine | ✅ Complete | 100 | C++ |
| Error Handling | ✅ Complete | 80 | C++ |

**STEP 3 is complete. Firmware ready for upload to ESP32-S3.**

---

## Verification Checklist

Before deployment:

- [ ] `servo_config.h` in same directory as `.ino` file
- [ ] Wi-Fi SSID/password configured
- [ ] Backend IP address correct
- [ ] Libraries installed (ArduinoWebSockets, ArduinoJson, Adafruit PWM)
- [ ] ESP32-S3 board selected in Arduino IDE
- [ ] USB cable connected to ESP32-S3
- [ ] External 6V servo power supply tested (no load)
- [ ] I2C wires checked (SDA=GPIO8, SCL=GPIO9)
- [ ] Common ground connected between ESP32 and servo GND
- [ ] Firmware compiles without errors
- [ ] Serial monitor opens at 115200 baud
- [ ] Wi-Fi connects within 30 seconds
- [ ] WebSocket connects to backend within 60 seconds

---

