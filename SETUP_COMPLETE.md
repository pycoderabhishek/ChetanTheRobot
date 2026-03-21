# 🚀 ESP32 ↔ Backend Complete Setup Guide

## ✅ What's Done
- [x] Backend server running on **10.44.185.246:8000**
- [x] mDNS advertiser active (Layer 1 discovery)
- [x] UDP broadcast listener active (Layer 2 discovery)
- [x] Database initialized
- [x] WebSocket endpoint ready at `/ws/{device_id}`

## 📋 Your System Information
- **PC IP Address**: `10.44.185.246`
- **Backend Port**: `8000`
- **Backend URL**: `http://10.44.185.246:8000`
- **WebSocket URL**: `ws://10.44.185.246:8000/ws/{device_id}`
- **Backend Status**: ✅ RUNNING

---

## 🔧 STEP 1: Arduino IDE Configuration

### Board Selection (CRITICAL)
1. Open **Arduino IDE**
2. Go to **Tools** → **Board Manager**
3. Search for "esp32" and install latest
4. Select: **Tools** → **Board** → **ESP32S3** → **ESP32S3 Dev Module**

### Recommended Settings
```
Board                : ESP32S3 Dev Module
USB CDC On Boot      : Enabled ✓
Upload Speed         : 2000000 (or 1500000 if errors)
CPU Frequency        : 240 MHz
Flash Mode           : QIO
Flash Size           : 16MB
Flash Freq           : 80 MHz
Partition Scheme     : Huge APP (3MB No OTA)
PSRAM                : OPI PSRAM
Core Debug Level     : None
```

### Required Libraries (Install via Library Manager)
- WebSocketsClient
- ArduinoJson
- ESP32Servo

---

## 📝 STEP 2: Verify/Update ESP32 Code Files

### Confirm Discovery Settings
Check **espcod/ESPCAMSERVO/discovery_config.h**:

```cpp
#define MDNS_SERVICE_TYPE       "_http"
#define MDNS_SERVICE_PROTO      "tcp"
#define MDNS_BACKEND_HOSTNAME   "chetan-robot"
#define MDNS_QUERY_TIMEOUT_MS   3000

#define UDP_DISCOVERY_PORT      54321
#define UDP_DISCOVERY_REQUEST   "CHETAN_ROBOT_DISCOVERY"
#define UDP_DISCOVERY_PREFIX    "CHETAN_ROBOT_BACKEND:"

#define DISCOVERY_DEFAULT_PORT  8000
```

**Note**: The mDNS hostname in your backend is advertised as `chetan-robot._http._tcp.local`, so ESP32 will find it automatically!

---

## 🔌 STEP 3: Flash ESP32

### 3.1 Connect ESP32 to USB
- Use **USB-C cable** (ESP32-S3 uses USB-C, not micro-USB)
- Check **Tools** → **Port** for available COM port

### 3.2 Flash the Code
1. Open **espcod/ESPCAMSERVO/ESPCAMSERVO.ino** in Arduino IDE
2. Click **✓ Verify** first (compile check)
3. Click **→ Upload** to flash

**Wait for message**: 
```
Hard resetting via RTS pin...
```

---

## 📡 STEP 4: WiFi Setup on ESP32

### 4.1 First Power-On
ESP32 will NOT find WiFi automatically. It enters **Layer 4 (AP Mode)**:

1. **Look for WiFi network**: `ChetanRobot_SETUP_XXYY`
   - (Where XXYY = last 2 bytes of ESP32 MAC address)
   
2. **Connect to it** (no password by default)

3. **Open browser**: `192.168.4.1`

4. **Configure in Captive Portal**:
   - WiFi SSID: `YOUR_HOME_WIFI_NAME`
   - WiFi Password: `YOUR_WIFI_PASSWORD`
   - Backend IP: `10.44.185.246`
   - Backend Port: `8000`
   - Click **Save**

### 4.2 Backend IP Reference
If your PC IP changes (e.g., after restart), you can reconfigure:
- Hold **GPIO0 (BOOT button)** for 3+ seconds while powered on
- ESP32 resets EEPROM and enters AP mode again
- Reconfigure with new IP

---

## 🎯 STEP 5: Verify Connection

### 5.1 Serial Monitor (Baud: 115200)
After WiFi setup, you should see:

