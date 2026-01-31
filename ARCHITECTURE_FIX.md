# AMHR-PD Architecture Fix - HTTP Server Conflict Resolution

**Date:** 2026-01-30  
**Status:** ✅ FIXED

---

## ❌ PROBLEM IDENTIFIED

Your ESP32 firmware files had **conflicting HTTP WebServers** running on port 80 inside each ESP device. This was causing architecture confusion and potentially preventing your FastAPI server from functioning correctly.

### Issues Found:
1. **ESPSERVO.ino** - Had HTTP server on port 80 with endpoints `/`, `/move`, `/status`, `/test`
2. **ESPWHEEL.ino** - Had HTTP server on port 80 with endpoints `/`, `/forward`, `/backward`, `/left`, `/right`, `/stop`, `/status`
3. **ESPCAM.ino** - Had HTTP server on port 80 with endpoints `/`, `/capture`, `/stream`, `/flash`, `/status`, `/beep`

### Why This Was Wrong:
- **Architectural Conflict**: You have a centralized FastAPI dashboard (port 8000) designed to command and monitor all devices
- **Duplicate Functionality**: The ESP HTTP servers provided the same functionality that should be routed through FastAPI
- **Confusion**: Two different ways to control devices (direct HTTP to ESP vs. FastAPI WebSocket commands)
- **Management Nightmare**: Can't centrally log, monitor, or secure device operations when devices have their own HTTP APIs

---

## ✅ CORRECT ARCHITECTURE

```
┌─────────────────────────────────────────┐
│     FastAPI Backend (Port 8000)         │
│  ┌─────────────────────────────────┐   │
│  │  Dashboard (Web UI)              │   │
│  │  - Device monitoring             │   │
│  │  - Command interface             │   │
│  │  - Real-time status              │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  REST API                        │   │
│  │  - /api/devices                  │   │
│  │  - /api/command                  │   │
│  │  - /servo/pose/*                 │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  WebSocket Server                │   │
│  │  - /ws/{device_id}               │   │
│  │  - Device registration           │   │
│  │  - Command routing               │   │
│  │  - Status updates                │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
              ▲  ▲  ▲
              │  │  │
         WebSocket Connections
              │  │  │
    ┌─────────┘  │  └─────────┐
    │            │             │
    │            │             │
┌───▼───┐    ┌───▼───┐    ┌───▼───┐
│ESP32  │    │ESP32  │    │ESP32  │
│SERVO  │    │WHEEL  │    │ CAM   │
│       │    │       │    │       │
│(NO    │    │(NO    │    │(NO    │
│HTTP)  │    │HTTP)  │    │HTTP)  │
└───────┘    └───────┘    └───────┘
```

### Communication Flow:
1. **Dashboard → FastAPI** - User clicks button in web UI
2. **FastAPI → ESP (WebSocket)** - FastAPI sends command via WebSocket
3. **ESP executes command** - Device performs action (move servo, drive wheels, capture image)
4. **ESP → FastAPI (WebSocket)** - Device sends acknowledgment & status update
5. **FastAPI → Dashboard** - Dashboard shows updated device status

---

## 🔧 CHANGES MADE

### 1. ESPSERVO.ino
**Removed:**
- `#include <WebServer.h>`
- `WebServer server(80);` declaration
- `setup_http_server()` function (54 lines)
- `server.handleClient()` from loop

**Result:** Servo controller now ONLY communicates via WebSocket to FastAPI

---

### 2. ESPWHEEL.ino
**Removed:**
- `#include <WebServer.h>`
- `WebServer server(80);` declaration
- `setup_http_server()` function (52 lines)
- `server.handleClient()` from loop

**Result:** Wheel controller now ONLY communicates via WebSocket to FastAPI

---

### 3. ESPCAM.ino
**Removed:**
- `#include <WebServer.h>`
- `WebServer server(80);` declaration
- `setup_http_server()` function (84 lines)
- `server.handleClient()` from loop

**Result:** Camera controller now ONLY communicates via WebSocket to FastAPI

---

## 📋 HOW TO CONTROL DEVICES NOW

### ❌ OLD WAY (Removed - DO NOT USE):
```bash
# Direct HTTP to ESP (NO LONGER WORKS)
curl http://192.168.1.100/move?ch=0&angle=90
curl http://192.168.1.101/forward?speed=200
curl http://192.168.1.102/capture
```

### ✅ NEW WAY (Use This):

#### Via FastAPI REST API:
```powershell
# Send command to servo controller
curl -X POST "http://10.83.60.93:8000/servo/pose/handsup"

# Send generic command
curl -X POST "http://10.83.60.93:8000/api/command?device_type=esp32s3&command_name=resetposition"

# Get device status
curl "http://10.83.60.93:8000/api/devices"

# Get specific device
curl "http://10.83.60.93:8000/api/devices/servoscontroller"
```

