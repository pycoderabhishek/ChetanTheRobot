# 🔐 ESP32 WiFi Setup - Windows 11 Compatible

## What Changed
✅ **AP Password Added**: ESP32 now broadcasts with a password (Windows 11 compatible)

### New AP Credentials
```
SSID:     ChetanRobot_SETUP_XXYY
Password: ChetanRobot123
```

---

## 📱 How to Connect (Windows 11)

### Step 1: Flash Updated Code
1. Open Arduino IDE
2. Open **espcod/ESPCAMSERVO/ESPCAMSERVO.ino**
3. Click **Upload** (this compiles with the new AP password)

### Step 2: Power On ESP32
- Plug in USB-C cable
- Wait ~5 seconds for boot

### Step 3: Windows 11 WiFi Settings
1. **Settings** → **Network & internet** → **WiFi**
2. Click **Available networks**
3. Look for: **ChetanRobot_SETUP_XX** (where XX = ESP32's MAC last 2 bytes)
4. Click it → **Connect**
5. Enter password: **ChetanRobot123**
6. ✅ Connected!

### Step 4: Open Captive Portal
- Browser should **auto-open** to `192.168.4.1`
- If not, manually visit: **http://192.168.4.1**
- You'll see the **ChetanRobot Setup** form

### Step 5: Configure Backend
Fill in the form:

| Field | Value |
|-------|-------|
| WiFi SSID | Your home WiFi name |
| WiFi Password | Your home WiFi password |
| Backend IP | **10.44.185.246** |
| Backend Port | **8000** |

Click **Save & Connect**

### Step 6: Monitor Serial Output
1. Open Arduino IDE → **Tools** → **Serial Monitor**
2. Baud: **115200**
3. You should see:
```
[DISC] Layer 4 — launching AP mode ...
[AP] Server started at 192.168.4.1
[AP] WiFi SSID: ChetanRobot_SETUP_XX
[AP] AP Password: ChetanRobot123

-> User configures on captive portal at 192.168.4.1

[DISC] WiFi credentials saved to EEPROM
[WIFI] Connecting to YOUR_HOME_WIFI...
[WIFI] Connected! IP: 192.168.x.x

[DISC] Layer 1 — mDNS discovery ...
[mDNS] Found backend at 10.44.185.246:8000

[WS] Connecting to 10.44.185.246:8000 ...
[WS] WebSocket connected ✓
```

---

## 🔑 Password Details

| Parameter | Value |
|-----------|-------|
| Minimum length | 8 characters |
| Password | ChetanRobot123 |
| Encryption | WPA2 |
| Windows 11 support | ✅ Yes |

---

## 📋 Updated Credentials

### ESP32 AP (Setup Mode)
```
SSID:        ChetanRobot_SETUP_XXYY
Password:    ChetanRobot123
IP:          192.168.4.1
Port:        80
```

### Your Backend
```
IP:          10.44.185.246
Port:        8000
mDNS:        chetan-robot._http._tcp.local
```

### ESP32 After WiFi Setup
```
IP:          192.168.x.y (from your home WiFi)
Connected to: Your home WiFi
Backend:     10.44.185.246:8000
WebSocket:   ws://10.44.185.246:8000/ws/espcontroller_XXYY
```

---

## ❓ If Windows Still Can't Connect

### Try These:
1. **Restart Windows WiFi**:
   ```powershell
   ipconfig /release
   ipconfig /renew
   ```

2. **Restart ESP32**:
   - Unplug USB cable
   - Wait 3 seconds
   - Plug back in
   - Wait for AP to appear (~5 seconds)

3. **Check Serial Monitor** for AP startup:
   ```
   [AP] WiFi SSID: ChetanRobot_SETUP_XX
   [AP] AP Password: ChetanRobot123
   [AP] Server started at 192.168.4.1
   ```

4. **Manual IP Configuration**:
   - If auto-portal doesn't open, go to:
   - **Settings** → **WiFi** → **ChetanRobot_SETUP_XX** → **Properties**
   - Set IP to static: `192.168.4.100`
   - Gateway: `192.168.4.1`
   - Then visit: `http://192.168.4.1`

---

## ✅ Verification

After ESP32 connects to your home WiFi:

### Check Backend Console
```
INFO:     WebSocket accepted: espcontroller_aabbcc
[DEVICE_REGISTRY] Device registered: espcontroller_aabbcc
[mDNS] Service advertised...
```

### Check ESP32 Serial Monitor
```
[WS] WebSocket connected ✓
[AUDIO] Audio system initialized
[INIT] All servos at home position (90 deg)
```

---

## ⏭️ Next Steps
1. Re-flash ESP32 with updated code
2. Connect to AP using Windows 11 WiFi settings
3. Configure backend IP and WiFi credentials
4. Monitor serial output for connection confirmation
5. Test servo commands via dashboard

---

**Everything is now Windows 11 compatible!** 🎉
