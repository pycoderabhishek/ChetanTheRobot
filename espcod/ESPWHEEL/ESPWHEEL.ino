/*
 * AMHR-PD Wheel Controller
 * ESP32 Dev Module | L298N Motor Driver
 * 
 * Controls robot movement via WebSocket commands from FastAPI backend.
 * Status is reported to dashboard in real-time.
 */

#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// ============================== MOTOR PIN CONFIG ==============================

// Left Motor (L298N)
#define LEFT_MOTOR_EN   14    // PWM speed control
#define LEFT_MOTOR_IN1  27    // Direction pin 1
#define LEFT_MOTOR_IN2  26    // Direction pin 2

// Right Motor (L298N)
#define RIGHT_MOTOR_EN  32    // PWM speed control
#define RIGHT_MOTOR_IN1 25    // Direction pin 1
#define RIGHT_MOTOR_IN2 33    // Direction pin 2

// PWM Configuration
#define PWM_FREQ        5000
#define PWM_RESOLUTION  8     // 0-255
#define PWM_CHANNEL_L   0
#define PWM_CHANNEL_R   1

// ============================== NETWORK CONFIG ==============================

const char WIFI_SSID[] = "YOUR_SSID";  // TODO: Replace with your WiFi name
const char WIFI_PASSWORD[] = "YOUR_PASSWORD";  // TODO: Replace with your WiFi password

const char BACKEND_HOST[] = "10.83.60.93";  // Updated to current server IP
const uint16_t BACKEND_PORT = 8000;

const char DEVICE_ID[] = "wheelcontroller";
const char DEVICE_TYPE[] = "esp32";
const char FIRMWARE_VERSION[] = "1.0.0";

// ============================== STATE ==============================

enum SystemState {
  WIFI_CONNECTING,
  WIFI_CONNECTED,
  WS_CONNECTING,
  WS_CONNECTED
};

SystemState system_state = WIFI_CONNECTING;

// Motor state
int current_speed = 0;          // 0-255
String current_direction = "stopped";
bool motors_enabled = true;

// Timing
unsigned long last_heartbeat = 0;
const unsigned long HEARTBEAT_INTERVAL = 5000;

unsigned long last_status_update = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 1000;

// Safety: auto-stop if no command received
unsigned long last_command_time = 0;
const unsigned long COMMAND_TIMEOUT = 5000;  // Stop if no command for 5 seconds

WebSocketsClient webSocket;

// ============================== MOTOR FUNCTIONS ==============================

