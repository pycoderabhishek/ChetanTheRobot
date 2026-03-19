#ifndef WIFI_DISCOVERY_H
#define WIFI_DISCOVERY_H

/*
 * WIFI_DISCOVERY.H  —  4-layer WiFi + backend auto-discovery orchestrator
 *
 * Call discovery_begin() once from setup().  It blocks until a backend is
 * found (or the user configures one via the captive portal) and then
 * populates the three read-only accessors:
 *
 *   discovery_get_host()       — backend IP / hostname string
 *   discovery_get_port()       — backend port (uint16_t)
 *   discovery_get_device_id()  — unique "espcontroller_AABBCC" string
 *
 * Discovery order:
 *   1. Load EEPROM → connect to stored WiFi
 *   2. Ping stored backend IP  (Layer 3 — fastest)
 *   3. mDNS query              (Layer 1)
 *   4. UDP broadcast           (Layer 2)
 *   5. AP mode / captive portal (Layer 4 — fallback, loops until configured)
 *
 * Hold GPIO0 (BOOT button) at power-on for DISCOVERY_RESET_HOLD_MS to erase
 * EEPROM and force Layer 4 (fresh-start re-configuration).
 */

#include <WiFi.h>
#include "discovery_config.h"
#include "eeprom_config.h"
#include "mdns_handler.h"
#include "udp_discovery.h"
#include "ap_mode_server.h"

// ── Module-level state (populated by discovery_begin) ─────────────────────────
static String    _disc_backend_host;
static uint16_t  _disc_backend_port = DISCOVERY_DEFAULT_PORT;
static String    _disc_device_id;
static EEPROMConfig::Config _disc_saved_cfg;

// ── Internal helpers ──────────────────────────────────────────────────────────

// Build a unique device ID from the last 3 bytes of the MAC address.
// Format: "espcontroller_AABBCC" — 21 chars including null terminator.
// Buffer is 32 bytes to align to a power-of-two boundary.
static String _disc_make_device_id() {
    uint8_t mac[6];
    WiFi.macAddress(mac);
    char id[32];
    snprintf(id, sizeof(id), "espcontroller_%02x%02x%02x",
             mac[3], mac[4], mac[5]);
    return String(id);
}

// Attempt a WiFi station connection using the given credentials.
// Blocks for up to DISCOVERY_WIFI_TIMEOUT_MS, then returns the result.
static bool _disc_wifi_connect(const char* ssid, const char* password) {
    if (!ssid || strlen(ssid) == 0) return false;

    Serial.printf("[WIFI] Connecting to '%s' ...\n", ssid);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, (password && strlen(password) > 0) ? password : nullptr);

    unsigned long deadline = millis() + DISCOVERY_WIFI_TIMEOUT_MS;
    while (WiFi.status() != WL_CONNECTED) {
        if (millis() > deadline) {
            WiFi.disconnect(true);
            Serial.println("[WIFI] Connection timed out");
            return false;
        }
        Serial.print(".");
        delay(250);
    }
    Serial.printf("\n[WIFI] Connected! IP: %s\n",
                  WiFi.localIP().toString().c_str());
    return true;
}

// Open a TCP connection to host:port to verify the backend is reachable.
// Timeout is 2 seconds to keep discovery fast.
static bool _disc_ping_backend(const String& host, uint16_t port) {
    if (host.isEmpty()) return false;
    WiFiClient client;
    client.setTimeout(2000);
    bool ok = client.connect(host.c_str(), port);
    client.stop();
    return ok;
}