#### Via Dashboard Web UI:
1. Open browser: `http://10.83.60.93:8000/` or `http://localhost:8000/`
2. View all connected devices
3. Click buttons to send commands
4. Monitor real-time status updates

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Start FastAPI Backend
```powershell
cd D:\AMHR-PD\code\amhrpd\amhrpd-backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO: Database initialized
INFO: Command router initialized
INFO: Heartbeat monitor started
INFO: Servo controller routes registered
INFO: Static files mounted from D:\AMHR-PD\code\amhrpd\amhrpd-backend\app\dashboard\static
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
```

---

### Step 2: Verify Dashboard Loads
Open browser: `http://localhost:8000/`

**Expected:** See "AMHR-PD Dashboard" with device list

---

### Step 3: Configure WiFi in Firmware
Edit these 3 files with your WiFi credentials:
- `D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\ESPSERVO.ino`
- `D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\ESPWHEEL.ino`
- `D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\ESPCAM.ino`

Find lines:
```cpp
const char WIFI_SSID[] = "YOUR_SSID";  // TODO: Replace with your WiFi name
const char WIFI_PASSWORD[] = "YOUR_PASSWORD";  // TODO: Replace with your WiFi password
```

Replace with actual credentials (use 2.4GHz WiFi only).

---

### Step 4: Upload Corrected Firmware
Using Arduino IDE, upload firmware to each ESP32 device:

1. **ESPWHEEL** (simplest, test first)
   - Board: ESP32 Dev Module
   - Upload `ESPWHEEL.ino`
   - Monitor Serial (115200 baud)

2. **ESPSERVO**
   - Board: ESP32-S3 Dev Module
   - Upload `ESPSERVO.ino`
   - Monitor Serial (115200 baud)

3. **ESPCAM**
   - Board: ESP32-S3 Dev Module
   - Upload `ESPCAM.ino`
   - Monitor Serial (115200 baud)

---

### Step 5: Verify Connection

**Serial Monitor Output (Expected):**
```
========================================
  AMHR-PD [Device] Controller v1.0/2.0
========================================

[WIFI] Connecting...
[WIFI] Connected! IP: 192.168.X.X
[WS] Connecting to backend...
[WS] Connected and registered
[Heartbeat] Sent
```

**Dashboard Check:**
- Refresh `http://localhost:8000/`
- All 3 devices should show as "online"

**API Check:**
```powershell
curl http://localhost:8000/api/devices
```
Expected: JSON with 3 devices (servoscontroller, wheelcontroller, camcontroller)

---

## ✅ BENEFITS OF THIS FIX

### 1. **Centralized Control**
- All device commands go through FastAPI
- Single source of truth for device state

### 2. **Better Monitoring**
- Dashboard shows real-time status of all devices
- Command history logged in database
- Connection logs tracked

### 3. **Security**
- No direct HTTP access to ESP devices
- FastAPI can implement authentication/authorization
- Devices hidden behind WebSocket connection

### 4. **Scalability**
- Easy to add new devices
- Standardized communication protocol
- FastAPI handles load balancing

### 5. **Debugging**
- All communication logged in one place
- Easy to trace command flow
- Database stores historical data

---

## 🔍 VERIFICATION CHECKLIST

After uploading corrected firmware, verify:

- [ ] FastAPI server starts without errors
- [ ] Dashboard loads at `http://localhost:8000/`
- [ ] All 3 ESP devices connect via WebSocket
- [ ] Serial monitors show "WS Connected and registered"
- [ ] Dashboard shows all devices as "online"
- [ ] `/api/devices` endpoint returns 3 devices
- [ ] Can send commands via REST API (e.g., `/servo/pose/reset`)
- [ ] Devices execute commands and send acknowledgments
- [ ] No HTTP servers running on ESP devices (port 80)

---

## 📝 RELATED FILES

- **Backend:** `D:\AMHR-PD\code\amhrpd\amhrpd-backend\app\main.py`
- **Firmware (Servo):** `D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\ESPSERVO.ino`
- **Firmware (Wheel):** `D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\ESPWHEEL.ino`
- **Firmware (Camera):** `D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\ESPCAM.ino`
- **Gap Analysis:** `D:\AMHR-PD\code\amhrpd\GAP_ANALYSIS.md`
- **Setup Status:** `D:\AMHR-PD\code\amhrpd\SETUP_STATUS.md`

---

## 🎯 SUMMARY

**Problem:** ESP devices had conflicting HTTP servers (port 80) duplicating FastAPI functionality  
**Solution:** Removed all ESP HTTP servers - devices now communicate ONLY via WebSocket to FastAPI  
**Result:** Clean architecture with centralized control, monitoring, and logging through FastAPI dashboard  

**Status:** ✅ Ready for deployment after WiFi configuration
