/**
 * eeprom_config.h
 * Persistent storage for backend IP/port using ESP32 NVS (Preferences library).
 * Survives power cycles and eliminates the need to re-run discovery every boot.
 */

#pragma once
#include <Preferences.h>

// NVS namespace and keys
#define PREF_NAMESPACE   "chetan"
#define PREF_KEY_HOST    "backend_host"
#define PREF_KEY_PORT    "backend_port"

class EEPROMConfig {
public:
    /**
     * Load saved backend host and port.
     * Returns true if a non-empty host was found.
     */
    static bool load(String& host, uint16_t& port) {
        Preferences prefs;
        prefs.begin(PREF_NAMESPACE, /* readOnly= */ true);
        host = prefs.getString(PREF_KEY_HOST, "");
        port = prefs.getUShort(PREF_KEY_PORT, 8000);
        prefs.end();
        return host.length() > 0;
    }

    /**
     * Persist backend host and port to NVS flash.
     */
    static void save(const String& host, uint16_t port) {
        Preferences prefs;
        prefs.begin(PREF_NAMESPACE, /* readOnly= */ false);
        prefs.putString(PREF_KEY_HOST, host);
        prefs.putUShort(PREF_KEY_PORT, port);
        prefs.end();
        Serial.printf("[EEPROM] Saved backend %s:%u\n", host.c_str(), port);
    }

    /**
     * Erase all stored configuration (factory reset).
     */
    static void clear() {
        Preferences prefs;
        prefs.begin(PREF_NAMESPACE, /* readOnly= */ false);
        prefs.clear();
        prefs.end();
        Serial.println("[EEPROM] Configuration cleared");
    }
};