// Run layers 3 → 1 → 2 of the discovery stack (assumes WiFi is already up).
// Returns true and updates _disc_backend_host / _disc_backend_port on success.
static bool _disc_find_backend() {
    uint16_t found_port = DISCOVERY_DEFAULT_PORT;

    // ── Layer 3: EEPROM stored IP (fastest) ─────────────────────────────────
    if (strlen(_disc_saved_cfg.backend_host) > 0) {
        Serial.printf("[DISC] Layer 3 — trying EEPROM IP: %s:%u\n",
                      _disc_saved_cfg.backend_host,
                      _disc_saved_cfg.backend_port);
        if (_disc_ping_backend(_disc_saved_cfg.backend_host,
                               _disc_saved_cfg.backend_port)) {
            _disc_backend_host = _disc_saved_cfg.backend_host;
            _disc_backend_port = _disc_saved_cfg.backend_port;
            Serial.printf("[DISC] Layer 3 OK — backend at %s:%u\n",
                          _disc_backend_host.c_str(), _disc_backend_port);
            return true;
        }
        Serial.println("[DISC] Layer 3 — EEPROM IP not reachable");
    }

    // ── Layer 1: mDNS ────────────────────────────────────────────────────────
    Serial.println("[DISC] Layer 1 — mDNS discovery ...");
    String mdns_ip = MDNSHandler::resolve(found_port);
    if (!mdns_ip.isEmpty()) {
        _disc_backend_host = mdns_ip;
        _disc_backend_port = found_port;
        EEPROMConfig::saveBackendHost(_disc_backend_host.c_str(),
                                      _disc_backend_port);
        Serial.printf("[DISC] Layer 1 OK — backend at %s:%u\n",
                      _disc_backend_host.c_str(), _disc_backend_port);
        return true;
    }

    // ── Layer 2: UDP broadcast ───────────────────────────────────────────────
    Serial.println("[DISC] Layer 2 — UDP broadcast discovery ...");
    String udp_ip = UDPDiscovery::discover(found_port);
    if (!udp_ip.isEmpty()) {
        _disc_backend_host = udp_ip;
        _disc_backend_port = found_port;
        EEPROMConfig::saveBackendHost(_disc_backend_host.c_str(),
                                      _disc_backend_port);
        Serial.printf("[DISC] Layer 2 OK — backend at %s:%u\n",
                      _disc_backend_host.c_str(), _disc_backend_port);
        return true;
    }

    Serial.println("[DISC] All auto-discovery layers failed");
    return false;
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Run the full discovery process.  Blocks until a backend is found.
 *
 * After this function returns the caller can use:
 *   discovery_get_host()
 *   discovery_get_port()
 *   discovery_get_device_id()
 */
inline void discovery_begin() {
    // Build device ID as early as possible (needs WiFi MAC)
    WiFi.mode(WIFI_STA);
    _disc_device_id = _disc_make_device_id();
    Serial.printf("[DISC] Device ID: %s\n", _disc_device_id.c_str());

    // ── Check for factory-reset button (GPIO0 held LOW at boot) ──────────────
    pinMode(DISCOVERY_RESET_PIN, INPUT_PULLUP);
    if (digitalRead(DISCOVERY_RESET_PIN) == LOW) {
        unsigned long hold_start = millis();
        while (digitalRead(DISCOVERY_RESET_PIN) == LOW &&
               millis() - hold_start < DISCOVERY_RESET_HOLD_MS) {
            delay(50);
        }
        if (millis() - hold_start >= DISCOVERY_RESET_HOLD_MS) {
            Serial.println("[DISC] Reset button held — clearing stored config");
            EEPROMConfig::clear();
        }
    }

    // ── Load persisted config ─────────────────────────────────────────────────
    _disc_saved_cfg = EEPROMConfig::load();
    Serial.printf("[DISC] EEPROM: valid=%d ssid='%s' backend='%s:%u'\n",
                  _disc_saved_cfg.valid,
                  _disc_saved_cfg.wifi_ssid,
                  _disc_saved_cfg.backend_host,
                  _disc_saved_cfg.backend_port);

    // ── Attempt connection with stored WiFi credentials ───────────────────────
    bool wifi_ok = false;
    if (_disc_saved_cfg.valid && strlen(_disc_saved_cfg.wifi_ssid) > 0) {
        wifi_ok = _disc_wifi_connect(_disc_saved_cfg.wifi_ssid,
                                     _disc_saved_cfg.wifi_password);
    }

    // If WiFi is up, run layers 3 / 1 / 2
    if (wifi_ok && _disc_find_backend()) {
        return;   // ✓ Discovery succeeded
    }

    // ── Layer 4: AP mode + captive portal (loops until configured) ────────────
    Serial.println("[DISC] Layer 4 — launching AP mode ...");
    APModeServer::start();

    while (true) {
        if (APModeServer::loop()) {
            // User submitted the configuration form
            String new_ssid = APModeServer::getSSID();
            String new_pass = APModeServer::getPass();
            String new_host = APModeServer::getHost();
            uint16_t new_port = APModeServer::getPort();

            APModeServer::stop();
            delay(500);

            if (_disc_wifi_connect(new_ssid.c_str(), new_pass.c_str())) {
                // If the user supplied a static backend IP, use it directly
                if (!new_host.isEmpty()) {
                    _disc_backend_host = new_host;
                    _disc_backend_port = new_port;
                    EEPROMConfig::saveBackendHost(_disc_backend_host.c_str(),
                                                  _disc_backend_port);
                    Serial.printf("[DISC] User-configured backend: %s:%u\n",
                                  _disc_backend_host.c_str(), _disc_backend_port);
                    return;
                }

                // No static IP given — run auto-discovery on the new network
                if (_disc_find_backend()) {
                    return;
                }

                Serial.println("[DISC] Backend not found on new network. "
                               "Returning to AP mode.");
            } else {
                Serial.println("[DISC] WiFi connection failed. "
                               "Returning to AP mode.");
            }

            // Re-launch AP mode for another attempt
            APModeServer::start();
        }
        delay(10);
    }
}

// ── Accessors (valid after discovery_begin returns) ───────────────────────────

/** Backend hostname / IP address string. */
inline const char* discovery_get_host() {
    return _disc_backend_host.c_str();
}

/** Backend TCP port. */
inline uint16_t discovery_get_port() {
    return _disc_backend_port;
}

/** Unique MAC-based device identifier, e.g. "espcontroller_a1b2c3". */
inline const char* discovery_get_device_id() {
    return _disc_device_id.c_str();
}

#endif // WIFI_DISCOVERY_H
