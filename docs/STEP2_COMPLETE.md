# STEP 2 — FASTAPI SERVO CONTROL SERVER

**Status:** COMPLETE  
**Date:** January 26, 2026

---

## Overview

STEP 2 implements a professional FastAPI backend that:

- **Accepts WebSocket connections** from the ESP32
- **Validates device registration** (verifies "servoscontroller")
- **Manages servo state** in memory (current and target angles)
- **Routes servo commands** to ESP32 via WebSocket
- **Collects state feedback** from ESP32 and updates local cache
- **Exposes REST endpoints** for command and query operations

---

## Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────┐
│  FastAPI Application (main.py)          │
│  - REST endpoints                       │
│  - WebSocket endpoint                   │
│  - CORS middleware                      │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│  Route Layer (devices/routes.py)        │
│  - POST /servo/set                      │
│  - GET /servo/state/{channel}           │
│  - GET /servo/all                       │
│  - POST /servo/reset                    │
│  - GET /servo/health                    │
│  - WebSocket /ws/servo                  │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│  Manager Layer                          │
│  ├─ ServoStateManager (devices/servo_   │
│  │  state.py)                           │
│  │  - In-memory servo state              │
│  │  - Thread-safe (asyncio.Lock)        │
│  │  - Initialize, set angle, feedback   │
│  │                                       │
│  └─ ServoWebSocketManager               │
│     (websocket/servo_manager.py)        │
│     - Device registration               │
│     - Connection tracking               │
│     - Message dispatch                  │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│  Data Layer                             │
│  - ServoConfig (servo_config.py)        │
│  - ServoController (conversions)        │
└─────────────────────────────────────────┘
```

---

## Component 1: ServoStateManager

**File**: `app/devices/servo_state.py`

Maintains in-memory state of all 10 servos with thread-safe access.

### Class: `ServoStateManager`

**Attributes**:
- `servo_configs`: Dict[int, ServoConfig] – Configuration for each servo
- `controller`: ServoController – Conversion logic (angle ↔ ticks)
- `states`: Dict[int, ServoState] – Current runtime state
- `lock`: asyncio.Lock – Thread-safe access
- `last_updated`: datetime – Last state modification

**Key Methods**:

```python
async def initialize():
    """Initialize all servos to home position (90°)"""

async def set_target_angle(channel: int, angle: float) -> ServoState:
    """Set target angle, clamps to safe range, calculates PWM"""

async def update_current_angle(channel: int, angle: float) -> ServoState:
    """Update feedback from ESP32, tracks motion"""

async def set_error(channel: int, error_msg: str) -> ServoState:
    """Record error condition"""

async def get_state(channel: int) -> ServoState:
    """Get single servo state"""

async def get_all_states() -> Dict[int, ServoState]:
    """Get all servo states"""
```

### Example Usage

```python
# Initialize
state_mgr = await get_servo_state_manager()

# Set servo 0 to 120 degrees
state = await state_mgr.set_target_angle(channel=0, angle=120.0)
print(f"Ticks: {state.pca9685_ticks}")  # 369 for 120°

# ESP32 sends feedback: "servo at 119.5°"
await state_mgr.update_current_angle(channel=0, angle=119.5)

