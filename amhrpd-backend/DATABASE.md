# AMHR-PD Backend - Database Integration

## Database Configuration

### Setup
1. Database auto-creates on first run
2. SQLite file: `amhrpd.db` (in project root)
3. Foreign keys enabled automatically

### Environment Variable
```bash
DATABASE_URL=sqlite:///./amhrpd.db
```

## Database Schema

### Tables

#### `devices`
Stores device connection status and metadata
```
device_id (PK)       → Device identifier
device_type          → ESP32, ESP32-S3, or ESP32-CAM
is_online            → Connection status
last_heartbeat       → Last activity timestamp
connected_at         → Initial connection time
disconnected_at      → Disconnection time (if offline)
metadata_json        → Additional device metadata
```

#### `device_state_snapshots`
Hardware state snapshots (auto-persisted on each status message)
```
id (PK)              → Auto-increment ID
device_id (FK)       → Reference to devices table
device_type          → ESP32, ESP32-S3, or ESP32-CAM
state_data           → JSON payload from device
timestamp            → Snapshot timestamp
```

#### `command_logs`
Command execution history
```
command_id (PK)      → UUID from command router
device_type          → Target device type
command_name         → Command name
payload              → JSON command payload
status               → pending → created → sent → ack_success/ack_error
created_at           → Command creation time
executed_at          → Time command was sent
completed_at         → Time ACK received
response_data        → Device response (if any)
target_device_count  → Total devices targeted
success_count        → Devices that acknowledged
```

#### `device_connection_logs`
Connection event history
```
id (PK)              → Auto-increment ID
device_id (FK)       → Reference to devices table
device_type          → ESP32, ESP32-S3, or ESP32-CAM
event                → "connected", "disconnected", "timeout"
timestamp            → Event timestamp
details              → JSON event details
```

## Historical Data Endpoints

### Get Device State History
```
GET /state-history/{device_id}?limit=100
```
Returns last N state snapshots for a device.

### Get Command Logs
```
GET /command-logs?status=ack_success&limit=100
GET /command-logs?device_type=ESP32&limit=100
GET /command-logs?limit=100
```
Filter by status or device type.

### Get Connection History
```
GET /device-connection-history/{device_id}?limit=100
```
Returns connection events (connected, disconnected, timeout).

## Data Persistence Flow

### On Device Connection (WebSocket `/ws/{device_id}`)
1. Device sends first message with `device_type`
2. Device registered in memory (registry)
3. **Persisted to `devices` table**
4. **Connection event logged in `device_connection_logs`**

### On Device State Update (message_type="status")
1. State updated in memory (state_manager)
2. **Persisted to `device_state_snapshots` table**

### On Command Routing (POST `/command`)
1. Command created with UUID
2. **Persisted to `command_logs` table** with status="created"
3. Command sent to devices
4. **Status updated to "sent"**

### On Command ACK (message_type="command_ack")
1. Status updated in memory
2. **Status persisted in `command_logs`** with status="ack_success" or "ack_error"

### On Device Disconnect
1. Device marked offline in memory
2. **Device status updated in `devices` table**
3. **Disconnection event logged**

## API Behavior (No Changes)

All existing endpoints maintain same behavior:
- `POST /command` → Same response
- `GET /devices` → Same response
- `GET /devices/{device_id}` → Same response
- `WebSocket /ws/{device_id}` → Same protocol

Database persistence is transparent to the API.

## Running with Database

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn app.main:app --reload

# Database auto-initializes on startup
```

Database will be created at `amhrpd.db` on first run.

## Example Records

### Device Record
```json
{
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "is_online": true,
  "last_heartbeat": "2026-01-24T10:30:45.123456",
  "connected_at": "2026-01-24T10:15:00.000000",
  "disconnected_at": null,
  "metadata_json": {}
}
```

### State Snapshot
```json
{
  "id": 1,
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "state_data": {
    "temperature": 25.3,
    "humidity": 45.2,
    "battery": 87
  },
  "timestamp": "2026-01-24T10:30:45.123456"
}
```

### Command Log
```json
{
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_type": "ESP32",
  "command_name": "reboot",
  "payload": {
    "delay_ms": 1000
  },
  "status": "ack_success",
  "created_at": "2026-01-24T10:25:00.000000",
  "executed_at": "2026-01-24T10:25:01.000000",
  "completed_at": "2026-01-24T10:25:03.000000",
  "target_device_count": 2,
  "success_count": 2
}
```

### Connection Log
```json
{
  "id": 1,
  "device_id": "esp32_001",
  "device_type": "ESP32",
  "event": "connected",
  "timestamp": "2026-01-24T10:15:00.000000",
  "details": {}
}
```
