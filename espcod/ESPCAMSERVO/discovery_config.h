#ifndef DISCOVERY_CONFIG_H
#define DISCOVERY_CONFIG_H

/*
 * DISCOVERY_CONFIG.H
 *
 * Shared constants for the 4-layer WiFi auto-discovery system.
 *
 * Discovery layers (tried in order):
 *   Layer 3 (fastest) : EEPROM — re-use last known backend IP
 *   Layer 1           : mDNS   — query "chetan-robot._http._tcp.local."
 *   Layer 2           : UDP    — broadcast CHETAN_ROBOT_DISCOVERY on LAN
 *   Layer 4 (fallback): AP     — create "ChetanRobot_SETUP_XXYY" hotspot
 */

// ── mDNS ──────────────────────────────────────────────────────────────────────
#define MDNS_SERVICE_TYPE       "_http"
#define MDNS_SERVICE_PROTO      "tcp"
// Substring that must appear in the mDNS hostname to identify the backend
#define MDNS_BACKEND_HOSTNAME   "chetan-robot"
// Time (ms) to wait for mDNS service query results
#define MDNS_QUERY_TIMEOUT_MS   3000

// ── UDP broadcast ─────────────────────────────────────────────────────────────
#define UDP_DISCOVERY_PORT      54321
#define UDP_DISCOVERY_BCAST     "255.255.255.255"
#define UDP_DISCOVERY_REQUEST   "CHETAN_ROBOT_DISCOVERY"
#define UDP_DISCOVERY_PREFIX    "CHETAN_ROBOT_BACKEND:"
// Time (ms) to wait for a UDP discovery response
#define UDP_DISCOVERY_TIMEOUT_MS 5000

// ── AP / captive portal ───────────────────────────────────────────────────────
// AP SSID will be suffixed with the last 2 bytes of the MAC address
#define DISCOVERY_AP_SSID_PREFIX  "ChetanRobot_SETUP"
// AP password for Windows 11 compatibility (minimum 8 characters)
#define DISCOVERY_AP_PASSWORD     "ChetanRobot123"
#define DISCOVERY_DNS_PORT        53
#define DISCOVERY_HTTP_PORT       80

// ── WiFi ──────────────────────────────────────────────────────────────────────
// Maximum time (ms) to wait for a WiFi station connection before giving up
#define DISCOVERY_WIFI_TIMEOUT_MS 15000

// ── Backend ───────────────────────────────────────────────────────────────────
#define DISCOVERY_DEFAULT_PORT  8000

// ── Reset button ─────────────────────────────────────────────────────────────
// GPIO0 is the BOOT button on most ESP32-S3 dev boards.
// Hold it for DISCOVERY_RESET_HOLD_MS at power-on to clear stored config.
#define DISCOVERY_RESET_PIN       0
#define DISCOVERY_RESET_HOLD_MS   3000

#endif // DISCOVERY_CONFIG_H