```
========================================
  ESPCAM + SERVO INTEGRATED v1.0
  ESP32-S3 N16R8
========================================

[INIT] Attaching servos...
[INIT] Servo 0 -> GPIO 12 (OK)
[INIT] Servo 1 -> GPIO 13 (OK)
...
[INIT] All servos at home position (90 deg)

[DISC] Device ID: espcontroller_aabbcc
[DISC] Layer 3 — trying EEPROM IP...
[DISC] Layer 3 OK — backend at 10.44.185.246:8000

[WIFI] Discovery done. Backend: 10.44.185.246:8000  Device: espcontroller_aabbcc

[WS] Connecting to 10.44.185.246:8000 ...
[WS] WebSocket connected ✓

[AUDIO] Audio system initialized
[AUDIO] Wake threshold calibrated: 450
```

### 5.2 Backend Console (Terminal)
You should see:

```
[mDNS] ✓ Service advertised: chetan-robot._http._tcp.local
[UDP] ✓ Listening on 54321

INFO:     WebSocket accepted: espcontroller_aabbcc
[DEVICE_REGISTRY] Device registered: espcontroller_aabbcc
[HEARTBEAT] Device online: espcontroller_aabbcc
```

---

## 🛠️ Troubleshooting

### Issue: ESP32 Won't Connect to WiFi
**Solution**:
- Check WiFi SSID and password in AP config portal
- Ensure PC and ESP32 are on **same WiFi network**
- Restart ESP32

### Issue: WiFi Works but WebSocket Fails
**Symptoms**:
```
[WS] Connecting to 10.44.185.246:8000 ...
[WS] Connection failed, retrying...
```

**Check**:
1. Is backend still running? 
   ```powershell
   netstat -an | findstr "8000.*LISTENING"
   ```
2. Is firewall blocking port 8000?
   - Right-click antivirus/firewall
   - Add Python.exe to whitelist
3. Restart backend:
   - Kill terminal
   - Run again: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

### Issue: mDNS Discovery Fails
**ESP32 logs show**: `[DISC] Layer 1 — mDNS discovery ...` then nothing

**Check**:
1. Bonjour installed on Windows? (not required for UDP fallback)
2. Backend logs should show: `[mDNS] ✓ Service advertised`
3. Fallback: Use **Layer 2 (UDP broadcast)** instead - it's more reliable on Windows

---

## 📊 Testing Commands

### Test Backend Health
```powershell
# Check if running
netstat -an | findstr "8000"

# Test HTTP endpoint
Invoke-WebRequest http://localhost:8000 -UseBasicParsing
```

### Send Test Command to ESP32
Once connected, you can send servo commands via the dashboard:
- Open browser: `http://10.44.185.246:8000`
- Use dashboard to control servos

---

## 🎮 Next Steps

### Send Commands to ESP32
```json
// Example: Move servo
{
  "message_type": "command",
  "command_name": "handsup"
}

// Example: Text-to-speech
{
  "message_type": "audio_response",
  "audio_base64": "//NExAAkQgf..."
}
```

### Supported Commands
- `resetposition` - Reset all servos to home
- `handsup` - Raise both arms
- `headup` - Look up
- `headleft` - Turn head left
- `start_recording` - Begin audio recording

---

## 📞 Connection Summary

```
┌─────────────────────────────────────┐
│  Your Windows PC (10.44.185.246)    │
│  Backend: FastAPI + mDNS + UDP      │
│  Port: 8000                         │
└─────────────────────────────────────┘
            ↑           ↑
         mDNS &       UDP Broadcast
         WebSocket
            ↓           ↓
┌─────────────────────────────────────┐
│  ESP32-S3 CAM SERVO                 │
│  ID: espcontroller_aabbcc           │
│  Discovering backend automatically   │
└─────────────────────────────────────┘
```

---

## ✅ Verification Checklist

- [ ] Backend running: ✅ Port 8000 listening
- [ ] Arduino IDE set to ESP32S3 Dev Module
- [ ] ESP32 flashed with ESPCAMSERVO code
- [ ] Serial monitor shows startup messages
- [ ] ESP32 connected to home WiFi
- [ ] WebSocket connection established
- [ ] Backend console shows device registered
- [ ] LED/servo moves when command sent

---

**Ready to test? Follow STEP 4 next!** 🚀
