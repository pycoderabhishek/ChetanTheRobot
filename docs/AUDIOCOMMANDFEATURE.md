# AMHR-PD Audio Command Feature — Design Document
 
## Purpose
 
- Define an audio-only, voice-driven control feature for AMHR-PD.
- Keep ESP32-S3 as an I/O device (mic in, amp out); move all intelligence to Backend.
- Provide clear pipelines, routes, data formats, and contracts enabling reliable ESP ↔ Backend communication without altering current working code.
 
---
 
## Architecture Overview
 
- **ESP32-S3 (Audio I/O only)**
  - INMP441 I2S Microphone (input)
  - MAX98357 I2S Amplifier (output)
  - Wake word detection (“HI CHETAN”), fixed 8-second recording, audio transfer, audio playback
- **Backend (FastAPI, Python)**
  - Audio ingest (PCM/WAV) → WAV normalization
  - Speech-to-Text (STT) → English normalization
  - Prefix Gate (“ESP” or “NATIONAL PG”)
  - CommandCheck (grammar/polite removal, keyword extraction, fuzzy matching, confidence scoring)
  - TTS response generation, device command dispatch, execution monitoring
- **Transport**
  - HTTP POST or WebSocket (binary frames)
  - Audio format: 16,000 Hz, 16-bit PCM, mono (WAV-compatible)
 
---
 
## Hardware Configuration (ESP32-S3)
 
- **INMP441 Mic (I2S RX)**
  - Pins: WS/LRCLK, SCK/BCLK, SD (exact mapping defined in firmware config)
- **MAX98357 Amp (I2S TX)**
  - Pins: BCLK, LRC, DIN (exact mapping defined in firmware config)
- **Audio Format**
  - Sample rate: 16 kHz
  - Bit depth: 16-bit PCM
  - Channels: Mono
- **Wake Word**
  - Phrase: “HI CHETAN”
  - Passive listening mode; sensitivity configured
- **Recording Window**
  - Fixed duration: 8 seconds
 
---
 
## ESP Feature Design
 
### Wake Word Logic
- Continuously listen in passive mode.
- Detect “HI CHETAN”.
- Switch to active mode.
- Record exactly 8 seconds of audio; stop automatically.
- No speech or command processing on ESP.
 
### Audio Transfer
- **Option A: HTTP**
  - Route: `/api/audio/upload`
  - Content-Type: `audio/wav` or `application/octet-stream` (PCM)
  - Query: `device_id=<id>`
  - Body: raw PCM bytes or WAV
- **Option B: WebSocket**
  - Route: `/ws/audio/{device_id}`
  - Frame 1: JSON metadata `{ "samplerate":16000, "channels":1, "format":"pcm_s16_le" }`
  - Frame 2: Binary audio payload (PCM or WAV)
 
### Audio Playback
- Receive processed audio (PCM/WAV) from Backend.
- Play via MAX98357 using I2S TX.
- Used for confirmations and system responses.
 
---
 
## Backend Pipelines
 
### Audio Ingestion
- Accept PCM/WAV from ESP; normalize to WAV (16 kHz, mono, PCM16).
- Store reference as `USER_INPUT_AUDIO`.
 
### Speech-to-Text (STT) + English Normalization
- Run STT engine (e.g., Whisper).
- Normalize output text to English.
- Store as `USER_INPUT_TEXT`.
 
### Prefix Validation Gate
- Extract first 2–3 semantic tokens from `USER_INPUT_TEXT`.
- Proceed only if one exists: `ESP`, `NATIONAL PG`.
- If missing, reject and generate clarification TTS.
 
### CommandCheck
- Remove grammar words (is, am, are, the, a, an).
- Remove polite fillers (please, kindly, can you).
- Extract action keywords.
- Fuzzy match against known robot commands; calculate confidence score.
- Select highest-confidence executable command (threshold-controlled).
 
