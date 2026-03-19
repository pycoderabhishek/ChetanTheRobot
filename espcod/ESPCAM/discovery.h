/**
 * discovery.h
 * Orchestrates the 4-layer auto-discovery system:
 *
 *   Layer 1 — mDNS:      resolve 'chetan-robot.local'    (3 attempts)
 *   Layer 2 — UDP:       broadcast probe on LAN           (2 attempts)
 *   Layer 3 — EEPROM:    use last known IP from NVS       (1 attempt)
 *   Layer 4 — AP mode:   captive portal for manual setup  (blocks until done)
 *
 * Usage:
 *   #include "discovery.h"
 *   char backendHost[64];
 *   uint16_t backendPort = 8000;
 *   discover_backend(backendHost, sizeof(backendHost), &backendPort);
 */

#pragma once

#include <HTTPClient.h>
#include "eeprom_config.h"
#include "mdns_handler.h"
#include "udp_discovery.h"
#include "ap_mode.h"

// How many times to retry each discovery method before falling back
#define DISCOVERY_MDNS_RETRIES  3
#define DISCOVERY_UDP_RETRIES   2

/**
 * Verify the backend is reachable by issuing a quick HTTP GET to /health.
 * Returns true if the server responds with HTTP 2xx.
 */
static bool _ping_backend(const char* host, uint16_t port) {
  HTTPClient http;
  String url = String("http://") + host + ":" + port + "/health";
  http.begin(url);
  http.setTimeout(3000);
  int code = http.GET();
  http.end();
  return (code >= 200 && code < 300);
}

/**
 * Run the full discovery sequence.
 * `out_host` is filled with the resolved IP/hostname on success.
 * `out_port` is updated when a port is discovered (default 8000).
 *
 * The function never returns without a valid backend address —
 * if all automated methods fail it enters AP mode which reboots the device.
 */
void discover_backend(char* out_host, size_t host_size, uint16_t* out_port = nullptr) {
  uint16_t port = out_port ? *out_port : 8000;
  char tmp[64];

  Serial.println("\n[DISCOVERY] Starting auto-discovery...");

  // ── Layer 1: mDNS ────────────────────────────────────────────────────────
  Serial.println("[DISCOVERY] Layer 1: mDNS");
  for (int attempt = 1; attempt <= DISCOVERY_MDNS_RETRIES; attempt++) {
    Serial.printf("[DISCOVERY]   mDNS attempt %d/%d\n", attempt, DISCOVERY_MDNS_RETRIES);
    uint16_t discovered_port = port;
    if (mdns_discover(tmp, sizeof(tmp), &discovered_port)) {
      if (_ping_backend(tmp, discovered_port)) {
        strlcpy(out_host, tmp, host_size);
        if (out_port) *out_port = discovered_port;
        EEPROMConfig::saveHost(out_host, discovered_port);
        Serial.printf("[DISCOVERY] ✓ Backend found via mDNS: %s:%u\n", out_host, discovered_port);
        return;
      }
      Serial.printf("[DISCOVERY]   mDNS resolved %s but /health check failed\n", tmp);
    }
    if (attempt < DISCOVERY_MDNS_RETRIES) delay(2000);
  }

  // ── Layer 2: UDP Broadcast ───────────────────────────────────────────────
  Serial.println("[DISCOVERY] Layer 2: UDP broadcast");
  for (int attempt = 1; attempt <= DISCOVERY_UDP_RETRIES; attempt++) {
    Serial.printf("[DISCOVERY]   UDP attempt %d/%d\n", attempt, DISCOVERY_UDP_RETRIES);
    uint16_t discovered_port = port;
    if (udp_discover(tmp, sizeof(tmp), &discovered_port)) {
      if (_ping_backend(tmp, discovered_port)) {
        strlcpy(out_host, tmp, host_size);
        if (out_port) *out_port = discovered_port;
        EEPROMConfig::saveHost(out_host, discovered_port);
        Serial.printf("[DISCOVERY] ✓ Backend found via UDP: %s:%u\n", out_host, discovered_port);
        return;
      }
      Serial.printf("[DISCOVERY]   UDP resolved %s but /health check failed\n", tmp);
    }
    if (attempt < DISCOVERY_UDP_RETRIES) delay(2000);
  }

  // ── Layer 3: EEPROM stored IP ────────────────────────────────────────────
  Serial.println("[DISCOVERY] Layer 3: EEPROM stored config");
  uint16_t stored_port = port;
  if (EEPROMConfig::loadHost(tmp, sizeof(tmp), &stored_port)) {
    Serial.printf("[DISCOVERY]   Trying stored backend: %s:%u\n", tmp, stored_port);
    if (_ping_backend(tmp, stored_port)) {
      strlcpy(out_host, tmp, host_size);
      if (out_port) *out_port = stored_port;
      Serial.printf("[DISCOVERY] ✓ Backend found via EEPROM: %s:%u\n", out_host, stored_port);
      return;
    }
    Serial.println("[DISCOVERY]   Stored IP unreachable");
  } else {
    Serial.println("[DISCOVERY]   No stored config found");
  }

  // ── Layer 4: AP mode + captive portal ────────────────────────────────────
  Serial.println("[DISCOVERY] Layer 4: Entering AP mode for manual configuration");
  // enter_ap_mode() calls ESP.restart() — it never returns
  enter_ap_mode();
}
