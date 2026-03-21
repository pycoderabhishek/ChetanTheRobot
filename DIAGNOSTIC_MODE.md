# 🔧 WiFi AP Troubleshooting - DIAGNOSTIC MODE

## Problem
ESP32 shows AP startup messages but **Windows 11 doesn't see the WiFi network**

## Possible Causes
1. ❌ EEPROM has corrupted data (`YOUR_SSID`)
2. ❌ MAC address showing as `000000` (not initialized)
3. ❌ WiFi mode not properly set before AP starts
4. ❌ DNS/DHCP server not starting correctly

---

## 🛠️ Quick Fix - Use Diagnostic Sketch

### Step 1: Flash Diagnostic Version
```
1. Open DIAGNOSTIC.ino in Arduino IDE
   (Location: espcod/ESPCAMSERVO/DIAGNOSTIC.ino)

2. Click Upload

3. Open Serial Monitor (115200 baud)
```

### Step 2: Expected Output
```
========================================
  DIAGNOSTIC MODE - CLEAR & AP ONLY
  ESP32-S3 N16R8
========================================

[MAC] MAC Address: XX:XX:XX:XX:YY:ZZ
[DEVICE_ID] espcontroller_XXYYZZ

[EEPROM] Clearing all stored configuration...
[EEPROM] ✓ Cleared

[SETUP] Launching AP mode immediately...

[AP] softAP() returned: TRUE
[AP] SSID: 'ChetanRobot_SETUP_YYZZ'
[AP] Password: 'ChetanRobot123'
[AP] IP: 192.168.4.1
[AP] Connected stations: 0

=========================================
DIAGNOSTIC COMPLETE
=========================================

[INSTRUCTIONS]
1. Look for WiFi: 'ChetanRobot_SETUP_YYZZ'
2. Password: 'ChetanRobot123'
3. Connect from Windows 11
4. Open browser: http://192.168.4.1
```

### Step 3: Check Windows 11
1. **Settings** → **Network & internet** → **WiFi**
2. Click **Available networks**
3. Look for: **ChetanRobot_SETUP_YYZZ**
4. If you see it → Connect with password **ChetanRobot123**

---

## ✅ If Diagnostic Works

The problem was corrupted EEPROM. Now:

1. **Exit Diagnostic**: Upload full `ESPCAMSERVO.ino` again
2. **Flash Normal Code**: Do NOT hold BOOT button (we cleared EEPROM already)
3. **ESP32 will boot** and immediately show AP setup form
4. **Windows 11** can now connect

---

## ❌ If Still Can't See WiFi

### Check These:
1. **Correct board selected?**
   - Tools → Board → **ESP32S3 Dev Module**
   - Tools → Upload Speed → **2000000**

2. **Is compile successful?**
   - Check for errors in Serial Monitor
   - Look for `[AP] softAP() returned:`

3. **Is USB connection stable?**
   - Try different USB-C cable
   - Try different USB port

4. **Is WiFi on Windows enabled?**
   ```powershell
   # Check WiFi status
   netsh interface show interface
   
   # Should show WiFi as "Connected" or "Disconnected"
   ```

5. **Restart ESP32**:
   - Unplug USB
   - Wait 3 seconds
   - Plug back in
   - Wait 10 seconds

---

## 📋 Serial Output Interpretation

| Output | Meaning | Action |
|--------|---------|--------|
| `[AP] softAP() returned: TRUE` | ✅ AP started successfully | Windows should see network |
| `[AP] softAP() returned: FALSE` | ❌ AP failed to start | Check board selection, try restart |
| `[MAC] MAC Address: 00:00:00:00:00:00` | ❌ WiFi not initialized | Restart board with fresh code |
| `[AP] Connected stations: 1` | ✅ Device connected! | Open http://192.168.4.1 |

---

## 🚀 After WiFi Setup Works

Once you confirm AP appears in Windows 11:

1. **Go back to full ESPCAMSERVO.ino**
   - DON'T flash DIAGNOSTIC.ino again
   - Flash the regular code: `ESPCAMSERVO.ino`

2. **Configure WiFi**
   - ESP32 will show AP again
   - Windows can now auto-connect
   - Open 192.168.4.1
   - Enter home WiFi credentials

3. **Verify Connection**
   - Serial shows: `[WS] WebSocket connected ✓`
   - Backend console shows device registered

---

## 🆘 Still Having Issues?

Check these debug points:

```cpp
// In DIAGNOSTIC.ino, look for:
[MAC] MAC Address: ...          // Should show real MAC, not 00:00:00
[EEPROM] ✓ Cleared              // Confirms EEPROM was cleared  
[AP] softAP() returned: TRUE     // Confirms AP mode works
[AP] SSID: 'ChetanRobot_SETUP...  // Should match Windows network name
[AP] IP: 192.168.4.1             // Should be this exact IP
```

If MAC shows all zeros → Board not initialized properly → **Restart**

---

## 📞 Summary

| Task | Command |
|------|---------|
| **Flash Diagnostic** | Open DIAGNOSTIC.ino → Upload |
| **Check Serial** | Monitor at 115200 |
| **Look for WiFi** | Windows Settings → Available networks |
| **Connect** | "ChetanRobot_SETUP_XX" + password |
| **Flash Normal Code** | Upload ESPCAMSERVO.ino after confirming |

---

**Try diagnostic mode now - it will clarify the exact issue!** 🔍
