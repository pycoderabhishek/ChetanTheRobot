/**
 * eeprom_config.h
 * Persistent storage for backend hostname/IP using ESP32 NVS (via Preferences).
 * Survives reboots so the device can reconnect without re-running discovery.
 */

#pragma once

#include <Preferences.h>

#define PREF_NAMESPACE   "chetan"
#define PREF_KEY_HOST    "backend_host"
#define PREF_KEY_PORT    "backend_port"

class EEPROMConfig {
public:
  /**
   * Load stored backend host into `out_host` (max `host_size` bytes).
   * Returns true if a non-empty host was found.
   */
  static bool loadHost(char* out_host, size_t host_size, uint16_t* out_port = nullptr) {
    Preferences prefs;
    prefs.begin(PREF_NAMESPACE, /*readOnly=*/true);
    String host = prefs.getString(PREF_KEY_HOST, "");
    if (out_port) {
      *out_port = (uint16_t)prefs.getUInt(PREF_KEY_PORT, 8000);
    }
    prefs.end();

    if (host.length() == 0) return false;
    strlcpy(out_host, host.c_str(), host_size);
    return true;
  }

  /**
   * Save backend host (and optional port) to NVS.
   */
  static void saveHost(const char* host, uint16_t port = 8000) {
    Preferences prefs;
    prefs.begin(PREF_NAMESPACE, /*readOnly=*/false);
    prefs.putString(PREF_KEY_HOST, host);
    prefs.putUInt(PREF_KEY_PORT, port);
    prefs.end();
    Serial.printf("[EEPROM] Saved backend: %s:%u\n", host, port);
  }

  /**
   * Erase stored configuration (triggers re-discovery on next boot).
   */
  static void erase() {
    Preferences prefs;
    prefs.begin(PREF_NAMESPACE, /*readOnly=*/false);
    prefs.clear();
    prefs.end();
    Serial.println("[EEPROM] Configuration erased");
  }
};
