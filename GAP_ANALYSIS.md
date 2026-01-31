# AMHR-PD Server & Firmware - Gap Analysis and Setup Verification

**Date:** 2026-01-30  
**Status:** Pre-deployment Check

---

## Executive Summary

This document identifies gaps, errors, and configuration requirements before deploying the FastAPI backend server and uploading `.ino` firmware to ESP32 devices.

---

## 🔴 CRITICAL ISSUES

### 1. **Missing Python Dependencies**
**Severity:** HIGH - Server will not start  
**Issue:** Required packages not installed

```powershell
# Missing packages:
- uvicorn (WSGI server)
- websockets (WebSocket support)
- sqlalchemy (Database ORM)
- pydantic-settings (Configuration)
- python-dotenv (Environment variables)
```

**Fix:**
```powershell
cd D:\AMHR-PD\code\amhrpd\amhrpd-backend
pip install -r requirements.txt
```

**Verification:**
```powershell
pip show uvicorn sqlalchemy websockets pydantic-settings python-dotenv
```

---

### 2. **Firmware WiFi Credentials Not Configured**
**Severity:** HIGH - ESP devices cannot connect  
**Issue:** All 3 `.ino` files have placeholder WiFi credentials

**Files requiring configuration:**
- `ESPCAM.ino` (line 57-58)
- `ESPSERVO.ino` (line 26-27)
- `ESPWHEEL.ino` (line 34-35)

**Current (INVALID):**
```cpp
const char WIFI_SSID[] = "YOUR_SSID";
const char WIFI_PASSWORD[] = "YOUR_PASSWORD";
```

**Fix:** Replace with actual WiFi credentials:
```cpp
const char WIFI_SSID[] = "YourActualWiFiName";
const char WIFI_PASSWORD[] = "YourActualPassword";
```

⚠️ **All devices must connect to the SAME WiFi network as the server**

---

### 3. **Backend Host IP Address Hardcoded Incorrectly**
**Severity:** HIGH - ESPs will connect to wrong server  
**Issue:** All firmware files point to `10.218.125.93` (may be outdated)

**Files requiring update:**
- `ESPCAM.ino` (line 60)
- `ESPSERVO.ino` (line 29)
- `ESPWHEEL.ino` (line 37)

**Current:**
```cpp
const char BACKEND_HOST[] = "10.218.125.93";
```

**Fix:** Determine server's actual IP address:
```powershell
# Get your local IP address (Windows)
ipconfig | Select-String -Pattern "IPv4"
```

Then update all 3 files with the correct IP:
```cpp
const char BACKEND_HOST[] = "192.168.X.X";  // Your actual IP
```

---

## 🟡 MEDIUM PRIORITY ISSUES

### 4. **Arduino IDE and ESP32 Board Support Not Verified**
**Severity:** MEDIUM - Cannot upload firmware without this  
**Issue:** No verification that Arduino IDE is installed with ESP32 support

**Required:**
1. Arduino IDE 2.x or 1.8.x
2. ESP32 Board Definitions
3. Required libraries:
   - `WebSocketsClient` by Markus Sattler
   - `ArduinoJson` by Benoit Blanchon (v6.x)
   - `ESP32Servo` by Kevin Harrington (for ESPSERVO only)
   - `esp32-camera` (built-in for ESPCAM)

**Installation Steps:**
```
1. Open Arduino IDE
2. File → Preferences → Additional Boards Manager URLs:
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
3. Tools → Board → Boards Manager → Search "esp32" → Install
4. Sketch → Include Library → Manage Libraries → Install each library above
```

**Verification:**
- Tools → Board → ESP32 Arduino → Should show ESP32 boards

---

### 5. **Port Configuration Mismatch Risk**
**Severity:** MEDIUM - May cause connection failures  
**Issue:** Backend default port is 8000, firmware expects 8000

**Current Configuration:**
- Backend: `app/config.py` → PORT = 8000 ✓
- Firmware: `BACKEND_PORT = 8000` ✓

**Status:** ✓ Currently aligned, but if you change backend port, update firmware too

---

### 6. **Windows Firewall May Block WebSocket Connections**
**Severity:** MEDIUM - ESPs cannot connect to server  
**Issue:** Windows firewall may block incoming connections on port 8000

**Fix:**
```powershell
# Allow Python through firewall (run as Administrator)
New-NetFirewallRule -DisplayName "Python FastAPI Backend" -Direction Inbound -Program "C:\Path\To\python.exe" -Action Allow
```

Or manually:
1. Windows Defender Firewall → Advanced Settings
2. Inbound Rules → New Rule
3. Program → Browse to `python.exe`
4. Allow the connection → Apply to all profiles

---

## 🟢 LOW PRIORITY / WARNINGS

### 7. **Dashboard Static Files Present**
**Status:** ✓ GOOD - Dashboard exists and should load at `http://localhost:8000/`

**Files:**
- `app/dashboard/static/index.html` ✓
- `app/dashboard/static/app.js` ✓
- `app/dashboard/static/style.css` ✓

---

### 8. **Database File Exists**
**Status:** ✓ GOOD - `amhrpd.db` is present

