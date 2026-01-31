# AMHR-PD Audio-Only Robotic Command System - Working Documentation

This document explains the architecture and operational flow of the audio-only robotic system developed for the AMHR-PD project.

## 1. System Architecture

The system consists of two main layers:
1.  **Hardware Layer (ESP32-S3)**: Handles audio capture (INMP441), wake-word detection, audio playback (MAX98357), and movement/servo control.
2.  **Backend Layer (FastAPI)**: Handles Speech-to-Text (STT), intent recognition, command routing, and Text-to-Speech (TTS) response generation.

### Audio Flow Diagram
```
[ESP32-S3] -> (Wake Word "HI CHETAN") -> [8s PCM Record] -> [HTTP POST /api/audio/upload]
                                                                        |
                                                                        v
[ESP32-S3] <- [WebSocket: audio_response] <- [STT] -> [Prefix Check] -> [Command Match] -> [TTS]
```

---

## 2. Hardware Components (Audio-Only)

The system has been updated to remove all camera-related features, focusing exclusively on audio interactions.

### Audio Input (Microphone)
- **Component**: INMP441 (I2S MEMS Microphone)
- **Configuration**: 16kHz sample rate, 16-bit PCM, Mono.
- **Pins**:
    - BCLK: GPIO 4
    - LRC: GPIO 5
    - DIN: GPIO 7

### Audio Output (Speaker)
- **Component**: MAX98357 (I2S Class-D Amplifier)
- **Configuration**: 16kHz sample rate, 16-bit PCM, Mono.
- **Pins**:
    - BCLK: GPIO 4
    - LRC: GPIO 5
    - DOUT: GPIO 6

---

## 3. Backend Logic (FastAPI)

The backend processes the uploaded PCM audio through a series of stages:

### A. Speech-to-Text (STT)
The system uses a custom STT wrapper (`app/audio/stt.py`) that processes raw 16kHz PCM data into text.

### B. Prefix Gating
To prevent accidental triggers, the system checks for a valid prefix in the transcribed text:
- **Allowed Prefixes**: "ESP", "NATIONAL PG".
- **Implementation**: `app/audio/prefix_gate.py`.

### C. Command Matching & Intent
The system uses fuzzy string matching to identify robot commands from the transcribed text.
- **Keywords**:
    - Movement: `forward`, `backward`, `left`, `right`, `stop`.
    - Servo Poses: `resetposition`, `handsup`, `headleft`, `headright`, `headup`, `headdown`.
- **Implementation**: `app/audio/commandcheck.py`.

### D. Command Routing
Once an intent is matched, it is routed to the corresponding device type:
- **esp32**: Wheel/Motor controller.
- **esp32s3**: Servo controller.
- **Implementation**: `app/audio/routes.py`.

### E. Text-to-Speech (TTS)
A response is generated for the user (e.g., "Executing handsup") and converted to 16kHz PCM audio.
- **Implementation**: `app/audio/tts.py`.

---

## 4. Operational Flow

1.  **Idle State**: ESP32-S3 monitors I2S input for an energy spike (wake-word detection).
2.  **Triggered**: When "HI CHETAN" is detected (via energy threshold), the device records 8 seconds of PCM audio.
3.  **Upload**: The audio is sent via HTTP POST to the backend.
4.  **Processing**: The backend transcribes the audio, validates the prefix, and matches the command.
5.  **Execution**:
    - The command is dispatched to the target device (Wheel or Servo) via WebSocket.
    - A TTS response is generated.
6.  **Feedback**: The backend sends the TTS audio back to the ESP32-S3 via the established WebSocket connection (`message_type: "audio_response"`).
7.  **Playback**: The ESP32-S3 decodes the base64 audio and plays it through the MAX98357 amplifier.

---

## 5. Command Mapping

| Voice Command | Action | Target Device Type |
|---------------|--------|--------------------|
| "Forward" | Move Robot Forward | `esp32` |
| "Backward" | Move Robot Backward | `esp32` |
| "Stop" | Stop All Movement | `esp32` |
| "Reset Position" | Reset Servos to Home | `esp32s3` |
| "Hands Up" | Trigger Hands Up Pose | `esp32s3` |
| "Head Left" | Turn Head Left | `esp32s3` |

---

## 6. How to Run

1.  **Backend**:
    - Start the FastAPI server: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
    - Ensure the database is initialized.
2.  **Firmware**:
    - Flash `ESPCAM.ino` to the ESP32-S3 (with INMP441 and MAX98357 connected).
    - Update `WIFI_SSID` and `WIFI_PASSWORD` in the code.
    - Verify the `BACKEND_HOST` matches your server's IP.
