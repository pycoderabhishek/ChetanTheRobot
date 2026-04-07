import base64
import logging
from datetime import datetime
from fastapi import APIRouter, Request
from app.audio.stt import transcribe_pcm
from app.audio.tts import tts_to_pcm
from app.audio.prefix_gate import has_valid_prefix
from app.audio.commandcheck import match_command
from app.audio.knowledge_base import get_answer
from app.audio.chatbot_profile import get_chatbot_profile
from app.audio.language_detector import detect_language
from app.audio.multilingual_knowledge_base import get_answer_multilingual
from app.audio.hindi_translator import translate_to_english, translate_to_hindi
from app.audio.multilingual_tts import tts_to_pcm_multilingual
from app.dependencies import get_connection_manager

router = APIRouter(prefix="/api/audio", tags=["Audio"])
logger = logging.getLogger(__name__)
MAX_AUDIO_LOGS = 200
AUDIO_LOGS: list[dict] = []
TRANSCRIPT_LOGS: list[dict] = []
DEVICE_TYPE_BY_COMMAND = {
    "MOVE_FORWARD": "esp32",
    "MOVE_BACKWARD": "esp32",
    "TURN_LEFT": "esp32",
    "TURN_RIGHT": "esp32",
    "STOP": "esp32",
    "resetposition": "esp32s3",
    "handsup": "esp32s3",
    "headleft": "esp32s3",
    "headright": "esp32s3",
    "headup": "esp32s3",
    "headdown": "esp32s3",
}

CHUNK_SIZE = 2048

async def send_audio_response(device_id: str, pcm: bytes, samplerate: int = 16000) -> bool:
    if not pcm:
        return False
    cm = get_connection_manager()
    
    # Always use chunking for stability (Fix #5)
    total = (len(pcm) + CHUNK_SIZE - 1) // CHUNK_SIZE
    for idx in range(total):
        start = idx * CHUNK_SIZE
        end = min(len(pcm), start + CHUNK_SIZE)
        b64 = base64.b64encode(pcm[start:end]).decode("ascii")
        sent = await cm.send_to_device(device_id, {
            "message_type": "audio_chunk",
            "samplerate": samplerate,
            "format": "pcm_s16_le",
            "audio_base64": b64,
            "index": idx,
            "total": total,
            "is_last": idx == total - 1
        })
        if not sent:
            logger.error(f"Failed to send audio chunk {idx+1}/{total} to {device_id}")
            return False
    return True

