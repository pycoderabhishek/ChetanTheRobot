#ifndef MDNS_HANDLER_H
#define MDNS_HANDLER_H

/*
 * MDNS_HANDLER.H  —  Layer 1 of the discovery system
 *
 * Queries mDNS for the backend service "_http._tcp.local." and returns the
 * IP address of any host whose mDNS hostname contains "chetan-robot".
 *
 * The backend registers itself via zeroconf (Python) as:
 *   Service type : _http._tcp.local.
 *   Service name : chetan-robot._http._tcp.local.
 *   Hostname     : chetan-robot.local.
 *
 * Requires:  ESPmDNS  (built into ESP32 Arduino SDK)
 */

#include <ESPmDNS.h>
#include "discovery_config.h"

namespace MDNSHandler {

// Query mDNS for the backend service.
// On success, sets out_port and returns the backend IP as a String.
// Returns an empty String if the backend cannot be found.
inline String resolve(uint16_t& out_port) {
    out_port = DISCOVERY_DEFAULT_PORT;

    // Initialise mDNS for this device.  The hostname given here is the
    // ESP32's own advertised name, not the service we are searching for.
    if (!MDNS.begin("espcam-discovery")) {
        Serial.println("[mDNS] Failed to start mDNS responder");
        return "";
    }

    Serial.printf("[mDNS] Querying for %s.%s.local ...\n",
                  MDNS_SERVICE_TYPE, MDNS_SERVICE_PROTO);

    // Query blocks for up to MDNS_QUERY_TIMEOUT_MS and returns the number
    // of matching services found.
    int n = MDNS.queryService(MDNS_SERVICE_TYPE, MDNS_SERVICE_PROTO,
                              MDNS_QUERY_TIMEOUT_MS);

    if (n <= 0) {
        Serial.println("[mDNS] No services found");
        return "";
    }

    for (int i = 0; i < n; i++) {
        String hostname = MDNS.hostname(i);
        Serial.printf("[mDNS] Candidate %d: hostname='%s' ip=%s port=%u\n",
                      i, hostname.c_str(),
                      MDNS.IP(i).toString().c_str(), MDNS.port(i));

        if (hostname.indexOf(MDNS_BACKEND_HOSTNAME) >= 0) {
            String ip = MDNS.IP(i).toString();
            out_port  = MDNS.port(i);
            Serial.printf("[mDNS] Backend matched: %s:%u\n", ip.c_str(), out_port);
            return ip;
        }
    }

    Serial.println("[mDNS] No matching backend in query results");
    return "";
}

} // namespace MDNSHandler

#endif // MDNS_HANDLER_H
