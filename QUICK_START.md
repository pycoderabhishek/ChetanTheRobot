# AMHR-PD Quick Start Guide

**Date:** 2026-01-30  
**Status:** ✅ Ready for Deployment

---

## ✅ FIXES COMPLETED

### 1. Architecture Issue Resolved
- **Problem:** ESP devices had conflicting HTTP servers (port 80)
- **Solution:** Removed all ESP HTTP servers
- **Result:** Clean architecture - ESPs communicate ONLY via WebSocket to FastAPI

### 2. FastAPI Server Status
- **Status:** ✅ Running correctly on port 8000
- **Health Check:** http://localhost:8000/health returns `{"status":"ok"}`
- **Dashboard:** Available at http://localhost:8000/

---

## 🚀 NEXT STEPS TO DEPLOY

### Step 1: Verify FastAPI Server is Running

```powershell
# Check if server is running
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status":"ok","timestamp":"2026-01-30T...","app":"AMHR-PD Backend","version":"0.1.0"}
```

**If server is NOT running, start it:**
```powershell
cd D:\AMHR-PD\code\amhrpd\amhrpd-backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Step 2: Open Dashboard in Browser

```
http://localhost:8000/
```

or 

```
http://10.83.60.93:8000/
```

You should see the AMHR-PD dashboard interface.

---

### Step 3: Configure WiFi Credentials in Firmware

**⚠️ MANUAL ACTION REQUIRED**

Edit these 3 firmware files and replace WiFi credentials:

1. `D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\ESPSERVO.ino`
2. `D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\ESPWHEEL.ino`
3. `D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\ESPCAM.ino`

**Find these lines (around line 26-35 in each file):**
```cpp
const char WIFI_SSID[] = "YOUR_SSID";  // TODO: Replace
const char WIFI_PASSWORD[] = "YOUR_PASSWORD";  // TODO: Replace
```

**Replace with your actual WiFi:**
```cpp
const char WIFI_SSID[] = "YourActualWiFiName";
const char WIFI_PASSWORD[] = "YourActualPassword";
```

**IMPORTANT:** Use 2.4GHz WiFi (ESP32 doesn't support 5GHz)

---

### Step 4: Verify Backend Host IP is Correct

All 3 firmware files are already configured to connect to:
```cpp
const char BACKEND_HOST[] = "10.83.60.93";  // Your current server IP
```

**Verify this is still your computer's IP:**
```powershell
ipconfig | Select-String -Pattern "IPv4"
```

If your IP changed, update `BACKEND_HOST` in all 3 firmware files.

---

### Step 5: Upload Firmware to ESP32 Devices

Using Arduino IDE:

#### 5.1 ESPWHEEL (Simplest - Upload First)
1. Open `ESPWHEEL.ino`
2. Tools → Board → ESP32 Arduino → **ESP32 Dev Module**
3. Tools → Port → Select your COM port
4. Click **Upload** button
5. Open Serial Monitor (115200 baud)

**Expected Serial Output:**
```
========================================
  AMHR-PD Wheel Controller v1.0
  ESP32 + L298N Motor Driver
========================================

[INIT] Motors initialized
[WIFI] Connecting...
[WIFI] Connected! IP: 192.168.X.X
[WS] Connecting to backend...
[WS] Connected and registered
[Heartbeat] Sent
```

---

#### 5.2 ESPSERVO
1. Open `ESPSERVO.ino`
2. Tools → Board → ESP32 Arduino → **ESP32-S3 Dev Module**
3. Tools → Port → Select your COM port
4. Click **Upload** button
5. Open Serial Monitor (115200 baud)

**Expected Serial Output:**
```
========================================
  AMHR-PD Servo Controller v2.0
  ESP32Servo Library Edition
========================================

[INIT] Attaching servos...
[INIT] Servo 0 -> GPIO 4 (OK)
[INIT] Servo 1 -> GPIO 5 (OK)
...
[INIT] All servos initialized at home position (90 deg)
[WIFI] Connecting...
[WIFI] Connected! IP: 192.168.X.X
[WS] Connecting to backend...
[WS] Connected and registered
[Heartbeat] Sent
```

---

#### 5.3 ESPCAM
1. Open `ESPCAM.ino`
2. Tools → Board → ESP32 Arduino → **ESP32-S3 Dev Module**
3. Tools → Port → Select your COM port
4. Click **Upload** button
5. Open Serial Monitor (115200 baud)

**Expected Serial Output:**
```
========================================
  AMHR-PD Camera Controller v1.0
  ESP32-S3 CAM + Audio
========================================

[CAM] PSRAM found - using VGA (or QVGA)
[CAM] Initialized successfully
[AUDIO] I2S initialized
[WIFI] Connecting...
[WIFI] Connected! IP: 192.168.X.X
[WS] Connecting to backend...
[WS] Connected and registered
[Heartbeat] Sent
```

---

### Step 6: Verify All Devices Connected

#### 6.1 Check Dashboard
Open browser: http://localhost:8000/

You should see all 3 devices listed as "online":
- `servoscontroller` (esp32s3)
- `wheelcontroller` (esp32)
- `camcontroller` (esp32s3cam)

---

#### 6.2 Check API
```powershell
curl http://localhost:8000/api/devices
```

**Expected Response:**
```json
{
  "total": 3,
  "devices": [
    {
      "device_id": "servoscontroller",
      "device_type": "esp32s3",
      "is_online": true,
      ...
    },
    {
      "device_id": "wheelcontroller",
      "device_type": "esp32",
      "is_online": true,
      ...
    },
    {
      "device_id": "camcontroller",
      "device_type": "esp32s3cam",
      "is_online": true,
      ...
    }
  ]
}
```

---

### Step 7: Test Sending Commands

#### Test Servo Commands
```powershell
# Reset servo positions
curl -X POST "http://localhost:8000/servo/pose/reset"

