# AMHR-PD Message Contracts (STEP 6)

Complete JSON protocol specification for AMHR-PD device communication.

---

## Overview

All messages between ESP32 devices and FastAPI backend use JSON format over WebSocket.

**Protocol**: JSON over WebSocket
**Connection**: `/ws/{device_id}`
**Port**: 8000 (default)
**Message Direction**: Bidirectional
**Encoding**: UTF-8
**Format**: JSON (single message per frame)

---

## Message Types

| Type | Direction | Purpose | Frequency |
|------|-----------|---------|-----------|
| `heartbeat` | Device → Server | Keep-alive signal | Every 5 seconds |
| `status` | Device → Server | Hardware state update | On-demand |
| `command` | Server → Device | Execute action | On-demand |
| `command_ack` | Device → Server | Command completion | On-command |
| `error` | Device ↔ Server | Error notification | On-error |
| `registration` | Device → Server | Device init | On-connect |

---

## 1. REGISTRATION MESSAGE

**Direction**: Device → Server (sent once on first connection)

**Purpose**: Register device with backend, provide metadata

**Timing**: Immediately after WebSocket connection established

### JSON Format
```json
{
  "message_type": "registration",
  "device_id": "esp32_kitchen_001",
  "device_type": "ESP32",
  "firmware_version": "1.0.0",
  "mac_address": "A4:CF:12:34:56:78",
  "ip_address": "192.168.1.100",
  "rssi": -45,
  "uptime": 0,
  "metadata": {
    "location": "Kitchen",
    "capabilities": ["blink_led", "read_temp", "test_hardware"],
    "hardware": {
      "has_led": true,
      "has_temp_sensor": true,
      "battery_capable": false
    }
  },
  "timestamp": 1705970400
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_type` | string | ✓ | Always: `"registration"` |
| `device_id` | string | ✓ | Unique device identifier (alphanumeric, hyphens, underscores) |
| `device_type` | string | ✓ | Device model: `ESP32`, `ESP32-S3`, `ESP32-CAM` |
| `firmware_version` | string | ✓ | Semantic version: `"1.0.0"` |
| `mac_address` | string | ✓ | MAC address format: `"A4:CF:12:34:56:78"` |
| `ip_address` | string | ✓ | Device IP address: `"192.168.1.100"` |
| `rssi` | integer | ✓ | WiFi signal strength: -120 to -30 dBm |
| `uptime` | integer | ✓ | Seconds since device boot |
| `metadata` | object | ✓ | Device capabilities and info (see below) |
| `timestamp` | integer | ✓ | Unix timestamp (seconds) |

### Metadata Object

```json
{
  "location": "Kitchen",
  "capabilities": [
    "blink_led",
    "read_temp",
    "test_hardware",
    "reboot"
  ],
  "hardware": {
    "has_led": true,
    "has_temp_sensor": true,
    "battery_capable": false,
    "features": ["wifi", "ble"]
  }
}
```

### Validation Rules
- `device_id`: 3-50 characters, alphanumeric + `-_`
- `device_type`: Must be in [ESP32, ESP32-S3, ESP32-CAM]
- `firmware_version`: Semantic version format `X.Y.Z`
- `mac_address`: 6 pairs of hex digits separated by colons
- `ip_address`: Valid IPv4 address
- `rssi`: Integer between -120 and -30
- `timestamp`: Unix timestamp (seconds, not milliseconds)
- `capabilities`: Array of strings, max 20 items

### Backend Response
Server acknowledges registration by adding device to registry. If device ID already exists, device is marked online and counters reset.

---

## 2. HEARTBEAT MESSAGE

**Direction**: Device → Server (sent every 5 seconds)

**Purpose**: Keep-alive signal, signal device is online

**Timing**: Every 5 seconds after registration