**Location:** `D:\AMHR-PD\code\amhrpd\amhrpd-backend\amhrpd.db`

**Note:** If you want a fresh start, delete this file and let the server recreate it.

---

### 9. **Device ID Naming Consistency**
**Status:** ⚠️ REVIEW - Ensure device IDs match what dashboard expects

**Current Device IDs:**
- ESPCAM: `camcontroller`
- ESPSERVO: `servoscontroller`
- ESPWHEEL: `wheelcontroller`

**Backend expects:**
- Servo routes target device_type `"esp32s3"` ✓
- WebSocket blocks reserved IDs: `servo`, `dashboard`, `browser` ✓

**Recommendation:** Current setup is correct, but if you rename devices, update both firmware and backend expectations.

---

### 10. **Python Version Compatibility**
**Status:** ✓ GOOD - Python 3.14.2 installed

**Note:** FastAPI requires Python 3.7+, you have 3.14.2 ✓

**Issue:** `fastapi` version mismatch:
- `requirements.txt`: 0.104.1
- Installed: 0.128.0

This is usually fine (newer is compatible), but if issues occur:
```powershell
pip install fastapi==0.104.1 --force-reinstall
```

---

## 📋 PRE-LAUNCH CHECKLIST

### Backend Server

- [ ] **Install all Python dependencies**
  ```powershell
  cd D:\AMHR-PD\code\amhrpd\amhrpd-backend
  pip install -r requirements.txt
  ```

- [ ] **Verify backend starts without errors**
  ```powershell
  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
  Expected output:
  ```
  INFO:     Database initialized
  INFO:     Command router initialized
  INFO:     Heartbeat monitor started
  INFO:     Application startup complete.
  INFO:     Uvicorn running on http://0.0.0.0:8000
  ```

- [ ] **Test dashboard loads**
  - Open browser: `http://localhost:8000/`
  - Should see "AMHR-PD Dashboard"

- [ ] **Test API health endpoint**
  ```powershell
  curl http://localhost:8000/health
  ```
  Expected: `{"status":"ok", ...}`

- [ ] **Configure Windows Firewall** (if needed)

---

### ESP32 Firmware (All 3 Devices)

#### Configuration Updates Required:

- [ ] **Update WiFi credentials in all 3 files:**
  - `ESPCAM.ino` (line 57-58)
  - `ESPSERVO.ino` (line 26-27)
  - `ESPWHEEL.ino` (line 34-35)

- [ ] **Update backend host IP in all 3 files:**
  - Get your server's IP: `ipconfig`
  - Update `BACKEND_HOST` in all 3 files

