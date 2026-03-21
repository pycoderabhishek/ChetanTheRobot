"""
Multilingual TTS Module for Chetan Robot
Provides bilingual text-to-speech: Hindi (gTTS) and English (pyttsx3).

Primary for Hindi: gTTS (Google Text-to-Speech) → returns PCM bytes
Fallback / English: pyttsx3 (current system)
"""

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def tts_to_pcm_multilingual(text: str, language: str = "en", samplerate: int = 16000) -> bytes:
    """
    Convert text to PCM audio, language-aware.

    Args:
        text: Text to synthesize.
        language: "hi" for Hindi TTS (gTTS), "en" for English TTS (pyttsx3).
        samplerate: Target sample rate (default 16000 Hz).

    Returns:
        PCM audio bytes (16-bit signed little-endian at the given samplerate).
    """
    if not text or not text.strip():
        return b""

    if language == "hi":
        pcm = _gtts_to_pcm(text, samplerate)
        if pcm:
            return pcm
        logger.warning("gTTS Hindi TTS failed, falling back to English pyttsx3")

    # English / fallback: use existing pyttsx3-based TTS
    from app.audio.tts import tts_to_pcm
    return tts_to_pcm(text, samplerate)


def _gtts_to_pcm(text: str, samplerate: int = 16000) -> Optional[bytes]:
    """
    Use gTTS to synthesise Hindi text and return raw PCM bytes.

    gTTS produces MP3; we decode to PCM using pydub (if available) or
    fall back to returning the raw MP3 bytes wrapped in a WAV container
    via the standard library (wave + audioop).

    Returns None on any error so the caller can fall back gracefully.
    """
    try:
        from gtts import gTTS
    except ImportError:
        logger.debug("gTTS not installed; skipping Hindi TTS")
        return None

    try:
        mp3_buffer = io.BytesIO()
        tts_obj = gTTS(text=text, lang="hi", slow=False)
        tts_obj.write_to_fp(mp3_buffer)
        mp3_buffer.seek(0)
        mp3_bytes = mp3_buffer.read()
    except Exception as exc:
        logger.warning(f"gTTS synthesis failed: {exc}")
        return None

    # Try to decode MP3 → PCM using pydub + ffmpeg
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        audio = audio.set_frame_rate(samplerate).set_channels(1).set_sample_width(2)
        return audio.raw_data
    except Exception:
        pass

    # Try soundfile + numpy as an alternative decoder
    try:
        import soundfile as sf
        import numpy as np
        import scipy.signal as sg

        data, orig_rate = sf.read(io.BytesIO(mp3_bytes), dtype="int16", always_2d=False)
        if data.ndim > 1:
            data = data[:, 0]
        if orig_rate != samplerate:
            num_samples = int(len(data) * samplerate / orig_rate)
            data = sg.resample(data, num_samples).astype("int16")
        return data.tobytes()
    except Exception:
        pass

    logger.warning("Could not decode MP3 from gTTS; falling back to pyttsx3")
    return None