# Check if moving
state = await state_mgr.get_state(0)
print(f"Moving: {state.is_moving}")  # False (close to target)
```

---

## Component 2: ServoWebSocketManager

**File**: `app/websocket/servo_manager.py`

Manages WebSocket connections to ESP32 and message routing.

### Classes

#### `WebSocketMessage`
Generic message wrapper for all WebSocket communications:

```json
{
  "type": "register|command|feedback|error|ack|ping|pong",
  "data": {...}
}
```

#### `DeviceRegistration`
Sent by ESP32 to identify itself:

```json
{
  "device_id": "servoscontroller",
  "device_type": "esp32s3",
  "firmware_version": "1.0.0"
}
```

#### `ServoCommand`
Sent by backend to ESP32:

```json
{
  "channel": 0,
  "angle": 90.0
}
```

#### `ServoFeedback`
Sent by ESP32 to backend (state update):

```json
{
  "channel": 0,
  "current_angle": 90.0,
  "pulse_width_us": 1500,
  "pca9685_ticks": 307
}
```

#### `ErrorReport`
Sent by ESP32 when error occurs:

```json
{
  "channel": 0,
  "error": "PCA9685 I2C communication failed"
}
```

### Class: `ServoWebSocketManager`

**Attributes**:
- `state_manager`: ServoStateManager – Reference to state layer
- `active_connections`: Dict[str, ServoWebSocketConnection] – Active devices
- `devices_lock`: asyncio.Lock – Thread-safe device tracking

**Key Methods**:

```python
async def register_device(websocket, registration) -> bool:
    """Register ESP32 device"""

async def unregister_device(device_id: str):
    """Unregister on disconnect"""

async def send_command(device_id: str, channel: int, angle: float) -> bool:
    """Send servo command to ESP32"""

async def handle_feedback(device_id: str, feedback: ServoFeedback) -> bool:
    """Process state feedback from ESP32"""

async def handle_error(device_id: str, error: ErrorReport) -> bool:
    """Process error report from ESP32"""

async def send_registration_ack(device_id: str, config_json: Dict) -> bool:
    """Send ACK with servo configurations"""

async def get_connection_status() -> Dict:
    """Get status of all connections"""
```

---

## Component 3: FastAPI Routes

**File**: `app/devices/routes.py`

REST endpoints + WebSocket endpoint for servo control.

### REST Endpoints

#### `POST /servo/set`
Command a servo to target angle.

**Query Parameters**:
- `channel` (int): 0–9
- `angle` (float): 0–180 (will be clamped)

**Response** (ServoState):
```json
{
  "channel": 0,
  "label": "Base Rotation",
  "current_angle": 90.0,
  "target_angle": 120.0,
  "pulse_width_us": 1610,
  "pca9685_ticks": 330,
  "is_moving": true,
  "error": null
}
```

**Errors**:
- `400`: Invalid channel or angle
- `503`: ESP32 not connected

---

#### `GET /servo/state/{channel}`
Get current state of one servo.

**Path Parameters**:
- `channel` (int): 0–9

**Response** (ServoState):
```json
{
  "channel": 0,
  "label": "Base Rotation",
  "current_angle": 90.0,
  "target_angle": 90.0,
  "pulse_width_us": 1500,
  "pca9685_ticks": 307,
  "is_moving": false,
  "error": null
}
```

---

#### `GET /servo/all`
Get state of all 10 servos.

**Response**:
```json
{
  "0": {...ServoState...},
  "1": {...ServoState...},
  ...
  "9": {...ServoState...}
}
```

---

#### `POST /servo/reset`
Reset all servos to home position (90°).

**Response**:
```json
{
  "status": "reset_sent",
  "servos_reset": 10,
  "total_servos": 10
}
```

---

#### `GET /servo/health`
Health check: Is ESP32 connected?

**Response**:
```json
{
  "status": "healthy",
  "esp32_connected": true,
  "devices": {
    "servoscontroller": {
      "connected": true,
      "device_type": "esp32s3",
      "connected_at": "2026-01-26T12:34:56.123456",
      "last_heartbeat": "2026-01-26T12:34:58.456789"
    }
  }
}
```

---

### WebSocket Endpoint: `/ws/servo`

**Full Duplex Communication**

ESP32 connects: `ws://localhost:8000/servo/ws/servo`

#### Message Flow