### JSON Format
```json
{
  "message_type": "heartbeat",
  "device_id": "esp32_kitchen_001",
  "device_type": "ESP32",
  "timestamp": 1705970405,
  "rssi": -48,
  "uptime": 5,
  "freeHeap": 180000
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_type` | string | ✓ | Always: `"heartbeat"` |
| `device_id` | string | ✓ | Same as registration |
| `device_type` | string | ✓ | Device model (ESP32, ESP32-S3, ESP32-CAM) |
| `timestamp` | integer | ✓ | Unix timestamp (seconds) |
| `rssi` | integer | ✗ | WiFi signal strength: -120 to -30 dBm |
| `uptime` | integer | ✗ | Seconds since device boot |
| `freeHeap` | integer | ✗ | Free heap memory in bytes |

### Validation Rules
- `message_type`: Must be exactly `"heartbeat"`
- `device_id`: Required and must match registered device
- `timestamp`: Current Unix timestamp (server checks if within ±30 seconds)
- `rssi`: If provided, must be -120 to -30
- `uptime`: If provided, must be non-negative
- `freeHeap`: If provided, must be positive

### Minimum Valid Heartbeat
```json
{
  "message_type": "heartbeat",
  "device_id": "esp32_kitchen_001",
  "device_type": "ESP32",
  "timestamp": 1705970405
}
```

### Server Behavior
- Updates `last_heartbeat` timestamp in device registry
- If device was offline, marks as online
- If heartbeat missing for 90+ seconds, marks device offline
- All heartbeats logged to database

---

## 3. STATE UPDATE MESSAGE

**Direction**: Device → Server (sent on-demand)

**Purpose**: Report current hardware state/sensor readings

**Timing**: After command execution or on-demand interval

### JSON Format
```json
{
  "message_type": "status",
  "device_id": "esp32_kitchen_001",
  "device_type": "ESP32",
  "timestamp": 1705970410,
  "payload": {
    "temperature": 23.5,
    "humidity": 45.2,
    "pressure": 1013.25,
    "light_level": 600,
    "battery": 87,
    "led_state": "on",
    "motion_detected": false,
    "uptime": 10,
    "freeHeap": 175000,
    "rssi": -50
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_type` | string | ✓ | Always: `"status"` |
| `device_id` | string | ✓ | Unique device identifier |
| `device_type` | string | ✓ | Device model |
| `timestamp` | integer | ✓ | Unix timestamp (seconds) |
| `payload` | object | ✓ | Hardware state/sensor data (see below) |

### Payload Object (Hardware-specific)

```json
{
  "temperature": 23.5,
  "humidity": 45.2,
  "pressure": 1013.25,
  "light_level": 600,
  "battery": 87,
  "led_state": "on",
  "motion_detected": false,
  "uptime": 10,
  "freeHeap": 175000,
  "rssi": -50,
  "gpio": {
    "D1": 1,
    "D2": 0,
    "D3": 1
  }
}
```

### Payload Field Types

| Field | Type | Range/Values | Description |
|-------|------|--------------|-------------|
| `temperature` | float | -40 to 125 | Celsius |
| `humidity` | float | 0 to 100 | Percent |
| `pressure` | float | 300 to 1100 | hPa |
| `light_level` | integer | 0 to 4095 | ADC value |
| `battery` | integer | 0 to 100 | Percent |
| `led_state` | string | "on" / "off" | LED state |
| `motion_detected` | boolean | true / false | Motion sensor |
| `uptime` | integer | 0+ | Seconds |
| `freeHeap` | integer | 0+ | Bytes |
| `rssi` | integer | -120 to -30 | dBm |
| `gpio` | object | varies | GPIO pin states |

### Validation Rules
- `payload` must contain at least 1 field
- `payload` can contain any custom fields (for extensibility)
- Numeric values should be reasonable ranges
- String values must be lowercase or match enum values
- Boolean values must be true/false (not 0/1)
- `timestamp`: Should be close to current Unix time (±5 seconds tolerance)

### Minimal State Update
```json
{
  "message_type": "status",
  "device_id": "esp32_kitchen_001",
  "device_type": "ESP32",
  "timestamp": 1705970410,
  "payload": {
    "led_state": "on",
    "temperature": 23.5
  }
}
```

