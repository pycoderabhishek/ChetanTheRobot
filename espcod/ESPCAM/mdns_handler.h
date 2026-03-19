/**
 * mdns_handler.h
 * Discovers the backend server by querying for the mDNS/Bonjour service
 * "chetan-robot._http._tcp.local." that the Python backend advertises.
 *
 * Requires: ESP32 built-in ESPmDNS library (no extra installation needed).
 */

#pragma once
#include <ESPmDNS.h>

// The service name the Python backend registers (must match mdns_advertiser.py)
#define MDNS_QUERY_SERVICE  "http"
#define MDNS_QUERY_PROTO    "tcp"
#define MDNS_HOST_PREFIX    "chetan-robot"

// How long to wait for mDNS responses (ms)
#define MDNS_TIMEOUT_MS  5000

/**
 * Query the local network for the Chetan robot backend via mDNS.
 * On success, writes the resolved IP into `host` and port into `port`
 * and returns true.  Returns false if no matching service is found.
 */
bool mdns_find_backend(String& host, uint16_t& port) {
    Serial.println("[mDNS] Starting query for chetan-robot backend...");

    if (!MDNS.begin("esp32-chetan")) {
        Serial.println("[mDNS] MDNS.begin() failed");
        return false;
    }

    unsigned long start = millis();
    int n = 0;

    // Retry within the timeout window
    while (millis() - start < MDNS_TIMEOUT_MS) {
        n = MDNS.queryService(MDNS_QUERY_SERVICE, MDNS_QUERY_PROTO);
        if (n > 0) break;
        delay(200);
    }

    if (n == 0) {
        Serial.println("[mDNS] No services found");
        return false;
    }

    Serial.printf("[mDNS] Found %d service(s)\n", n);
    for (int i = 0; i < n; i++) {
        String hostname = MDNS.hostname(i);
        Serial.printf("[mDNS]   %s -> %s:%u\n",
                      hostname.c_str(),
                      MDNS.IP(i).toString().c_str(),
                      MDNS.port(i));

        if (hostname.startsWith(MDNS_HOST_PREFIX)) {
            host = MDNS.IP(i).toString();
            port = MDNS.port(i);
            Serial.printf("[mDNS] Resolved backend: %s:%u\n", host.c_str(), port);
            return true;
        }
    }

    Serial.println("[mDNS] No matching backend service found");
    return false;
}