**1. ESP32 Registers**
```
ESP32 → Backend
{
  "type": "register",
  "data": {
    "device_id": "servoscontroller",
    "device_type": "esp32s3",
    "firmware_version": "1.0.0"
  }
}

Backend → ESP32 (Registration ACK)
{
  "type": "ack",
  "data": {
    "0": {
      "ch": 0,
      "label": "Base Rotation",
      "minA": 0.0,
      "maxA": 180.0,
      "minPulse": 1000,
      "maxPulse": 2000,
      "home": 90.0
    },
    "1": {...},
    ...
    "9": {...}
  }
}
```

**2. Backend Sends Command**
```
Backend → ESP32
{
  "type": "command",
  "data": {
    "channel": 0,
    "angle": 120.0
  }
}
```

**3. ESP32 Sends Feedback**
```
ESP32 → Backend
{
  "type": "feedback",
  "data": {
    "channel": 0,
    "current_angle": 120.0,
    "pulse_width_us": 1610,
    "pca9685_ticks": 330
  }
}
```

Backend updates `ServoStateManager` with new angle.

**4. ESP32 Reports Error**
```
ESP32 → Backend
{
  "type": "error",
  "data": {
    "channel": 0,
    "error": "PCA9685 not responding on I2C"
  }
}
```

Backend sets error flag in `ServoStateManager`.

**5. Heartbeat (Optional)**
```
Backend → ESP32
{"type": "ping"}

ESP32 → Backend
{"type": "pong"}
```

---

## Integration with main.py

Servo routes are registered in `main.py`:

```python
# Import servo routes
from app.devices.routes import router as servo_router
app.include_router(servo_router)
```

All servo endpoints are prefixed with `/servo/`:
- `POST /servo/set`
- `GET /servo/state/0`
- `GET /servo/all`
- `POST /servo/reset`
- `GET /servo/health`
- `WebSocket /servo/ws/servo`

---

## Dependency Injection

**File**: `app/dependencies.py`

Added two new dependency functions:

```python
async def get_servo_state_manager() -> ServoStateManager:
    """Get Servo State Manager singleton"""
    global _servo_state_manager
    if _servo_state_manager is None:
        _servo_state_manager = create_state_manager()
        await _servo_state_manager.initialize()
    return _servo_state_manager

async def get_websocket_manager() -> ServoWebSocketManager:
    """Get Servo WebSocket Manager singleton"""
    global _servo_websocket_manager
    if _servo_websocket_manager is None:
        state_mgr = await get_servo_state_manager()
        _servo_websocket_manager = create_websocket_manager(state_mgr)
    return _servo_websocket_manager
```

Used in route handlers via FastAPI's dependency injection system.

---

## Error Handling

### Command Validation
1. Channel must be 0–9
2. Angle must be reasonable (±180°)
3. ESP32 must be connected before sending commands

### State Tracking
- Each servo tracks: current angle, target angle, pulse width, ticks
- Moving status automatically set based on distance to target
- Error flag prevents further commands until cleared

### WebSocket Disconnection
- If ESP32 disconnects, `ServoWebSocketManager.unregister_device()` removes it
- REST endpoints return `503 Service Unavailable`
- `/servo/health` shows disconnected status

---

## Example Workflow: Manual Servo Control

```python
# 1. User opens web dashboard
#    Browser connects to http://localhost:8000
#    Dashboard runs JavaScript to interact with backend

# 2. User moves slider for servo 0 to 120 degrees
#    JavaScript sends: POST /servo/set?channel=0&angle=120

# 3. FastAPI handler:
#    a) Validates channel (0–9) ✓
#    b) Validates angle (0–180, input 120) ✓
#    c) Calls state_mgr.set_target_angle(0, 120)
#    d) state_mgr clamps, calculates PWM:
#       - 120° in [0, 180] → 1610 µs → 330 ticks
#    e) Calls ws_mgr.send_command("servoscontroller", 0, 120.0)
#    f) WebSocket sends to ESP32:
#       {"type": "command", "data": {"channel": 0, "angle": 120.0}}

# 4. ESP32 firmware:
#    a) Receives command
#    b) Converts 120° → 330 ticks
#    c) Writes PCA9685 PWM register for channel 0
#    d) Servo starts moving

# 5. ESP32 polls servo position periodically
#    a) Reads feedback from servo (if available)
#    b) Sends to backend:
#       {"type": "feedback", "data": {"channel": 0, "current_angle": 119.5, ...}}

# 6. FastAPI handler:
#    a) Receives feedback message
#    b) Calls state_mgr.update_current_angle(0, 119.5)
#    c) state_mgr updates local state (current_angle = 119.5)
#    d) Detects close to target (120.0 - 119.5 = 0.5° < 1.0°)
#    e) Sets is_moving = False

# 7. User checks slider position (optional):
#    a) Browser sends: GET /servo/state/0
#    b) Returns current ServoState with current_angle = 119.5
#    c) Dashboard updates slider to show 119.5°
```