### Server Behavior
- Creates `device_state_snapshot` record
- Updates in-memory state manager
- Available via `/api/state-history` endpoint
- Latest state shown in dashboard

---

## 4. COMMAND REQUEST MESSAGE

**Direction**: Server → Device (initiated by backend)

**Purpose**: Request device to execute an action

**Timing**: When command is sent via `/api/command` endpoint

### JSON Format
```json
{
  "message_type": "command",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_type": "ESP32",
  "command_name": "test_hardware",
  "payload": {
    "duration": 5,
    "intensity": 80
  },
  "timestamp": 1705970420,
  "timeout": 30
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_type` | string | ✓ | Always: `"command"` |
| `command_id` | string | ✓ | UUID v4 unique command ID |
| `device_type` | string | ✓ | Target device type (broadcasts to all of type) |
| `command_name` | string | ✓ | Action to execute (alphanumeric, underscores) |
| `payload` | object | ✗ | Command parameters/arguments |
| `timestamp` | integer | ✓ | Unix timestamp when command created |
| `timeout` | integer | ✓ | Seconds to wait for ACK (default: 30) |

### Valid Command Names

| Command | Payload | Purpose |
|---------|---------|---------|
| `test_hardware` | `{duration, intensity}` | Run hardware diagnostics |
| `blink` | `{count: 5, delay: 500}` | Blink LED |
| `reboot` | `{}` | Restart device |
| `get_status` | `{}` | Request state update |
| `calibrate` | `{sensor: "temp"}` | Calibrate sensor |
| `led_on` | `{}` | Turn LED on |
| `led_off` | `{}` | Turn LED off |

### Validation Rules
- `command_id`: Must be valid UUID v4 format
- `command_name`: 3-50 characters, alphanumeric + underscores, lowercase
- `payload`: If present, must be object (can be empty)
- `timeout`: Integer 1-300 seconds
- `timestamp`: Should match current time (±30 seconds)
- `device_type`: Must match registered devices

### Example: Test Hardware Command
```json
{
  "message_type": "command",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_type": "ESP32",
  "command_name": "test_hardware",
  "payload": {
    "duration": 5,
    "intensity": 80
  },
  "timestamp": 1705970420,
  "timeout": 30
}
```

### Example: Reboot Command
```json
{
  "message_type": "command",
  "command_id": "550e8400-e29b-41d4-a716-446655440001",
  "device_type": "ESP32-S3",
  "command_name": "reboot",
  "payload": {},
  "timestamp": 1705970420,
  "timeout": 60
}
```

### Server Behavior
- Routes to all connected devices of `device_type`
- Logs command to database
- Marks command status as "sent"
- Waits for ACK up to `timeout` seconds
- Updates command status based on ACK received

---

## 5. COMMAND RESPONSE MESSAGE

**Direction**: Device → Server (response to command)

**Purpose**: Report command execution result

**Timing**: After command execution completes

### JSON Format
```json
{
  "message_type": "command_ack",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "esp32_kitchen_001",
  "device_type": "ESP32",
  "status": "success",
  "timestamp": 1705970425,
  "execution_time": 5.2,
  "payload": {
    "test_results": {
      "led": "pass",
      "temp_sensor": "pass",
      "memory": "pass"
    },
    "details": "All systems operational"
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_type` | string | ✓ | Always: `"command_ack"` |
| `command_id` | string | ✓ | UUID from original command |
| `device_id` | string | ✓ | Device that executed command |
| `device_type` | string | ✓ | Device model |
| `status` | string | ✓ | Result: success / failure / error |
| `timestamp` | integer | ✓ | Unix timestamp when ACK sent |
| `execution_time` | float | ✗ | Seconds to execute (with decimals) |
| `payload` | object | ✗ | Command result data |

### Status Values

