#ifndef AP_MODE_SERVER_H
#define AP_MODE_SERVER_H

/*
 * AP_MODE_SERVER.H  —  Layer 4 of the discovery system
 *
 * When all auto-discovery methods fail, the ESP32 creates a standalone WiFi
 * access point and hosts a captive-portal web page at 192.168.4.1.
 *
 * The user connects to the AP (SSID: "ChetanRobot_SETUP_XXYY", open / no
 * password), opens a browser, fills in their WiFi SSID, password and
 * optionally a static backend IP, then presses "Save & Connect".
 *
 * The saved values are written to EEPROM via EEPROMConfig::save().
 *
 * Requires:  WebServer, DNSServer  (built into ESP32 Arduino SDK)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include "discovery_config.h"
#include "eeprom_config.h"

namespace APModeServer {

// ── Module state ──────────────────────────────────────────────────────────────
static WebServer _server(DISCOVERY_HTTP_PORT);
static DNSServer _dns;
static bool      _configured = false;

static String    _result_ssid;
static String    _result_pass;
static String    _result_host;
static uint16_t  _result_port = DISCOVERY_DEFAULT_PORT;

// ── HTML pages ────────────────────────────────────────────────────────────────
static const char HTML_PORTAL[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ChetanRobot Setup</title>
  <style>
    body{font-family:Arial,sans-serif;background:#1a1a2e;color:#eee;padding:20px;max-width:500px;margin:auto}
    h1{color:#e94560}
    label{display:block;margin-top:14px;font-size:.9em;color:#aaa}
    input{width:100%;padding:10px;margin-top:4px;background:#16213e;color:#eee;
          border:1px solid #0f3460;border-radius:6px;box-sizing:border-box}
    button{width:100%;padding:12px;margin-top:20px;background:#e94560;color:#fff;
           border:none;border-radius:6px;font-size:1em;cursor:pointer}
    button:hover{background:#c73652}
    .info{background:#0f3460;padding:10px;border-radius:6px;margin-top:10px;font-size:.85em}
  </style>
</head>
<body>
  <h1>&#129302; ChetanRobot Setup</h1>
  <p>Configure WiFi and backend server connection.</p>
  <div class="info">&#128272; Settings are saved permanently on the device.</div>
  <form method="POST" action="/save">
    <label>WiFi SSID *</label>
    <input type="text" name="ssid" placeholder="Your WiFi network name" required>
    <label>WiFi Password</label>
    <input type="password" name="pass" placeholder="Leave blank for open networks">
    <label>Backend IP <small>(leave blank for auto-discovery)</small></label>
    <input type="text" name="host" placeholder="e.g. 192.168.1.100">
    <label>Backend Port</label>
    <input type="number" name="port" value="8000" min="1" max="65535">
    <button type="submit">Save &amp; Connect</button>
  </form>
</body>
</html>
)rawliteral";

static const char HTML_SAVED[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Saved!</title>
  <style>
    body{font-family:Arial,sans-serif;background:#1a1a2e;color:#eee;
         padding:20px;max-width:500px;margin:auto;text-align:center}
    h1{color:#4ecca3}
  </style>
</head>
<body>
  <h1>&#10003; Configuration Saved!</h1>
  <p>The device will now restart and connect to your network.</p>
  <p>Reconnect your phone / laptop to your normal WiFi.</p>
</body>
</html>
)rawliteral";

// ── Request handlers ──────────────────────────────────────────────────────────
static void _handleRoot() {
    _server.send_P(200, "text/html", HTML_PORTAL);
}

static void _handleSave() {
    String ssid = _server.arg("ssid");
    String pass = _server.arg("pass");
    String host = _server.arg("host");
    String port_str = _server.arg("port");

    if (ssid.length() == 0) {
        _server.send(400, "text/html",
                     "<h2 style='color:red'>Error: WiFi SSID is required.</h2>");
        return;
    }

    uint16_t port = (port_str.length() > 0) ? (uint16_t)port_str.toInt()
                                             : DISCOVERY_DEFAULT_PORT;
    if (port == 0) port = DISCOVERY_DEFAULT_PORT;

    _result_ssid = ssid;
    _result_pass = pass;
    _result_host = host;
    _result_port = port;

    // Persist immediately so a power-cycle during WiFi reconnect recovers
    EEPROMConfig::Config cfg;
    strncpy(cfg.wifi_ssid,     ssid.c_str(), sizeof(cfg.wifi_ssid)     - 1);
    strncpy(cfg.wifi_password, pass.c_str(), sizeof(cfg.wifi_password) - 1);
    strncpy(cfg.backend_host,  host.c_str(), sizeof(cfg.backend_host)  - 1);
    cfg.backend_port = port;
    EEPROMConfig::save(cfg);

    _server.send_P(200, "text/html", HTML_SAVED);
    _configured = true;
}

// ── Public API ────────────────────────────────────────────────────────────────

// Start the access point, DNS redirect and web server.
inline void start() {
    _configured = false;

    // Build AP SSID: "ChetanRobot_SETUP_XXYY" using last 2 MAC bytes
    uint8_t mac[6];
    WiFi.macAddress(mac);
    char ap_ssid[36];
    snprintf(ap_ssid, sizeof(ap_ssid), "%s_%02X%02X",
             DISCOVERY_AP_SSID_PREFIX, mac[4], mac[5]);

    Serial.printf("[AP] Starting access point: '%s'\n", ap_ssid);

    WiFi.mode(WIFI_AP);
    WiFi.softAPConfig(
        IPAddress(192, 168, 4, 1),
        IPAddress(192, 168, 4, 1),
        IPAddress(255, 255, 255, 0)
    );

    const char* ap_pw = (strlen(DISCOVERY_AP_PASSWORD) > 0)
                         ? DISCOVERY_AP_PASSWORD : nullptr;
    WiFi.softAP(ap_ssid, ap_pw);

    Serial.printf("[AP] Access-point IP: %s\n",
                  WiFi.softAPIP().toString().c_str());
    Serial.println("[AP] Open http://192.168.4.1 to configure");

    // Redirect ALL DNS queries to the captive portal IP
    _dns.start(DISCOVERY_DNS_PORT, "*", IPAddress(192, 168, 4, 1));

    _server.on("/",      HTTP_GET,  _handleRoot);
    _server.on("/save",  HTTP_POST, _handleSave);
    _server.onNotFound(_handleRoot);   // captive-portal catch-all
    _server.begin();
}

// Run one iteration of the AP event loop.
// Returns true once the user has submitted the configuration form.
inline bool loop() {
    _dns.processNextRequest();
    _server.handleClient();
    return _configured;
}

// Stop the access point, DNS server and web server.
inline void stop() {
    _server.stop();
    _dns.stop();
    WiFi.softAPdisconnect(true);
    Serial.println("[AP] Access point stopped");
}

// Accessors for the values submitted via the form
inline bool     isConfigured() { return _configured; }
inline String   getSSID()      { return _result_ssid; }
inline String   getPass()      { return _result_pass; }
inline String   getHost()      { return _result_host; }
inline uint16_t getPort()      { return _result_port; }

} // namespace APModeServer

#endif // AP_MODE_SERVER_H
