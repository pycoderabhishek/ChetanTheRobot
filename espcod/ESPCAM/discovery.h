/**
 * discovery.h
 * 4-layer hierarchical backend discovery orchestrator.
 *
 * Layer order (fastest → most reliable fallback):
 *   1. EEPROM / NVS   — instant reconnect using last-known good IP
 *   2. mDNS            — zero-config discovery via 'chetan-robot.local'
 *   3. UDP Broadcast   — LAN-wide probe/response discovery
 *   4. AP Mode         — user-facing captive portal for manual entry
 *
 * Usage (in ESPCAM.ino setup(), after WiFi is connected):
 *
 *   #include "discovery.h"
 *   String backend_host;
 *   uint16_t backend_port = 8000;
 *   if (!discover_backend(backend_host, backend_port)) {
 *       Serial.println("[DISCOVERY] All layers failed — halting");
 *       while(1) delay(1000);
 *   }
 */

#pragma once
#include <WiFi.h>
#include "eeprom_config.h"
#include "mdns_handler.h"
#include "udp_discovery.h"
#include "ap_mode.h"

// Milliseconds to wait for a TCP connection check (ping substitute)
#define DISCOVERY_CONN_TIMEOUT_MS  3000

/**
 * Quickly verify that `host:port` is reachable by attempting a TCP connection.
 * Returns true if the server accepts the connection within the timeout.
 */
static bool _backend_reachable(const String& host, uint16_t port) {
    if (host.length() == 0) return false;

    WiFiClient client;
    client.setTimeout(DISCOVERY_CONN_TIMEOUT_MS);
    bool ok = client.connect(host.c_str(), port);
    client.stop();
    return ok;
}

/**
 * Run the 4-layer discovery sequence.
 * Blocks until a reachable backend is found or all layers are exhausted.
 *
 * @param host  [out] Resolved backend IP address string
 * @param port  [out] Resolved backend port
 * @return true  if a reachable backend was found
 * @return false if every layer failed (AP mode timed out)
 */
bool discover_backend(String& host, uint16_t& port) {
    Serial.println("\n[DISCOVERY] Starting 4-layer backend discovery...");

    // ------------------------------------------------------------------
    // Layer 3 (EEPROM — tried first for instant reconnect on boot):
    // If we have a cached backend IP from a previous successful connection,
    // try it before running the slower discovery methods.
    // ------------------------------------------------------------------
    {
        String stored_host;
        uint16_t stored_port = 8000;
        if (EEPROMConfig::load(stored_host, stored_port)) {
            Serial.printf("[DISCOVERY] L3-EEPROM: trying stored IP %s:%u\n",
                          stored_host.c_str(), stored_port);
            if (_backend_reachable(stored_host, stored_port)) {
                host = stored_host;
                port = stored_port;
                Serial.println("[DISCOVERY] L3-EEPROM: success ✓");
                return true;
            }
            Serial.println("[DISCOVERY] L3-EEPROM: stored IP unreachable, continuing...");
        } else {
            Serial.println("[DISCOVERY] L3-EEPROM: no stored config");
        }
    }

    // ------------------------------------------------------------------
    // Layer 1: mDNS — query for 'chetan-robot._http._tcp.local.'
    // ------------------------------------------------------------------
    {
        String mdns_host;
        uint16_t mdns_port = 8000;
        Serial.println("[DISCOVERY] L1-mDNS: querying chetan-robot.local...");
        if (mdns_find_backend(mdns_host, mdns_port)) {
            if (_backend_reachable(mdns_host, mdns_port)) {
                host = mdns_host;
                port = mdns_port;
                EEPROMConfig::save(host, port);   // cache for next boot
                Serial.println("[DISCOVERY] L1-mDNS: success ✓");
                return true;
            }
            Serial.println("[DISCOVERY] L1-mDNS: found but unreachable");
        } else {
            Serial.println("[DISCOVERY] L1-mDNS: no response");
        }
    }

    // ------------------------------------------------------------------
    // Layer 2: UDP Broadcast — "CHETAN_ROBOT_DISCOVERY" probe
    // ------------------------------------------------------------------
    {
        String udp_host;
        uint16_t udp_port = 8000;
        Serial.println("[DISCOVERY] L2-UDP: broadcasting discovery probe...");
        if (udp_discover_backend(udp_host, udp_port)) {
            if (_backend_reachable(udp_host, udp_port)) {
                host = udp_host;
                port = udp_port;
                EEPROMConfig::save(host, port);   // cache for next boot
                Serial.println("[DISCOVERY] L2-UDP: success ✓");
                return true;
            }
            Serial.println("[DISCOVERY] L2-UDP: found but unreachable");
        } else {
            Serial.println("[DISCOVERY] L2-UDP: no response");
        }
    }

    // ------------------------------------------------------------------
    // Layer 4: AP Mode — user manually provides backend address
    // ------------------------------------------------------------------
    {
        String ap_host;
        uint16_t ap_port = 8000;
        Serial.println("[DISCOVERY] L4-AP: launching captive portal...");
        if (ap_mode_start(ap_host, ap_port)) {
            host = ap_host;
            port = ap_port;
            EEPROMConfig::save(host, port);       // cache for next boot
            Serial.println("[DISCOVERY] L4-AP: configuration received ✓");
            return true;
        }
        Serial.println("[DISCOVERY] L4-AP: no configuration entered — discovery failed");
    }

    return false;
}