| Status | Meaning | Description |
|--------|---------|-------------|
| `success` | ✓ | Command executed successfully |
| `failure` | ✗ | Command failed (recoverable) |
| `error` | ⚠ | Command error (unrecoverable) |
| `timeout` | ⏱ | Command execution timeout |

### Payload Object (Result-specific)

```json
{
  "test_results": {
    "led": "pass",
    "temp_sensor": "pass",
    "memory": "pass"
  },
  "details": "All systems operational",
  "metrics": {
    "temperature": 23.5,
    "led_brightness": 100,
    "response_time": 250
  }
}
```

### Validation Rules
- `command_id`: Must match original command UUID
- `device_id`: Must match device registry
- `status`: Must be one of [success, failure, error, timeout]
- `timestamp`: Should be current Unix time (±5 seconds)
- `execution_time`: If present, must be positive float
- `payload`: Can be any object structure

### Example: Test Hardware Success
```json
{
  "message_type": "command_ack",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "esp32_kitchen_001",
  "device_type": "ESP32",
  "status": "success",
  "timestamp": 1705970425,
  "execution_time": 5.2,
  "payload": {
    "test_results": {
      "led": "pass",
      "temp_sensor": "pass",
      "memory": "pass"
    }
  }
}
```

### Example: Command Failure
```json
{
  "message_type": "command_ack",
  "command_id": "550e8400-e29b-41d4-a716-446655440001",
  "device_id": "esp32_bedroom_002",
  "device_type": "ESP32-S3",
  "status": "failure",
  "timestamp": 1705970425,
  "execution_time": 0.5,
  "payload": {
    "error": "Sensor not detected",
    "code": "SENSOR_NOT_FOUND"
  }
}
```

### Server Behavior
- Matches `command_id` with command log
- Updates command status to `ack_success` or `ack_error`
- Stores response payload
- Increments success/failure counters
- Logs to database and dashboard

---

## 6. ERROR RESPONSE MESSAGE

**Direction**: Device ↔ Server (sent when error occurs)

**Purpose**: Report protocol/execution errors

**Timing**: When error detected (any time)

### JSON Format
```json
{
  "message_type": "error",
  "device_id": "esp32_kitchen_001",
  "device_type": "ESP32",
  "error_code": "INVALID_MESSAGE",
  "error_message": "Unknown message type: 'invalid'",
  "timestamp": 1705970430,
  "context": {
    "received_message_type": "invalid",
    "received_length": 512,
    "uptime": 30
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_type` | string | ✓ | Always: `"error"` |
| `device_id` | string | ✓ | Device where error occurred |
| `device_type` | string | ✓ | Device model |
| `error_code` | string | ✓ | Machine-readable error code |
| `error_message` | string | ✓ | Human-readable error description |
| `timestamp` | integer | ✓ | Unix timestamp when error occurred |
| `context` | object | ✗ | Additional error context |

### Standard Error Codes

| Code | HTTP Equiv | Description |
|------|-----------|-------------|
| `INVALID_MESSAGE` | 400 | Malformed JSON or invalid structure |
| `UNKNOWN_MESSAGE_TYPE` | 400 | Unknown `message_type` value |
| `MISSING_REQUIRED_FIELD` | 400 | Required field missing |
| `INVALID_FIELD_TYPE` | 400 | Field type mismatch |
| `INVALID_FIELD_VALUE` | 400 | Field value out of range |
| `UNAUTHORIZED` | 401 | Device not registered |
| `COMMAND_NOT_FOUND` | 404 | Command ID doesn't exist |
| `EXECUTION_ERROR` | 500 | Command execution failed |
| `SENSOR_ERROR` | 500 | Sensor reading failed |
| `CONNECTION_TIMEOUT` | 504 | Server connection timeout |
| `PROTOCOL_VERSION_MISMATCH` | 400 | Incompatible protocol version |
| `RESOURCE_EXHAUSTED` | 429 | Memory/resource limit reached |