void setup_motors() {
  // Configure motor pins
  pinMode(LEFT_MOTOR_IN1, OUTPUT);
  pinMode(LEFT_MOTOR_IN2, OUTPUT);
  pinMode(RIGHT_MOTOR_IN1, OUTPUT);
  pinMode(RIGHT_MOTOR_IN2, OUTPUT);
  
  // Configure PWM for speed control
  ledcSetup(PWM_CHANNEL_L, PWM_FREQ, PWM_RESOLUTION);
  ledcSetup(PWM_CHANNEL_R, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(LEFT_MOTOR_EN, PWM_CHANNEL_L);
  ledcAttachPin(RIGHT_MOTOR_EN, PWM_CHANNEL_R);
  
  // Start with motors stopped
  stop_motors();
  
  Serial.println("[INIT] Motors initialized");
}

void set_motor_speed(int left_speed, int right_speed) {
  // Clamp speeds to valid range
  left_speed = constrain(left_speed, 0, 255);
  right_speed = constrain(right_speed, 0, 255);
  
  ledcWrite(PWM_CHANNEL_L, left_speed);
  ledcWrite(PWM_CHANNEL_R, right_speed);
  
  current_speed = (left_speed + right_speed) / 2;
}

void move_forward(int speed) {
  if (!motors_enabled) return;
  
  digitalWrite(LEFT_MOTOR_IN1, HIGH);
  digitalWrite(LEFT_MOTOR_IN2, LOW);
  digitalWrite(RIGHT_MOTOR_IN1, HIGH);
  digitalWrite(RIGHT_MOTOR_IN2, LOW);
  
  set_motor_speed(speed, speed);
  current_direction = "forward";
  
  Serial.printf("[MOTOR] Forward at speed %d\n", speed);
}

void move_backward(int speed) {
  if (!motors_enabled) return;
  
  digitalWrite(LEFT_MOTOR_IN1, LOW);
  digitalWrite(LEFT_MOTOR_IN2, HIGH);
  digitalWrite(RIGHT_MOTOR_IN1, LOW);
  digitalWrite(RIGHT_MOTOR_IN2, HIGH);
  
  set_motor_speed(speed, speed);
  current_direction = "backward";
  
  Serial.printf("[MOTOR] Backward at speed %d\n", speed);
}

void turn_left(int speed) {
  if (!motors_enabled) return;
  
  // Left motor backward, right motor forward
  digitalWrite(LEFT_MOTOR_IN1, LOW);
  digitalWrite(LEFT_MOTOR_IN2, HIGH);
  digitalWrite(RIGHT_MOTOR_IN1, HIGH);
  digitalWrite(RIGHT_MOTOR_IN2, LOW);
  
  set_motor_speed(speed, speed);
  current_direction = "left";
  
  Serial.printf("[MOTOR] Turn left at speed %d\n", speed);
}

void turn_right(int speed) {
  if (!motors_enabled) return;
  
  // Left motor forward, right motor backward
  digitalWrite(LEFT_MOTOR_IN1, HIGH);
  digitalWrite(LEFT_MOTOR_IN2, LOW);
  digitalWrite(RIGHT_MOTOR_IN1, LOW);
  digitalWrite(RIGHT_MOTOR_IN2, HIGH);
  
  set_motor_speed(speed, speed);
  current_direction = "right";
  
  Serial.printf("[MOTOR] Turn right at speed %d\n", speed);
}

void stop_motors() {
  digitalWrite(LEFT_MOTOR_IN1, LOW);
  digitalWrite(LEFT_MOTOR_IN2, LOW);
  digitalWrite(RIGHT_MOTOR_IN1, LOW);
  digitalWrite(RIGHT_MOTOR_IN2, LOW);
  
  set_motor_speed(0, 0);
  current_direction = "stopped";
  current_speed = 0;
  
  Serial.println("[MOTOR] Stopped");
}

// Tank drive: independent control of left and right motors
void tank_drive(int left_speed, int right_speed) {
  if (!motors_enabled) return;
  
  // Handle left motor direction
  if (left_speed >= 0) {
    digitalWrite(LEFT_MOTOR_IN1, HIGH);
    digitalWrite(LEFT_MOTOR_IN2, LOW);
  } else {
    digitalWrite(LEFT_MOTOR_IN1, LOW);
    digitalWrite(LEFT_MOTOR_IN2, HIGH);
    left_speed = -left_speed;
  }
  
  // Handle right motor direction
  if (right_speed >= 0) {
    digitalWrite(RIGHT_MOTOR_IN1, HIGH);
    digitalWrite(RIGHT_MOTOR_IN2, LOW);
  } else {
    digitalWrite(RIGHT_MOTOR_IN1, LOW);
    digitalWrite(RIGHT_MOTOR_IN2, HIGH);
    right_speed = -right_speed;
  }
  
  set_motor_speed(left_speed, right_speed);
  current_direction = "tank";
  
  Serial.printf("[MOTOR] Tank drive L:%d R:%d\n", left_speed, right_speed);
}

// ============================== WIFI ==============================

void setup_wifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  system_state = WIFI_CONNECTING;
  Serial.println("[WIFI] Connecting...");
}

// ============================== WEBSOCKET ==============================

void setup_websocket() {
  webSocket.begin(BACKEND_HOST, BACKEND_PORT, "/ws/wheelcontroller");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
  system_state = WS_CONNECTING;
  Serial.println("[WS] Connecting to backend...");
}

void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      system_state = WS_CONNECTED;
      send_registration();
      Serial.println("[WS] Connected and registered");
      break;

    case WStype_TEXT:
      handle_ws_message((char*)payload, length);
      break;

    case WStype_DISCONNECTED:
      system_state = WIFI_CONNECTED;
      stop_motors();  // Safety: stop on disconnect
      Serial.println("[WS] Disconnected - motors stopped");
      break;

    case WStype_ERROR:
      Serial.println("[WS] Error occurred");
      break;

    default:
      break;
  }
}

void send_registration() {
  StaticJsonDocument<256> reg;
  reg["message_type"] = "registration";
  reg["device_type"] = DEVICE_TYPE;

  JsonObject meta = reg.createNestedObject("metadata");
  meta["device_id"] = DEVICE_ID;
  meta["firmware_version"] = FIRMWARE_VERSION;
  meta["capabilities"] = "movement";

  String out;
  serializeJson(reg, out);
  webSocket.sendTXT(out);
}

