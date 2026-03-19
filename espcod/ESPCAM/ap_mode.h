/**
 * ap_mode.h
 * Fallback AP mode + captive portal.
 * If all auto-discovery methods fail, the ESP32 creates a WiFi hotspot
 * ("ChetanRobot_SETUP") and serves a web page at 192.168.4.1 where the
 * user can enter the backend's IP address.  The address is persisted to
 * NVS and the device reboots to reconnect normally.
 */

#pragma once

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include "eeprom_config.h"

#define AP_SSID        "ChetanRobot_SETUP"
#define AP_PASSWORD    ""          // Open AP — no password required
#define AP_IP          "192.168.4.1"
#define DNS_PORT       53
#define AP_TIMEOUT_MS  300000UL    // 5 minutes before auto-reboot

static const char AP_PAGE[] PROGMEM = R"rawhtml(
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width,initial-scale=1'>
  <title>ChetanRobot Setup</title>
  <style>
    body{font-family:sans-serif;max-width:400px;margin:40px auto;padding:0 16px;background:#1a1a2e;color:#eee}
    h2{color:#e94560}
    input[type=text],input[type=number]{width:100%;padding:10px;margin:8px 0;box-sizing:border-box;background:#16213e;border:1px solid #e94560;color:#eee;border-radius:4px}
    button{background:#e94560;color:#fff;border:none;padding:12px 24px;border-radius:4px;cursor:pointer;font-size:1em;width:100%}
    .note{font-size:0.85em;color:#aaa;margin-top:16px}
  </style>
</head>
<body>
  <h2>ChetanRobot Backend Setup</h2>
  <p>Enter the IP address of the machine running the backend server.</p>
  <form action='/save' method='POST'>
    <label>Backend IP Address</label>
    <input type='text' name='host' placeholder='e.g. 192.168.1.100' required>
    <label>Backend Port</label>
    <input type='number' name='port' value='8000' min='1' max='65535'>
    <br><br>
    <button type='submit'>Save &amp; Connect</button>
  </form>
  <p class='note'>After saving, the robot will reboot and connect automatically.</p>
</body>
</html>
)rawhtml";

static const char AP_SAVED_PAGE[] PROGMEM = R"rawhtml(
<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>Saved!</title>
<style>body{font-family:sans-serif;max-width:400px;margin:40px auto;background:#1a1a2e;color:#eee;text-align:center}
h2{color:#e94560}</style>
</head>
<body><h2>&#10003; Configuration Saved</h2><p>The robot will reboot and connect to your backend now.</p></body>
</html>
)rawhtml";

static DNSServer   _dnsServer;
static WebServer   _webServer(80);
static bool        _ap_config_saved = false;

static void _handleRoot() {
  _webServer.send_P(200, "text/html", AP_PAGE);
}

static void _handleSave() {
  if (_webServer.method() != HTTP_POST) {
    _webServer.send(405, "text/plain", "Method Not Allowed");
    return;
  }

  String host = _webServer.arg("host");
  String portStr = _webServer.arg("port");

  host.trim();
  if (host.length() == 0) {
    _webServer.send(400, "text/plain", "Host is required");
    return;
  }

  uint16_t port = portStr.length() > 0 ? (uint16_t)portStr.toInt() : 8000;
  if (port == 0) port = 8000;

  EEPROMConfig::saveHost(host.c_str(), port);
  _webServer.send_P(200, "text/html", AP_SAVED_PAGE);
  _ap_config_saved = true;
  Serial.printf("[AP] User configured backend: %s:%u\n", host.c_str(), port);
}

/**
 * Enter AP mode with captive portal.
 * Blocks until the user submits a valid backend address (or AP_TIMEOUT_MS elapses),
 * then reboots the device.
 */
void enter_ap_mode() {
  Serial.println("[AP] Entering AP mode — SSID: " AP_SSID);

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD);
  delay(500);

  IPAddress apIP(192, 168, 4, 1);
  WiFi.softAPConfig(apIP, apIP, IPAddress(255, 255, 255, 0));

  // Redirect all DNS queries to the AP IP (captive portal behaviour)
  _dnsServer.start(DNS_PORT, "*", apIP);

  _webServer.on("/", HTTP_GET,  _handleRoot);
  _webServer.on("/save", HTTP_POST, _handleSave);
  _webServer.onNotFound(_handleRoot);  // Captive portal catch-all
  _webServer.begin();

  Serial.printf("[AP] Captive portal running at http://%s\n", AP_IP);

  unsigned long start = millis();
  while (!_ap_config_saved && millis() - start < AP_TIMEOUT_MS) {
    _dnsServer.processNextRequest();
    _webServer.handleClient();
    delay(10);
  }

  if (!_ap_config_saved) {
    Serial.println("[AP] Timeout reached — rebooting");
  } else {
    Serial.println("[AP] Configuration saved — rebooting");
    delay(1500);
  }

  _webServer.stop();
  _dnsServer.stop();
  ESP.restart();
}