# Hands up pose
curl -X POST "http://localhost:8000/servo/pose/handsup"

# Head left
curl -X POST "http://localhost:8000/servo/pose/headleft"
```

#### Test Wheel Commands
```powershell
# Send generic command
curl -X POST "http://localhost:8000/api/command?device_type=esp32&command_name=forward" `
  -H "Content-Type: application/json" `
  -d '{"speed": 200}'

# Stop motors
curl -X POST "http://localhost:8000/api/command?device_type=esp32&command_name=stop"
```

#### Test Camera Commands
```powershell
# Start streaming
curl -X POST "http://localhost:8000/api/command?device_type=esp32s3cam&command_name=start_stream"

# Capture frame
curl -X POST "http://localhost:8000/api/command?device_type=esp32s3cam&command_name=capture"

# Flash on
curl -X POST "http://localhost:8000/api/command?device_type=esp32s3cam&command_name=flash_on"
```

---

## 📊 SYSTEM STATUS

| Component | Status | Notes |
|-----------|--------|-------|
| Python Dependencies | ✅ Installed | All packages present |
| FastAPI Server | ✅ Running | Port 8000, responds to health check |
| Dashboard | ✅ Ready | Accessible at localhost:8000 |
| Database | ✅ Ready | amhrpd.db initialized |
| Backend IP Config | ✅ Updated | Set to 10.83.60.93 |
| ESP HTTP Servers | ✅ Removed | Architecture conflict fixed |
| WiFi Config | ⚠️ Manual | YOU MUST ADD WiFi credentials |
| Firmware Upload | ⏳ Pending | After WiFi config complete |

---

## 🔍 TROUBLESHOOTING

### Issue: ESP won't connect to WiFi
**Solutions:**
- Verify WiFi credentials are correct
- Make sure using 2.4GHz WiFi (not 5GHz)
- Check WiFi allows new devices to connect

### Issue: ESP connects to WiFi but not WebSocket
**Solutions:**
- Verify `BACKEND_HOST` IP is correct
- Check Windows Firewall isn't blocking port 8000
- Ensure FastAPI server is running

### Issue: Commands not reaching ESP
**Solutions:**
- Check device appears in `/api/devices` as "online"
- Verify `device_type` in command matches exactly
- Check Serial Monitor for error messages

### Issue: FastAPI server won't start - "Address already in use"
**Solution:**
- Server is already running! Check `curl http://localhost:8000/health`
- If you need to restart, kill process:
  ```powershell
  netstat -ano | Select-String "8000"  # Find PID
  Stop-Process -Id <PID>  # Kill it
  ```

---

## 📝 KEY FILES

### Documentation
- **This Guide:** `QUICK_START.md`
- **Architecture Fix:** `ARCHITECTURE_FIX.md`
- **Gap Analysis:** `GAP_ANALYSIS.md`
- **Setup Status:** `SETUP_STATUS.md`
- **WiFi Instructions:** `WIFI_CONFIG_INSTRUCTIONS.txt`

### Backend
- **Main Server:** `amhrpd-backend/app/main.py`
- **Configuration:** `amhrpd-backend/app/config.py`
- **Dashboard:** `amhrpd-backend/app/dashboard/static/`

### Firmware
- **Servo Controller:** `amhrpd-firmware/amhrpd_firmware/ESPSERVO.ino`
- **Wheel Controller:** `amhrpd-firmware/amhrpd_firmware/ESPWHEEL.ino`
- **Camera Controller:** `amhrpd-firmware/amhrpd_firmware/ESPCAM.ino`

---

## ✅ WHAT'S BEEN FIXED

1. ✅ **Python dependencies installed** - All required packages present
2. ✅ **FastAPI server verified working** - Health endpoint responds
3. ✅ **Backend IP updated** - Set to 10.83.60.93 in all firmware
4. ✅ **ESP HTTP servers removed** - Architecture conflict resolved
5. ✅ **Documentation created** - Complete guides for deployment

## ⚠️ WHAT YOU NEED TO DO

1. **Configure WiFi credentials** in all 3 firmware files (5 minutes)
2. **Upload firmware** to ESP32 devices using Arduino IDE (15 minutes)
3. **Verify devices connect** via Serial Monitor and Dashboard (5 minutes)
4. **Test commands** to ensure everything works (10 minutes)

---

## 🎉 YOU'RE READY!

Once you add WiFi credentials and upload firmware, your robotic system will be fully operational with:

- ✅ Centralized control via FastAPI
- ✅ Real-time monitoring via web dashboard
- ✅ Clean WebSocket-based architecture
- ✅ Command logging and history
- ✅ Device status tracking

**Total Setup Time:** ~35 minutes

**Questions?** Refer to `ARCHITECTURE_FIX.md` for detailed explanations.
