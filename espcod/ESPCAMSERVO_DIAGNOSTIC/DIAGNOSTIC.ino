/*
 * STANDALONE DIAGNOSTIC SKETCH
 * 
 * Place in: e:\Desktop\new\New folder\ChetanTheRobot\espcod\ESPCAMSERVO_DIAGNOSTIC\DIAGNOSTIC.ino
 * 
 * This REPLACES the normal code - use for troubleshooting ONLY
 * After diagnosis, go back to ESPCAMSERVO.ino
 */

#include <WiFi.h>
#include <Preferences.h>

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================");
  Serial.println("  DIAGNOSTIC MODE - CLEAR & AP ONLY");
  Serial.println("  ESP32-S3 N16R8");
  Serial.println("========================================\n");

  // Read MAC BEFORE WiFi mode change
  delay(100);
  WiFi.mode(WIFI_STA);
  delay(100);
  
  uint8_t mac[6];
  WiFi.macAddress(mac);
  Serial.printf("[MAC] MAC Address: %02X:%02X:%02X:%02X:%02X:%02X\n",
                mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  Serial.printf("[DEVICE_ID] espcontroller_%02X%02X%02X\n",
                mac[3], mac[4], mac[5]);

  // CLEAR EEPROM
  Serial.println("\n[EEPROM] Clearing all stored configuration...");
  Preferences prefs;
  prefs.begin("chetanrobot", false);
  prefs.clear();
  prefs.end();
  Serial.println("[EEPROM] ✓ Cleared\n");

  // FORCE AP MODE
  Serial.println("[SETUP] Launching AP mode immediately...\n");
  
  WiFi.mode(WIFI_AP);
  delay(100);
  
  WiFi.softAPConfig(
    IPAddress(192, 168, 4, 1),
    IPAddress(192, 168, 4, 1),
    IPAddress(255, 255, 255, 0)
  );

  char ap_ssid[36];
  snprintf(ap_ssid, sizeof(ap_ssid), "ChetanRobot_SETUP_%02X%02X",
           mac[4], mac[5]);

  // Use password
  const char* ap_password = "ChetanRobot123";
  
  bool ap_ok = WiFi.softAP(ap_ssid, ap_password);
  
  Serial.printf("[AP] softAP() returned: %s\n", ap_ok ? "TRUE" : "FALSE");
  Serial.printf("[AP] SSID: '%s'\n", ap_ssid);
  Serial.printf("[AP] Password: '%s'\n", ap_password);
  Serial.printf("[AP] IP: %s\n", WiFi.softAPIP().toString().c_str());
  
  // Get AP info
  int devices = WiFi.softAPgetStationNum();
  Serial.printf("[AP] Connected stations: %d\n", devices);
  
  IPAddress ip = WiFi.softAPIP();
  IPAddress broadcast = IPAddress(ip[0], ip[1], ip[2], 255);
  Serial.printf("[AP] Broadcast IP: %s\n", broadcast.toString().c_str());

  Serial.println("\n========================================");
  Serial.println("DIAGNOSTIC COMPLETE");
  Serial.println("========================================\n");
  
  Serial.println("[INSTRUCTIONS]");
  Serial.printf("1. Look for WiFi: '%s'\n", ap_ssid);
  Serial.println("2. Password: 'ChetanRobot123'");
  Serial.println("3. Connect from Windows 11");
  Serial.println("4. Open browser: http://192.168.4.1");
  Serial.println("\nWatching for connections...\n");
}

void loop() {
  // Print connected clients every 5 seconds
  static unsigned long last_report = 0;
  
  if (millis() - last_report > 5000) {
    int num_clients = WiFi.softAPgetStationNum();
    if (num_clients > 0) {
      Serial.printf("[AP] ✓ Device(s) connected: %d\n", num_clients);
    }
    last_report = millis();
  }
  
  delay(100);
}
