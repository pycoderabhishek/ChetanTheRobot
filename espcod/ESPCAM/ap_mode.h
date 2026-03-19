/**
 * ap_mode.h
 * Emergency fallback: if all automatic discovery layers fail, the ESP32
 * creates a WiFi access point "ChetanRobot_SETUP" and serves a simple
 * captive portal at http://192.168.4.1 where the user can enter the
 * backend IP address manually.
 *
 * Requires: WebServer.h and DNSServer.h (both built into ESP32 Arduino SDK).
 */

#pragma once
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>

#define AP_SSID         "ChetanRobot_SETUP"
#define AP_PASSWORD     ""           // Open AP — no password
#define AP_LOCAL_IP     "192.168.4.1"
#define AP_DNS_PORT     53
#define AP_HTTP_PORT    80
#define AP_TIMEOUT_MS   300000       // 5-minute window before giving up

// ---- HTML pages ----

static const char AP_PAGE_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Chetan Robot Setup</title>
<style>
  body{font-family:sans-serif;background:#1a1a2e;color:#eee;display:flex;
       justify-content:center;align-items:center;min-height:100vh;margin:0}
  .card{background:#16213e;border-radius:12px;padding:2rem;width:320px;
        box-shadow:0 4px 24px #0004}
  h2{margin-top:0;color:#e94560}
  label{display:block;margin:.8rem 0 .3rem}
  input{width:100%;box-sizing:border-box;padding:.6rem;border-radius:6px;
        border:1px solid #444;background:#0f3460;color:#eee;font-size:1rem}
  button{margin-top:1.2rem;width:100%;padding:.75rem;border:none;
         border-radius:6px;background:#e94560;color:#fff;font-size:1rem;
         cursor:pointer}
  .note{margin-top:1rem;font-size:.8rem;color:#aaa}
</style>
</head>
<body>
<div class='card'>
  <h2>🤖 Chetan Robot Setup</h2>
  <p>Enter your backend server details:</p>
  <form action='/save' method='POST'>
    <label>Backend IP Address</label>
    <input type='text' name='host' placeholder='e.g. 192.168.1.100' required>
    <label>Port</label>
    <input type='number' name='port' value='8000' min='1' max='65535'>
    <button type='submit'>Save &amp; Connect</button>
  </form>
  <p class='note'>After saving, the device will reboot and connect automatically.</p>
</div>
</body>
</html>
)rawliteral";

static const char AP_PAGE_SAVED[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Saved!</title>
<style>body{font-family:sans-serif;background:#1a1a2e;color:#eee;
  display:flex;justify-content:center;align-items:center;min-height:100vh}</style>
</head>
<body>
<div style='text-align:center'>
  <h2 style='color:#4ecca3'>✅ Configuration Saved!</h2>
  <p>Device will restart and connect to the backend.</p>
</div>
</body>
</html>
)rawliteral";

// ---- AP mode implementation ----

static WebServer  _ap_server(AP_HTTP_PORT);
static DNSServer  _dns_server;
static String     _ap_result_host = "";
static uint16_t   _ap_result_port = 8000;
static bool       _ap_config_saved = false;

static void _ap_handle_root() {
    _ap_server.send_P(200, "text/html", AP_PAGE_HTML);
}

static void _ap_handle_save() {
    if (_ap_server.hasArg("host") && _ap_server.arg("host").length() > 0) {
        _ap_result_host = _ap_server.arg("host");
        _ap_result_host.trim();
        if (_ap_server.hasArg("port")) {
            _ap_result_port = (uint16_t)_ap_server.arg("port").toInt();
        }
        _ap_config_saved = true;
        _ap_server.send_P(200, "text/html", AP_PAGE_SAVED);
        Serial.printf("[AP] User configured backend: %s:%u\n",
                      _ap_result_host.c_str(), _ap_result_port);
    } else {
        _ap_server.send(400, "text/plain", "Missing 'host' parameter");
    }
}

/**
 * Start AP mode, serve the captive portal and block until the user provides
 * a backend address OR the timeout expires.
 *
 * On success: writes host/port and returns true.
 * On timeout: returns false.
 */
bool ap_mode_start(String& host, uint16_t& port) {
    Serial.println("[AP] Starting access point: " AP_SSID);

    WiFi.softAP(AP_SSID, AP_PASSWORD);
    delay(500);

    IPAddress apIP(192, 168, 4, 1);
    WiFi.softAPConfig(apIP, apIP, IPAddress(255, 255, 255, 0));

    // Redirect all DNS queries to the portal IP (captive portal trick)
    _dns_server.start(AP_DNS_PORT, "*", apIP);

    _ap_server.on("/",     HTTP_GET,  _ap_handle_root);
    _ap_server.on("/save", HTTP_POST, _ap_handle_save);
    // Catch-all for captive-portal detection requests
    _ap_server.onNotFound([]() {
        _ap_server.sendHeader("Location", "http://" AP_LOCAL_IP, true);
        _ap_server.send(302, "text/plain", "");
    });
    _ap_server.begin();

    Serial.println("[AP] Portal running at http://" AP_LOCAL_IP);
    Serial.printf("[AP] Waiting up to %lu seconds for user input...\n",
                  (unsigned long)(AP_TIMEOUT_MS / 1000));

    unsigned long start = millis();
    while (!_ap_config_saved && millis() - start < AP_TIMEOUT_MS) {
        _dns_server.processNextRequest();
        _ap_server.handleClient();
        delay(10);
    }

    _ap_server.stop();
    _dns_server.stop();
    WiFi.softAPdisconnect(true);

    if (_ap_config_saved) {
        host = _ap_result_host;
        port = _ap_result_port;
        Serial.printf("[AP] Configuration received: %s:%u\n", host.c_str(), port);
        return true;
    }

    Serial.println("[AP] Timeout — no configuration received");
    return false;
}
