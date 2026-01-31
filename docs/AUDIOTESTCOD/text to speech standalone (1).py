import os
import tempfile
import numpy as np
import soundfile as sf
import pyttsx3
import sounddevice as sd
from scipy.signal import resample

TARGET_SAMPLE_RATE = 16000


def generate_pcm_from_text(text: str, target_sr: int = 16000) -> bytes:
    """
    Offline TTS → RAW PCM (int16, mono, 16kHz)
    """

    engine = pyttsx3.init()
    engine.setProperty("rate", 150)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        wav_path = f.name

    engine.save_to_file(text, wav_path)
    engine.runAndWait()

    audio, sr = sf.read(wav_path, dtype="float32")
    os.remove(wav_path)

    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)

    if sr != target_sr:
        new_len = int(len(audio) * target_sr / sr)
        audio = resample(audio, new_len)

    audio = np.clip(audio, -1.0, 1.0)
    pcm_int16 = (audio * 32767).astype(np.int16)

    return pcm_int16.tobytes()


def play_pcm(pcm_bytes: bytes, samplerate: int = 16000):
    """
    Play RAW int16 PCM directly
    (Exactly what ESP32 would hear)
    """

    pcm_np = np.frombuffer(pcm_bytes, dtype=np.int16)

    sd.play(pcm_np, samplerate=samplerate, blocking=True)
    sd.stop()


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    text = "Daijobu shou ka? Anata no koe wa totemo kirei desu."

    print("Generating PCM...")
    pcm = generate_pcm_from_text(text)

    print(f"PCM size: {len(pcm)} bytes")

    print("Playing PCM...")
    play_pcm(pcm)