### Validation Rules
- `error_code`: UPPERCASE_WITH_UNDERSCORES format
- `error_message`: < 200 characters
- `timestamp`: Current Unix time
- `context`: Optional, any object structure
- If device not recognized, don't include `device_id`

### Example: Malformed JSON
```json
{
  "message_type": "error",
  "error_code": "INVALID_MESSAGE",
  "error_message": "Failed to parse JSON: Unexpected token",
  "timestamp": 1705970430
}
```

### Example: Missing Field
```json
{
  "message_type": "error",
  "device_id": "esp32_kitchen_001",
  "device_type": "ESP32",
  "error_code": "MISSING_REQUIRED_FIELD",
  "error_message": "Required field missing: 'payload'",
  "timestamp": 1705970430,
  "context": {
    "missing_field": "payload",
    "received_fields": ["message_type", "device_id", "timestamp"]
  }
}
```

### Example: Sensor Error
```json
{
  "message_type": "error",
  "device_id": "esp32_sensor_003",
  "device_type": "ESP32",
  "error_code": "SENSOR_ERROR",
  "error_message": "Temperature sensor read timeout",
  "timestamp": 1705970430,
  "context": {
    "sensor": "DHT22",
    "attempts": 3,
    "last_reading": 22.5
  }
}
```

### Server Behavior
- Logs error to error log
- Updates device status if appropriate
- Does not require response
- Continues processing other messages
- May trigger alert if critical

---

## Message Flow Diagram

### Typical Session Flow

```
Device                              Server
  |                                   |
  |--- WebSocket Connect -----------→ |
  |                                   |
  |--- Registration Message -------→ |
  |                                   | (Add to registry)
  |                                   |
  |--- Heartbeat (5s interval) ----→ | (Mark online)
  |                                   |
  |← ← ← Command (from /api) ← ← ← |
  |                                   |
  | (Execute test_hardware)           |
  |                                   |
  |--- Command ACK ----------------→ | (Log result)
  |                                   |
  |--- State Update (optional) ----→ | (Save snapshot)
  |                                   |
  |--- Heartbeat ----------------→ |
  |                                   |
  | (Heartbeat: 5s, no response)    |
  |                                   |
  |--- Heartbeat ----------------→ |
  |                                   |
  |← ← ← Error Message ← ← ← ← ← |
  |                                   |
  |--- Error ACK ----------------→ |
  |                                   |
  |--- Heartbeat (90+ sec timeout)   | (Mark offline)
  |                                   |
```

### Error Handling Flow

```
Device                              Server
  |                                   |
  | Send malformed JSON              |
  |------ (invalid) -------→         |
  |                                   | (Parse error)
  |←----- Error Message -----←       |
  |                                   |
  | Send unknown message type        |
  |------ {msg_type: "foo"} -------→ |
  |                                   | (Unknown type)
  |←------ Error: UNKNOWN_MESSAGE_TYPE ←|
  |                                   |
```

---

## Data Types Reference

### String
- UTF-8 encoded
- Max 255 characters (unless specified)
- Lowercase preferred for IDs and codes

### Integer
- 64-bit signed integer
- Unix timestamps in seconds (not milliseconds)
- Range: -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807

### Float
- 32-bit IEEE 754 floating point
- Decimals for precise values (temperature, time, etc.)
- Example: 23.5, -45.2, 1013.25

### Boolean
- true or false (lowercase, not 0/1)
- Example: `"motion_detected": true`

### Object
- JSON object with key-value pairs
- Keys must be strings, quoted
- Values can be any JSON type
- No trailing commas

### Array
- Ordered list of values
- Can contain mixed types (discouraged)
- Example: `["value1", "value2", "value3"]`

### UUID v4
- 36-character string with hyphens
- Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- Example: `550e8400-e29b-41d4-a716-446655440000`

---

## Validation & Error Handling

### Message Validation Order

