/**
 * udp_discovery.h
 * Discovers the backend by broadcasting a UDP probe on the LAN.
 * The Python backend (udp_broadcaster.py) listens on UDP port 54321 and
 * responds with its IP and port.
 *
 * Protocol:
 *   Request  (ESP32 → 255.255.255.255:54321): "CHETAN_ROBOT_DISCOVERY"
 *   Response (backend → ESP32):               "CHETAN_ROBOT_BACKEND:<ip>:<port>"
 */

#pragma once
#include <WiFiUDP.h>

// Must match constants in udp_broadcaster.py
#define UDP_DISCOVERY_PORT       54321
#define UDP_DISCOVERY_REQUEST    "CHETAN_ROBOT_DISCOVERY"
#define UDP_RESPONSE_PREFIX      "CHETAN_ROBOT_BACKEND:"

// Maximum time to wait for a response per attempt (ms)
#define UDP_TIMEOUT_MS           5000
// Number of broadcast attempts before giving up
#define UDP_MAX_ATTEMPTS         3

/**
 * Broadcast a discovery probe and wait for the backend to respond.
 * On success, writes the backend IP into `host` and port into `port`
 * and returns true.
 */
bool udp_discover_backend(String& host, uint16_t& port) {
    WiFiUDP udp;

    if (!udp.begin(UDP_DISCOVERY_PORT)) {
        Serial.println("[UDP] Failed to bind UDP socket");
        return false;
    }

    bool found = false;

    for (int attempt = 1; attempt <= UDP_MAX_ATTEMPTS && !found; attempt++) {
        Serial.printf("[UDP] Discovery attempt %d/%d...\n", attempt, UDP_MAX_ATTEMPTS);

        // Send broadcast probe
        udp.beginPacket(IPAddress(255, 255, 255, 255), UDP_DISCOVERY_PORT);
        udp.print(UDP_DISCOVERY_REQUEST);
        udp.endPacket();

        // Wait for response within timeout
        unsigned long start = millis();
        while (millis() - start < UDP_TIMEOUT_MS) {
            int pktSize = udp.parsePacket();
            if (pktSize > 0) {
                char buf[128] = {0};
                int len = udp.read(buf, sizeof(buf) - 1);
                if (len > 0) {
                    buf[len] = '\0';
                    String response = String(buf);
                    Serial.printf("[UDP] Received: %s\n", response.c_str());

                    if (response.startsWith(UDP_RESPONSE_PREFIX)) {
                        String payload = response.substring(strlen(UDP_RESPONSE_PREFIX));
                        int colon = payload.lastIndexOf(':');
                        if (colon > 0) {
                            host = payload.substring(0, colon);
                            port = (uint16_t)payload.substring(colon + 1).toInt();
                            Serial.printf("[UDP] Discovered backend: %s:%u\n",
                                          host.c_str(), port);
                            found = true;
                            break;
                        }
                    }
                }
            }
            delay(50);
        }
    }

    udp.stop();

    if (!found) {
        Serial.println("[UDP] Discovery failed — no response received");
    }
    return found;
}
