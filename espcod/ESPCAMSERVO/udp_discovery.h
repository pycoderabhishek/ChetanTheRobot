#ifndef UDP_DISCOVERY_H
#define UDP_DISCOVERY_H

/*
 * UDP_DISCOVERY.H  —  Layer 2 of the discovery system
 *
 * Broadcasts a discovery request on the LAN and waits for the backend to
 * reply with its IP address and port.
 *
 * Protocol (matches udp_broadcaster.py on the backend):
 *   Request  (ESP32  → broadcast port 54321): "CHETAN_ROBOT_DISCOVERY"
 *   Response (backend → ESP32 unicast):       "CHETAN_ROBOT_BACKEND:<ip>:<port>"
 *
 * Requires:  WiFiUdp  (built into ESP32 Arduino SDK)
 */

#include <WiFiUdp.h>
#include "discovery_config.h"

namespace UDPDiscovery {

// Broadcast a discovery request and wait up to UDP_DISCOVERY_TIMEOUT_MS for a
// response.  On success, sets out_port and returns the backend IP as a String.
// Returns an empty String if no backend responds in time.
inline String discover(uint16_t& out_port) {
    out_port = DISCOVERY_DEFAULT_PORT;

    WiFiUDP udp;
    if (!udp.begin(UDP_DISCOVERY_PORT)) {
        Serial.println("[UDP] Failed to bind local discovery port");
        return "";
    }

    // ── Broadcast the discovery request ──────────────────────────────────────
    Serial.printf("[UDP] Broadcasting '%s' on port %u ...\n",
                  UDP_DISCOVERY_REQUEST, UDP_DISCOVERY_PORT);

    udp.beginPacket(UDP_DISCOVERY_BCAST, UDP_DISCOVERY_PORT);
    udp.write(reinterpret_cast<const uint8_t*>(UDP_DISCOVERY_REQUEST),
              strlen(UDP_DISCOVERY_REQUEST));
    udp.endPacket();

    // ── Wait for the response ─────────────────────────────────────────────────
    String     result     = "";
    const char* prefix    = UDP_DISCOVERY_PREFIX;
    size_t      prefix_len = strlen(prefix);
    unsigned long deadline = millis() + UDP_DISCOVERY_TIMEOUT_MS;

    while (millis() < deadline) {
        int pkt_len = udp.parsePacket();
        if (pkt_len > 0) {
            char buf[128];
            int  n   = udp.read(buf, (int)sizeof(buf) - 1);
            if (n > 0) {
                buf[n] = '\0';
                Serial.printf("[UDP] Received: '%s'\n", buf);

                if (strncmp(buf, prefix, prefix_len) == 0) {
                    // Payload format: "<ip>:<port>"
                    char*  payload = buf + prefix_len;
                    char*  colon   = strchr(payload, ':');
                    if (colon) {
                        *colon    = '\0';
                        out_port  = (uint16_t)atoi(colon + 1);
                        result    = String(payload);
                    } else {
                        result    = String(payload);
                    }
                    if (out_port == 0) out_port = DISCOVERY_DEFAULT_PORT;
                    Serial.printf("[UDP] Backend found: %s:%u\n",
                                  result.c_str(), out_port);
                    break;
                }
            }
        }
        delay(50);
    }

    udp.stop();

    if (result.isEmpty()) {
        Serial.println("[UDP] No backend responded to discovery broadcast");
    }
    return result;
}

} // namespace UDPDiscovery

#endif // UDP_DISCOVERY_H