---

## Testing

### Manual Test 1: Health Check
```bash
curl http://localhost:8000/servo/health
```

Expected response (ESP32 not yet connected):
```json
{
  "status": "disconnected",
  "esp32_connected": false,
  "devices": {}
}
```

### Manual Test 2: After ESP32 Connects

```bash
curl http://localhost:8000/servo/health
```

Expected response:
```json
{
  "status": "healthy",
  "esp32_connected": true,
  "devices": {
    "servoscontroller": {
      "connected": true,
      "device_type": "esp32s3",
      "connected_at": "2026-01-26T12:35:00.000000",
      "last_heartbeat": "2026-01-26T12:35:05.123456"
    }
  }
}
```

### Manual Test 3: Set Servo
```bash
curl -X POST "http://localhost:8000/servo/set?channel=0&angle=90"
```

Expected response:
```json
{
  "channel": 0,
  "label": "Base Rotation",
  "current_angle": 90.0,
  "target_angle": 90.0,
  "pulse_width_us": 1500,
  "pca9685_ticks": 307,
  "is_moving": false,
  "error": null
}
```

---

## Files Created/Modified

| File | Type | Lines | Purpose |
|------|------|-------|---------|
| [`app/devices/servo_state.py`](../../amhrpd-backend/app/devices/servo_state.py) | New | 250 | State manager |
| [`app/websocket/servo_manager.py`](../../amhrpd-backend/app/websocket/servo_manager.py) | New | 400 | WebSocket manager |
| [`app/devices/routes.py`](../../amhrpd-backend/app/devices/routes.py) | New | 350 | FastAPI endpoints |
| [`app/dependencies.py`](../../amhrpd-backend/app/dependencies.py) | Modified | +25 | Added servo DI |
| [`app/main.py`](../../amhrpd-backend/app/main.py) | Modified | +5 | Registered servo routes |

---

## Safety & Robustness

✅ **Thread-Safe**: All state access protected by `asyncio.Lock`  
✅ **Input Validation**: All angles clamped to [min_angle, max_angle]  
✅ **Error Recovery**: ESP32 disconnection handled gracefully  
✅ **Type Safety**: Pydantic models enforce JSON schema  
✅ **Logging**: All operations logged for debugging  
✅ **No Direct PWM**: Backend sends logical angles only  

---

## Next Steps

**STEP 3**: Implement ESP32-S3 + PCA9685 firmware to handle WebSocket and drive servos  
**STEP 4**: Create web dashboard with 10 sliders  
**STEP 5**: Define message contracts (JSON schema)

---

## Status Summary

| Component | Status | Lines | Language |
|-----------|--------|-------|----------|
| ServoStateManager | ✅ Complete | 250 | Python 3.10+ |
| ServoWebSocketManager | ✅ Complete | 400 | Python 3.10+ |
| FastAPI Routes | ✅ Complete | 350 | Python 3.10+ |
| Dependency Injection | ✅ Complete | +25 | Python 3.10+ |
| Syntax Check | ✅ Pass | — | — |
| Type Hints | ✅ Complete | — | — |

**STEP 2 is complete. Ready for STEP 3 (firmware).**