@router.post("/upload")
async def upload_audio(
    request: Request,
    device_id: str,
    movement_device_type: str | None = None,
    manual: bool = False,
    level: int | None = None,
    threshold: int | None = None
):
    body = await request.body()
    text = transcribe_pcm(body, 16000)
    prefix_ok = has_valid_prefix(text)
    if manual:
        prefix_ok = True
    command_name, confidence = match_command(text)
    response_text = "I did not catch a valid command. Please repeat."
    response_lang = "en"
    if not prefix_ok and not manual:
        response_text = "I did not hear the wake word. Please repeat your command."
    elif prefix_ok and command_name:
        response_text = f"Executing {command_name}. Anything else?"
    elif prefix_ok:
        # 1. Detect language of the incoming query
        lang_info = detect_language(text)
        response_lang = lang_info.get("primary_lang", "en")

        # 2. Translate to English for searching if query is Hindi or code-mixed
        search_query = text
        if lang_info["language"] in ("hi", "code_mixed"):
            search_query = translate_to_english(text, lang_info["language"])

        # 3. Search knowledge bases with the (possibly translated) English query
        profile_answer = get_chatbot_profile(search_query)
        needs_translation = True
        if profile_answer:
            response_text = profile_answer
        else:
            # Pass original text so get_answer_multilingual can match
            # Hindi/Hinglish variants in the multilingual dataset directly.
            ml_answer, ml_lang = get_answer_multilingual(text)
            if ml_answer:
                response_text = ml_answer
                response_lang = ml_lang or response_lang
                # Answer is already in the user's preferred language; skip step 4.
                needs_translation = False
            elif (kb_answer := get_answer(search_query)):
                response_text = kb_answer
            else:
                response_text = "I heard you. Please repeat your command."

        # 4. Translate response back to Hindi if the user queried in Hindi or Hinglish
        if needs_translation and lang_info["language"] in ("hi", "code_mixed"):
            response_text = translate_to_hindi(response_text)
            response_lang = "hi"  # ensure TTS uses the Hindi voice
    tts_error = None
    pcm = b""
    try:
        pcm = tts_to_pcm_multilingual(response_text, language=response_lang, samplerate=16000)
    except Exception as exc:
        tts_error = str(exc)
        logger.exception("TTS failed for upload response")
    if pcm:
        await send_audio_response(device_id, pcm, 16000)
    result = {
        "text": text,
        "prefix_ok": prefix_ok,
        "command_name": command_name,
        "confidence": confidence
    }
    if tts_error:
        result["tts_error"] = tts_error
    AUDIO_LOGS.append({
        "timestamp": datetime.utcnow().isoformat(),
        "device_id": device_id,
        "text": text,
        "prefix_ok": prefix_ok,
        "command_name": command_name,
        "confidence": confidence,
        "manual": manual,
        "level": level,
        "threshold": threshold,
        "tts_error": tts_error,
    })
    if len(AUDIO_LOGS) > MAX_AUDIO_LOGS:
        del AUDIO_LOGS[:len(AUDIO_LOGS) - MAX_AUDIO_LOGS]
    if text:
        TRANSCRIPT_LOGS.append({
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": device_id,
            "text": text,
            "command_name": command_name,
            "confidence": confidence,
            "manual": manual
        })
        if len(TRANSCRIPT_LOGS) > MAX_AUDIO_LOGS:
            del TRANSCRIPT_LOGS[:len(TRANSCRIPT_LOGS) - MAX_AUDIO_LOGS]
    target_type = movement_device_type or (DEVICE_TYPE_BY_COMMAND.get(command_name) if command_name else None)
    if prefix_ok and command_name and target_type and hasattr(request.app.state, "command_router"):
        command = await request.app.state.command_router.route_command(target_type, command_name, {})
        result["dispatched_command_id"] = command.command_id
        result["dispatch_status"] = command.status
    return result

@router.get("/logs")
async def get_audio_logs(limit: int = 50):
    if limit < 1:
        limit = 1
    if limit > MAX_AUDIO_LOGS:
        limit = MAX_AUDIO_LOGS
    return {"logs": AUDIO_LOGS[-limit:]}

@router.get("/transcripts")
async def get_transcripts(limit: int = 50):
    if limit < 1:
        limit = 1
    if limit > MAX_AUDIO_LOGS:
        limit = MAX_AUDIO_LOGS
    return {"logs": TRANSCRIPT_LOGS[-limit:]}

@router.get("/notify")
async def notify(device_id: str, text: str, samplerate: int = 16000):
    # Log the notification (User requested status update log for "Hi Chetan")
    command_name = "FEEDBACK"
    if "listening" in text.lower():
        command_name = "WAKE_WORD"  # Status: Active

    AUDIO_LOGS.append({
        "timestamp": datetime.utcnow().isoformat(),
        "device_id": device_id,
        "text": text,
        "prefix_ok": True,
        "command_name": command_name,
        "confidence": 1.0,
        "manual": False,
        "level": 0,
        "threshold": 0
    })
    if len(AUDIO_LOGS) > MAX_AUDIO_LOGS:
        del AUDIO_LOGS[:len(AUDIO_LOGS) - MAX_AUDIO_LOGS]

    tts_error = None
    pcm = b""
    try:
        notify_lang = detect_language(text).get("primary_lang", "en")
        pcm = tts_to_pcm_multilingual(text, language=notify_lang, samplerate=samplerate)
    except Exception as exc:
        tts_error = str(exc)
        logger.exception("TTS failed for notify")
    sent = False
    if pcm:
        sent = await send_audio_response(device_id, pcm, samplerate)
    return {"sent": sent, "error": tts_error}