### Respond + Act
- Generate verbal confirmation text (e.g., “Moving forward”).
- TTS → PCM/WAV → send to ESP for playback.
- Dispatch movement/API command to Wheel ESP / navigation system via existing backend routes.
- Monitor execution; update state as needed.
 
---
 
## Data Flow (Conceptual)
 
```
Wake → Record(8s) → Transfer(PCM/WAV) → Ingest → WAV normalize
→ STT → English normalize → Prefix Gate(ESP|NATIONAL PG)
→ CommandCheck(fuzzy, confidence) → Confirm(TTS)
→ Send TTS to ESP + Send MOVE cmd to Wheel ESP → Monitor
```
 
---
 
## API Contracts (ESP ↔ Backend)
 
### Upload Audio (HTTP)
- Method: `POST /api/audio/upload?device_id=<id>`
- Headers: `Content-Type: audio/wav` or `application/octet-stream`
- Body: WAV or raw PCM bytes
- Response:
  - `{"status":"ok","audio_id":"<uuid>","samplerate":16000,"duration_ms":8000}`
 
### Upload Audio (WebSocket)
- Path: `/ws/audio/{device_id}`
- Client frames:
  - Frame 1: JSON metadata `{ "samplerate":16000, "channels":1, "format":"pcm_s16_le" }`
  - Frame 2: Binary audio payload (PCM/WAV)
- Server response:
  - `{"status":"ok","audio_id":"<uuid>"}` or error JSON
 
### Audio Response (Backend → ESP)
- Path: existing device websocket `/ws/{device_id}`
- Message payload:
  - `{"message_type":"audio_response","samplerate":16000,"format":"pcm_s16_le","bytes":"<binary>"}` (binary frame for audio)
 
### Command Dispatch (Backend → Devices)
- Reuse existing backend command router and WebSocket manager.
- `{"message_type":"command","command_name":"MOVE_FORWARD","payload":{}}`
 
---
 
## Command Vocabulary (Examples)
 
- `MOVE_FORWARD`, `MOVE_BACKWARD`, `TURN_LEFT`, `TURN_RIGHT`, `STOP`
- Confidence threshold (e.g., `0.70`); tie-break via intent priority.
 
---
 
## Error Handling & Validation
 
- Wake-word false positive mitigation via sensitivity and debounce.
- Audio payload integrity: samplerate/format validation; length checks; optional checksum.
- Prefix rejection: generate clarification TTS and send to ESP.
- Command confidence below threshold: ask for clarification or default to `STOP`.
 
---
 
## Testing Strategy
 
- **ESP**
  - Wake-word detection timing and reliability.
  - Exact 8-second buffer integrity (sample count, no drift).
  - I2S playback confirmation tone and round-trip latency checks.
- **Backend**
  - Ingest WAV fixture; verify STT → English normalize → Prefix Gate → CommandCheck → TTS.
  - WebSocket push of audio response; device routing behavior.
- **End-to-End**
  - Full pipeline with sample recordings; verify voice confirmation + action trigger.
 
---
 
## Modularity & Scalability
 
- Swap STT/TTS engines without changing ESP code or transport.
- Extend command vocabulary via backend configuration and CommandCheck rules.
- Strict separation of responsibilities:
  - ESP = Wake word, record, transfer, playback.
  - Backend = STT/NLP/decision-making/action routing.
 
---
 
## Constraints (Non-Negotiable)
 
- Audio-only: **no camera libraries**, drivers, or image/video logic.
- ESP does **not** perform STT/NLP/command filtering.
- Wake word “HI CHETAN”; fixed 8-second recording window.
- Prefix Gate must validate `ESP` or `NATIONAL PG` before any action.
 
---
 
## Reference Logic (Backend)
 
- STT: docs/AUDIOTESTCOD/transcribe stand aolone (1).py
- TTS: docs/AUDIOTESTCOD/text to speech standalone (1).py
- Command filtering: docs/AUDIOTESTCOD/test_audio_data (1).py
- Data model: docs/RESPONCEDATAFILES/data.json
 