void send_heartbeat() {
  StaticJsonDocument<64> hb;
  hb["message_type"] = "heartbeat";
  hb["device_type"] = DEVICE_TYPE;
  
  String out;
  serializeJson(hb, out);
  webSocket.sendTXT(out);
}

void send_status_update() {
  StaticJsonDocument<256> status;
  status["message_type"] = "status";
  status["device_type"] = DEVICE_TYPE;
  
  JsonObject payload = status.createNestedObject("payload");
  payload["direction"] = current_direction;
  payload["speed"] = current_speed;
  payload["motors_enabled"] = motors_enabled;
  payload["wifi_rssi"] = WiFi.RSSI();
  
  String out;
  serializeJson(status, out);
  webSocket.sendTXT(out);
}

// ============================== MESSAGE HANDLER ==============================

void handle_ws_message(char* payload, size_t len) {
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, payload, len);

  if (err) {
    Serial.printf("[WS] JSON parse failed: %s\n", err.c_str());
    return;
  }

  const char* message_type = doc["message_type"];
  if (!message_type) {
    Serial.println("[WS] Missing message_type");
    return;
  }

  // ===== COMMAND =====
  if (strcmp(message_type, "command") == 0) {
    Serial.println("[WS] Command received");
    last_command_time = millis();  // Reset timeout

    // Named command
    if (doc.containsKey("command_name")) {
      const char* cmd = doc["command_name"];
      int speed = doc["payload"]["speed"] | 200;  // Default speed 200
      
      Serial.printf("[WS] Movement command: %s (speed: %d)\n", cmd, speed);

      if (strcmp(cmd, "forward") == 0) move_forward(speed);
      else if (strcmp(cmd, "backward") == 0) move_backward(speed);
      else if (strcmp(cmd, "left") == 0) turn_left(speed);
      else if (strcmp(cmd, "right") == 0) turn_right(speed);
      else if (strcmp(cmd, "stop") == 0) stop_motors();
      else if (strcmp(cmd, "enable") == 0) { motors_enabled = true; Serial.println("[MOTOR] Enabled"); }
      else if (strcmp(cmd, "disable") == 0) { motors_enabled = false; stop_motors(); Serial.println("[MOTOR] Disabled"); }
      else Serial.printf("[WS] Unknown command: %s\n", cmd);
    }

    // Tank drive payload
    if (doc.containsKey("payload")) {
      JsonObject p = doc["payload"];
      if (p.containsKey("left_speed") && p.containsKey("right_speed")) {
        int left = p["left_speed"];
        int right = p["right_speed"];
        tank_drive(left, right);
      }
    }

    // Send ACK
    send_command_ack(doc["command_id"]);
  }
}

void send_command_ack(const char* command_id) {
  StaticJsonDocument<128> ack;
  ack["message_type"] = "command_ack";
  ack["device_type"] = DEVICE_TYPE;
  ack["command_id"] = command_id;
  ack["status"] = "success";

  String out;
  serializeJson(ack, out);
  webSocket.sendTXT(out);
}


// ============================== SETUP ==============================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================");
  Serial.println("  AMHR-PD Wheel Controller v1.0");
  Serial.println("  ESP32 + L298N Motor Driver");
  Serial.println("========================================\n");

  setup_motors();
  setup_wifi();
}

// ============================== LOOP ==============================

void loop() {
  // WiFi connection check
  if (WiFi.status() == WL_CONNECTED && system_state == WIFI_CONNECTING) {
    Serial.printf("[WIFI] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
    system_state = WIFI_CONNECTED;
    setup_websocket();
  }

  // Handle WebSocket
  webSocket.loop();

  // Send heartbeat
  if (system_state == WS_CONNECTED && millis() - last_heartbeat > HEARTBEAT_INTERVAL) {
    send_heartbeat();
    last_heartbeat = millis();
  }

  // Send periodic status update
  if (system_state == WS_CONNECTED && millis() - last_status_update > STATUS_UPDATE_INTERVAL) {
    send_status_update();
    last_status_update = millis();
  }

  // Safety timeout: stop motors if no command received
  if (current_direction != "stopped" && millis() - last_command_time > COMMAND_TIMEOUT) {
    Serial.println("[SAFETY] Command timeout - stopping motors");
    stop_motors();
  }
}