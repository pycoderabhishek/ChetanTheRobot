/**
 * mdns_handler.h
 * mDNS client: discovers the backend advertised as 'chetan-robot.local'.
 * Uses the Arduino ESPmDNS library included with the ESP32 core.
 */

#pragma once

#include <ESPmDNS.h>

#define MDNS_HOSTNAME  "chetan-robot"
#define MDNS_TIMEOUT_MS 5000

/**
 * Try to resolve 'chetan-robot.local' via mDNS.
 * Writes the resolved IP string into `out_host` (max `host_size` bytes).
 * Returns true on success.
 */
bool mdns_discover(char* out_host, size_t host_size, uint16_t* out_port = nullptr) {
  Serial.println("[mDNS] Starting query for 'chetan-robot.local'...");

  if (!MDNS.begin("espcam")) {
    Serial.println("[mDNS] MDNS.begin() failed");
    return false;
  }

  // Query for _http._tcp services named 'chetan-robot'
  int n = MDNS.queryService("http", "tcp");
  if (n > 0) {
    for (int i = 0; i < n; i++) {
      String name = MDNS.hostname(i);
      Serial.printf("[mDNS] Found service: %s  IP: %s  Port: %u\n",
                    name.c_str(),
                    MDNS.IP(i).toString().c_str(),
                    MDNS.port(i));
      if (name.indexOf(MDNS_HOSTNAME) >= 0) {
        String ip = MDNS.IP(i).toString();
        strlcpy(out_host, ip.c_str(), host_size);
        if (out_port) *out_port = MDNS.port(i);
        Serial.printf("[mDNS] Backend found at %s:%u\n", out_host, out_port ? *out_port : 8000);
        return true;
      }
    }
  }

  // Fallback: direct hostname lookup
  IPAddress addr = MDNS.queryHost(MDNS_HOSTNAME, MDNS_TIMEOUT_MS);
  if (addr != INADDR_NONE && addr != IPAddress(0, 0, 0, 0)) {
    String ip = addr.toString();
    strlcpy(out_host, ip.c_str(), host_size);
    Serial.printf("[mDNS] Hostname resolved: %s → %s\n", MDNS_HOSTNAME, out_host);
    return true;
  }

  Serial.println("[mDNS] Discovery failed");
  return false;
}