1. **JSON Parse** - Valid JSON syntax?
2. **Message Type** - Known message type?
3. **Required Fields** - All required fields present?
4. **Field Types** - Each field correct type?
5. **Field Values** - Field values valid ranges?
6. **Semantic** - Cross-field validation?
7. **Authorization** - Device registered?

### Device-Side Validation

```
Receive message:
  → Parse JSON
  → Check message_type
  → Validate required fields
  → Check field types
  → Validate field values
  → Execute command
  → Send ACK or Error
```

### Server-Side Validation

```
Receive message:
  → Parse JSON
  → Check device registered
  → Check message_type
  → Validate all fields
  → Check timestamp (±30 sec tolerance)
  → Process message
  → Update database
  → Send response if needed
```

### Timeout Behavior

| Scenario | Timeout | Action |
|----------|---------|--------|
| Command ACK missing | 30s (default) | Mark as timeout, retry or fail |
| Heartbeat missing | 90s | Mark device offline |
| Connection inactive | 300s | Close WebSocket |
| Message processing | 5s | Discard, log error |

---

## Examples by Scenario

### Scenario 1: Device Registers and Sends Heartbeat

**Device connects and registers:**
```json
{
  "message_type": "registration",
  "device_id": "esp32_living_room_001",
  "device_type": "ESP32",
  "firmware_version": "1.0.0",
  "mac_address": "A4:CF:12:34:56:78",
  "ip_address": "192.168.1.100",
  "rssi": -45,
  "uptime": 0,
  "metadata": {
    "location": "Living Room",
    "capabilities": ["blink_led", "test_hardware"],
    "hardware": {
      "has_led": true,
      "has_temp_sensor": false
    }
  },
  "timestamp": 1705970400
}
```

**Server adds to registry, device begins sending heartbeats (every 5 seconds):**
```json
{
  "message_type": "heartbeat",
  "device_id": "esp32_living_room_001",
  "device_type": "ESP32",
  "timestamp": 1705970405,
  "rssi": -46,
  "uptime": 5,
  "freeHeap": 180000
}
```

### Scenario 2: Server Sends Test Command

**User clicks "Test All" on dashboard → POST to `/api/command`:**
```json
{
  "message_type": "command",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_type": "ESP32",
  "command_name": "test_hardware",
  "payload": {
    "duration": 5,
    "intensity": 80
  },
  "timestamp": 1705970420,
  "timeout": 30
}
```

**Device receives, executes, sends back result:**
```json
{
  "message_type": "command_ack",
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "esp32_living_room_001",
  "device_type": "ESP32",
  "status": "success",
  "timestamp": 1705970425,
  "execution_time": 5.2,
  "payload": {
    "test_results": {
      "led": "pass",
      "memory": "pass",
      "connectivity": "pass"
    },
    "free_heap": 175000
  }
}
```

**Server logs, updates dashboard, marks command success.**

### Scenario 3: State Update After Command

**Device sends updated hardware state:**
```json
{
  "message_type": "status",
  "device_id": "esp32_living_room_001",
  "device_type": "ESP32",
  "timestamp": 1705970426,
  "payload": {
    "led_state": "off",
    "uptime": 26,
    "freeHeap": 174000,
    "rssi": -47
  }
}
```

**Server creates snapshot, updates in-memory state, available in `/api/state-history`.**

### Scenario 4: Error During Command Execution

**Device encounters error while executing command:**
```json
{
  "message_type": "command_ack",
  "command_id": "550e8400-e29b-41d4-a716-446655440001",
  "device_id": "esp32_bedroom_002",
  "device_type": "ESP32-S3",
  "status": "error",
  "timestamp": 1705970450,
  "execution_time": 0.3,
  "payload": {
    "error": "Sensor not initialized",
    "code": "SENSOR_INIT_FAILED"
  }
}
```

**Server logs error, updates command status to `ack_error`, shows in dashboard activity log.**

### Scenario 5: Protocol Error