- [ ] **Verify Arduino IDE setup:**
  - ESP32 board definitions installed
  - All required libraries installed (see Issue #4)

#### Upload Process (per device):

**ESPCAM (ESP32-S3-CAM):**
1. Arduino IDE → Tools → Board → ESP32 Arduino → ESP32-S3 Dev Module
2. Tools → Port → Select COM port
3. Open `ESPCAM.ino`
4. Click Upload
5. Monitor Serial at 115200 baud

**ESPSERVO (ESP32-S3):**
1. Arduino IDE → Tools → Board → ESP32-S3 Dev Module
2. Tools → Port → Select COM port
3. Open `ESPSERVO.ino`
4. Click Upload
5. Monitor Serial at 115200 baud

**ESPWHEEL (ESP32):**
1. Arduino IDE → Tools → Board → ESP32 Dev Module
2. Tools → Port → Select COM port
3. Open `ESPWHEEL.ino`
4. Click Upload
5. Monitor Serial at 115200 baud

---

### Post-Upload Verification

- [ ] **Check Serial Monitor for each device:**
  ```
  [WIFI] Connected!
  [WIFI] IP: 192.168.X.X
  [WS] Connected!
  [Device] Registered: <device_id> (<device_type>)
  [Heartbeat] Sent
  ```

- [ ] **Verify devices appear in dashboard**
  - `http://localhost:8000/` → Should show 3 devices online

- [ ] **Test REST API lists devices**
  ```powershell
  curl http://localhost:8000/api/devices
  ```
  Expected: JSON with 3 devices

- [ ] **Test sending a command**
  ```powershell
  # Test servo reset command
  curl -X POST "http://localhost:8000/servo/pose/reset"
  ```

---

## 🔧 RECOMMENDED IMPROVEMENTS

### 1. Environment Variables for Configuration
**Issue:** Sensitive data (WiFi, IPs) hardcoded in firmware

**Recommendation:** For backend, already using `.env` support (but no `.env` file exists)

**Create `.env` file:**
```bash
# D:\AMHR-PD\code\amhrpd\amhrpd-backend\.env
APP_NAME=AMHR-PD Backend
APP_VERSION=0.1.0
DEBUG=True
HOST=0.0.0.0
PORT=8000
WS_HEARTBEAT_INTERVAL=30
WS_HEARTBEAT_TIMEOUT=90
```

**For firmware:** Arduino doesn't support `.env` files natively, so hardcoding is acceptable for prototyping.

---

### 2. Add Server Startup Script
**Issue:** Manual server start is error-prone

**Create:** `start_server.bat`
```batch
@echo off
cd D:\AMHR-PD\code\amhrpd\amhrpd-backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
```

---

### 3. Add Requirements Verification Script
**Create:** `verify_setup.ps1`
```powershell
# Verify Python dependencies
Write-Host "Checking Python version..." -ForegroundColor Cyan
python --version

Write-Host "`nChecking required packages..." -ForegroundColor Cyan
$packages = @("fastapi", "uvicorn", "sqlalchemy", "websockets", "pydantic", "pydantic-settings")
foreach ($pkg in $packages) {
    pip show $pkg | Select-String "Name|Version"
}

Write-Host "`nChecking database..." -ForegroundColor Cyan
Test-Path "D:\AMHR-PD\code\amhrpd\amhrpd-backend\amhrpd.db"

Write-Host "`nChecking firmware files..." -ForegroundColor Cyan
$files = @("ESPCAM.ino", "ESPSERVO.ino", "ESPWHEEL.ino")
foreach ($f in $files) {
    $path = "D:\AMHR-PD\code\amhrpd\amhrpd-firmware\amhrpd_firmware\$f"
    Write-Host "$f exists: $(Test-Path $path)" -ForegroundColor $(if (Test-Path $path) {"Green"} else {"Red"})
}
```

---

## 📊 ARCHITECTURE VALIDATION

### ✓ Backend Structure
- ✓ Modular package layout
- ✓ WebSocket manager present
- ✓ Device registry implemented
- ✓ Database models defined
- ✓ REST API endpoints defined
- ✓ Dashboard static files present
- ✓ CORS middleware enabled (allows frontend)

### ✓ Firmware Structure
- ✓ 3 distinct device types (CAM, SERVO, WHEEL)
- ✓ WebSocket client implementation
- ✓ Registration messages defined
- ✓ Heartbeat mechanism implemented
- ✓ Command handlers present
- ✓ Hardware abstraction (pins, configs)

### ✓ Communication Protocol
- ✓ JSON message format consistent
- ✓ Message types defined: registration, heartbeat, status, command, command_ack
- ✓ Device type routing implemented
- ✓ Command acknowledgment flow present

---

## 🚀 DEPLOYMENT ORDER

1. **Install backend dependencies** (5 min)
2. **Start backend server** (verify it runs without errors)
3. **Get server IP address** (note it down)
4. **Update all 3 firmware files** (WiFi + IP)
5. **Upload ESPWHEEL first** (simplest, good test)
6. **Verify ESPWHEEL connects** (check Serial + Dashboard)
7. **Upload ESPSERVO** (test servo commands)
8. **Upload ESPCAM** (most complex, do last)
9. **Verify all 3 devices online**
10. **Test commands via dashboard/API**

---

## 📝 TESTING COMMANDS

### Backend Health
```powershell
curl http://localhost:8000/health
```

### List Devices
```powershell
curl http://localhost:8000/api/devices
```

### Send Test Command
```powershell
# Servo reset
curl -X POST "http://localhost:8000/servo/pose/reset"

# Generic command
curl -X POST "http://localhost:8000/api/command?device_type=esp32s3&command_name=handsup"
```

### Check Device History
```powershell
curl "http://localhost:8000/api/state-history/servoscontroller?limit=10"
```

---

## ⚠️ POTENTIAL RUNTIME ISSUES

### Issue: "Module not found" errors
**Cause:** Missing Python packages  
**Fix:** Run `pip install -r requirements.txt`

### Issue: "Database locked" errors
**Cause:** Multiple server instances  
**Fix:** Kill all Python processes, restart server once

### Issue: ESP won't connect to WiFi
**Cause:** Wrong credentials, 5GHz WiFi (ESP32 only supports 2.4GHz)  
**Fix:** Use 2.4GHz network, verify credentials

### Issue: ESP connects to WiFi but not WebSocket
**Cause:** Wrong IP address, firewall blocking, server not running  
**Fix:** Verify IP, check firewall, ensure server is running

### Issue: Commands not reaching ESP
**Cause:** Device not registered, wrong device_type in command  
**Fix:** Check device appears in `/api/devices`, match device_type exactly

---

## ✅ FINAL STATUS

**Server Ready:** ⚠️ NO - Missing dependencies  
**Firmware Ready:** ⚠️ NO - Config required  
**Database Ready:** ✓ YES  
**Dashboard Ready:** ✓ YES  
**Architecture Valid:** ✓ YES  

**Next Steps:**
1. Install Python dependencies
2. Configure firmware WiFi/IP
3. Start server
4. Upload firmware
5. Test system

---

## 📚 REFERENCE DOCUMENTATION

- Backend API: See `app/main.py` for all endpoints
- Firmware Guide: `amhrpd-firmware/FIRMWARE_GUIDE.md`
- Message Protocol: `docs/MESSAGE_CONTRACTS.md`
- Project Status: `docs/PROJECT_STATUS.md`

---

**Analysis Complete** - Address critical issues #1-3 before deployment.
