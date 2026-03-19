#ifndef EEPROM_CONFIG_H
#define EEPROM_CONFIG_H

/*
 * EEPROM_CONFIG.H
 *
 * Persistent storage for WiFi credentials and backend address using the
 * ESP32 Preferences library (backed by NVS flash).
 *
 * Stored keys (namespace "chetanrobot"):
 *   valid  (bool)   — true only after a successful save
 *   ssid   (String) — WiFi SSID
 *   pass   (String) — WiFi password
 *   bhost  (String) — backend hostname / IP
 *   bport  (UShort) — backend port
 */

#include <Preferences.h>
#include "discovery_config.h"

namespace EEPROMConfig {

// NVS namespace shared by all keys
static const char* NVS_NS = "chetanrobot";

// Persisted device configuration
struct Config {
    char     wifi_ssid[64];
    char     wifi_password[64];
    char     backend_host[64];
    uint16_t backend_port;
    bool     valid;

    Config() : backend_port(DISCOVERY_DEFAULT_PORT), valid(false) {
        memset(wifi_ssid,     0, sizeof(wifi_ssid));
        memset(wifi_password, 0, sizeof(wifi_password));
        memset(backend_host,  0, sizeof(backend_host));
    }
};

// Load stored config from NVS.  Returns a Config with valid=false if nothing
// has been saved yet.
inline Config load() {
    Config cfg;
    Preferences prefs;
    prefs.begin(NVS_NS, /*readOnly=*/true);
    cfg.valid        = prefs.getBool("valid", false);
    String ssid      = prefs.getString("ssid",  "");
    String pass      = prefs.getString("pass",  "");
    String bhost     = prefs.getString("bhost", "");
    cfg.backend_port = prefs.getUShort("bport", DISCOVERY_DEFAULT_PORT);
    prefs.end();

    strncpy(cfg.wifi_ssid,     ssid.c_str(),  sizeof(cfg.wifi_ssid)     - 1);
    strncpy(cfg.wifi_password, pass.c_str(),  sizeof(cfg.wifi_password) - 1);
    strncpy(cfg.backend_host,  bhost.c_str(), sizeof(cfg.backend_host)  - 1);
    cfg.wifi_ssid[sizeof(cfg.wifi_ssid)     - 1] = '\0';
    cfg.wifi_password[sizeof(cfg.wifi_password) - 1] = '\0';
    cfg.backend_host[sizeof(cfg.backend_host)   - 1] = '\0';
    return cfg;
}

// Persist a full config (WiFi + backend).
inline void save(const Config& cfg) {
    Preferences prefs;
    prefs.begin(NVS_NS, /*readOnly=*/false);
    prefs.putBool("valid",  true);
    prefs.putString("ssid",  cfg.wifi_ssid);
    prefs.putString("pass",  cfg.wifi_password);
    prefs.putString("bhost", cfg.backend_host);
    prefs.putUShort("bport", cfg.backend_port);
    prefs.end();
    Serial.printf("[EEPROM] Config saved: ssid='%s' backend='%s:%u'\n",
                  cfg.wifi_ssid, cfg.backend_host, cfg.backend_port);
}

// Update only the backend host and port (e.g. after mDNS / UDP discovery).
inline void saveBackendHost(const char* host, uint16_t port) {
    Preferences prefs;
    prefs.begin(NVS_NS, /*readOnly=*/false);
    prefs.putString("bhost", host);
    prefs.putUShort("bport", port);
    prefs.end();
    Serial.printf("[EEPROM] Backend updated: %s:%u\n", host, port);
}

// Erase all stored keys (triggers a fresh-start discovery on next boot).
inline void clear() {
    Preferences prefs;
    prefs.begin(NVS_NS, /*readOnly=*/false);
    prefs.clear();
    prefs.end();
    Serial.println("[EEPROM] All configuration cleared");
}

} // namespace EEPROMConfig

#endif // EEPROM_CONFIG_H