**Device receives malformed command (missing field):**
```json
{
  "message_type": "error",
  "device_id": "esp32_kitchen_003",
  "device_type": "ESP32",
  "error_code": "INVALID_MESSAGE",
  "error_message": "Missing required field: command_id",
  "timestamp": 1705970460,
  "context": {
    "missing_field": "command_id",
    "received_fields": ["message_type", "device_type", "command_name"]
  }
}
```

**Server logs error, does not process malformed command, may retry.**

---

## Protocol Compliance Checklist

### Device Implementation

- [ ] JSON parsing/generation
- [ ] Send registration on connect
- [ ] Send heartbeat every 5 seconds
- [ ] Validate incoming commands
- [ ] Execute commands safely
- [ ] Send command ACK with results
- [ ] Handle connection loss gracefully
- [ ] Reconnect automatically
- [ ] Send state updates as needed
- [ ] Error handling and reporting

### Server Implementation

- [ ] Accept WebSocket connections
- [ ] Parse JSON messages
- [ ] Validate all fields
- [ ] Register devices
- [ ] Track heartbeats
- [ ] Mark devices offline after 90s
- [ ] Route commands by device_type
- [ ] Log all operations
- [ ] Store state snapshots
- [ ] Respond to errors
- [ ] Cleanup disconnected clients

---

## Performance Guidelines

| Metric | Target | Limit |
|--------|--------|-------|
| Message size | <1KB | 10KB max |
| Heartbeat interval | 5s | 1-60s configurable |
| Command timeout | 30s | 1-300s configurable |
| State update frequency | On-demand | ≤1 per second |
| Connection setup | <500ms | <2s |
| Message processing | <10ms | <100ms |
| Database query | <10ms | <100ms |

---

## Future Protocol Versions

### Protocol Versioning Strategy

Each message can include optional protocol version field:

```json
{
  "protocol_version": "1.0",
  "message_type": "heartbeat",
  ...
}
```

### Version 1.0 (Current)
- Basic message types
- JSON over WebSocket
- Device registration
- Command/response pattern

### Version 1.1 (Planned)
- Message compression
- Batched heartbeats
- Command queueing
- Rate limiting

### Version 2.0 (Future)
- Binary protocol option
- Encryption support
- Message signing
- Session persistence

---

## Security Considerations

### Current Implementation
- No authentication
- No encryption
- Device trust based on connection
- Server-side validation only

### Recommendations for Production

1. **Add TLS/SSL** - Use WSS (WebSocket Secure)
2. **Device Authentication** - API key or certificate
3. **Message Signing** - HMAC validation
4. **Rate Limiting** - Per-device limits
5. **Input Sanitization** - Strict validation
6. **Timeout Protection** - Prevent hanging connections
7. **Logging** - Audit trail of all messages

---

## Testing Checklist

### Unit Tests

- [ ] JSON parsing valid messages
- [ ] JSON parsing invalid messages
- [ ] Field validation for each type
- [ ] Timestamp validation (±30s)
- [ ] UUID validation
- [ ] Device ID validation
- [ ] Command name validation

### Integration Tests

- [ ] Device registration flow
- [ ] Heartbeat persistence
- [ ] Command broadcast
- [ ] Command ACK timeout
- [ ] State snapshot storage
- [ ] Error logging
- [ ] Connection recovery
- [ ] Offline detection

### Load Tests

- [ ] 100 devices heartbeating
- [ ] 1000 commands/minute
- [ ] Large state payloads (5KB)
- [ ] Concurrent connections
- [ ] Memory under load
- [ ] Database query performance

---

## Summary

**Message Contract Specification Complete**

All AMHR-PD messages now have:
✓ JSON format defined
✓ Field descriptions documented
✓ Validation rules specified
✓ Error codes standardized
✓ Examples provided
✓ Protocol flows illustrated

**Total message types**: 6
**Total fields**: 50+
**Total error codes**: 12
**Total examples**: 10+

Ready for implementation and testing!

---

**Document Version**: 1.0
**Protocol Version**: 1.0
**Last Updated**: January 24, 2026
**Status**: Complete & Ready for Development
