import os
import tempfile
import numpy as np
import soundfile as sf
import whisper
import pyttsx3
from scipy.signal import resample

TARGET_SAMPLE_RATE = 16000


# ============================================================
# STEP 1: Generate RAW PCM bytes (16-bit, mono, 16kHz)
# ============================================================
def generate_pcm_from_text(text: str, target_sr: int = 16000) -> bytes:
    """
    Offline TTS -> WAV -> resample -> raw PCM bytes
    (Exactly what ESP32 would send, minus mic)
    """

    engine = pyttsx3.init()
    engine.setProperty("rate", 150)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        wav_path = f.name

    engine.save_to_file(text, wav_path)
    engine.runAndWait()

    # Load WAV
    audio, sr = sf.read(wav_path, dtype="float32")
    os.remove(wav_path)

    # Stereo -> mono
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)

    # Resample to 16kHz if needed
    if sr != target_sr:
        new_len = int(len(audio) * target_sr / sr)
        audio = resample(audio, new_len)

    # Float32 -> int16 PCM
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16)

    return pcm.tobytes()


# ============================================================
# STEP 2: Speech-to-Text using LOCAL Whisper
# ============================================================
class SpeechToText:
    def __init__(self, model_name: str = "base"):
        print("Loading Whisper model...")
        self.model = whisper.load_model(model_name)

    def transcribe(self, pcm_bytes: bytes, samplerate: int = 16000) -> str:
        """
        Raw int16 PCM -> Whisper (no WAV, no ffmpeg)
        """

        # int16 PCM -> float32
        audio = (
            np.frombuffer(pcm_bytes, dtype=np.int16)
            .astype(np.float32) / 32768.0
        )

        # Whisper expects 16kHz mono float32
        assert samplerate == 16000, "Whisper expects 16kHz audio"

        result = self.model.transcribe(audio, fp16=False)
        return result["text"]

# ============================================================
# STEP 3: Full end-to-end test
# ============================================================
if __name__ == "__main__":
    TEST_TEXT = "My name is chikki chikki chikki chikkki , my name is boom boom boom boom boom"

    print("Generating raw PCM...")
    pcm_bytes = generate_pcm_from_text(TEST_TEXT)

    print(f"PCM size: {len(pcm_bytes)} bytes")

    stt = SpeechToText(model_name="base")

    print("Running Whisper locally...")
    transcription = stt.transcribe(pcm_bytes)

    print("\n================ TRANSCRIPTION ================")
    print(transcription)
    print("================================================")
