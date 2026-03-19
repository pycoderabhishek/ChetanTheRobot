/**
 * udp_discovery.h
 * UDP broadcast discovery: ESP32 broadcasts a probe and the backend replies
 * with its IP address and port.
 *
 * Protocol:
 *   Request  → broadcasts b"CHETAN_ROBOT_DISCOVERY" to 255.255.255.255:54321
 *   Response ← backend replies b"CHETAN_ROBOT_BACKEND:<ip>:<port>"
 */

#pragma once

#include <WiFiUdp.h>

#define UDP_DISCOVERY_PORT    54321
#define UDP_RESPONSE_TIMEOUT  4000   // ms to wait for a reply
#define UDP_REQUEST_MSG       "CHETAN_ROBOT_DISCOVERY"
#define UDP_RESPONSE_PREFIX   "CHETAN_ROBOT_BACKEND:"

/**
 * Broadcast a UDP discovery probe and wait for a backend response.
 * Writes resolved IP into `out_host`; writes port into `out_port` if provided.
 * Returns true on success.
 */
bool udp_discover(char* out_host, size_t host_size, uint16_t* out_port = nullptr) {
  WiFiUDP udp;
  Serial.println("[UDP] Broadcasting discovery probe...");

  if (!udp.begin(UDP_DISCOVERY_PORT)) {
    Serial.println("[UDP] Failed to open UDP socket");
    return false;
  }

  // Send broadcast
  udp.beginPacket("255.255.255.255", UDP_DISCOVERY_PORT);
  udp.print(UDP_REQUEST_MSG);
  udp.endPacket();

  unsigned long start = millis();
  bool found = false;

  while (millis() - start < UDP_RESPONSE_TIMEOUT) {
    int pkt = udp.parsePacket();
    if (pkt > 0) {
      char buf[128] = {0};
      int len = udp.read(buf, sizeof(buf) - 1);
      buf[len] = '\0';

      Serial.printf("[UDP] Received: %s\n", buf);

      if (strncmp(buf, UDP_RESPONSE_PREFIX, strlen(UDP_RESPONSE_PREFIX)) == 0) {
        // Parse "ip:port" after the prefix
        char* payload = buf + strlen(UDP_RESPONSE_PREFIX);
        char* colon = strrchr(payload, ':');
        if (colon) {
          *colon = '\0';
          strlcpy(out_host, payload, host_size);
          if (out_port) *out_port = (uint16_t)atoi(colon + 1);
          Serial.printf("[UDP] Backend discovered: %s:%u\n",
                        out_host, out_port ? *out_port : 8000);
          found = true;
        } else {
          strlcpy(out_host, payload, host_size);
          found = true;
        }
        break;
      }
    }
    delay(10);
  }

  udp.stop();

  if (!found) {
    Serial.println("[UDP] Discovery timeout — no response received");
  }
  return found;
}
