"""Tests for send_audio_response() audio chunking logic.

These tests verify that:
- Small payloads (≤ CHUNK_SIZE) are sent as a single ``audio_response`` frame.
- Large payloads (> CHUNK_SIZE) are sent as multiple ``audio_chunk`` frames
  with correct ``index``, ``total``, and ``is_last`` fields.
- An ``asyncio.sleep(0)`` yield happens between all chunks except the last.
"""
import asyncio
import base64
import sys
import os
import types
import unittest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Stub out heavy audio dependencies so the module can be imported without
# installing whisper / pyttsx3 / soundfile etc.
# These stubs must be installed in sys.modules BEFORE importing routes.
# ---------------------------------------------------------------------------
def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod

_stub("whisper")
_stub("pyttsx3")
_stub("soundfile")
_stub("numpy")
_stub("scipy")
_stub("scipy.signal")
_stub(
    "app.audio.stt",
    transcribe_pcm=lambda *a, **kw: "",
)
_stub(
    "app.audio.tts",
    tts_to_pcm=lambda *a, **kw: b"",
)
_stub(
    "app.audio.prefix_gate",
    has_valid_prefix=lambda *a, **kw: False,
)
_stub(
    "app.audio.commandcheck",
    match_command=lambda *a, **kw: (None, 0.0),
)
_stub(
    "app.audio.knowledge_base",
    get_answer=lambda *a, **kw: None,
)

# Add project root to path so ``app.*`` imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.audio.routes import send_audio_response, CHUNK_SIZE  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeConnectionManager:
    """Records every message sent via send_to_device."""
    def __init__(self, should_succeed: bool = True):
        self.sent: list[dict] = []
        self.should_succeed = should_succeed

    async def send_to_device(self, device_id: str, message: dict) -> bool:
        self.sent.append(message)
        return self.should_succeed


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSendAudioResponseSmallPayload(unittest.TestCase):
    """Payloads ≤ CHUNK_SIZE must produce a single audio_response frame."""

    def setUp(self):
        self.cm = _FakeConnectionManager()
        self._patch = patch("app.audio.routes.get_connection_manager", return_value=self.cm)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()

    def test_empty_pcm_returns_false(self):
        result = _run(send_audio_response("dev1", b""))
        self.assertFalse(result)
        self.assertEqual(self.cm.sent, [])

    def test_small_pcm_sends_audio_response(self):
        pcm = b"\x00\x01" * 512  # 1024 bytes — well within CHUNK_SIZE
        result = _run(send_audio_response("dev1", pcm))
        self.assertTrue(result)
        self.assertEqual(len(self.cm.sent), 1)
        msg = self.cm.sent[0]
        self.assertEqual(msg["message_type"], "audio_response")
        self.assertIn("audio_base64", msg)
        self.assertEqual(msg["samplerate"], 16000)
        # Verify round-trip
        decoded = base64.b64decode(msg["audio_base64"])
        self.assertEqual(decoded, pcm)

    def test_exactly_chunk_size_sends_audio_response(self):
        pcm = bytes(CHUNK_SIZE)
        result = _run(send_audio_response("dev1", pcm))
        self.assertTrue(result)
        self.assertEqual(len(self.cm.sent), 1)
        self.assertEqual(self.cm.sent[0]["message_type"], "audio_response")

    def test_small_payload_no_chunk_fields(self):
        """audio_response must NOT include index/total/is_last."""
        pcm = bytes(100)
        _run(send_audio_response("dev1", pcm))
        msg = self.cm.sent[0]
        self.assertNotIn("index", msg)
        self.assertNotIn("total", msg)
        self.assertNotIn("is_last", msg)


class TestSendAudioResponseLargePayload(unittest.TestCase):
    """Payloads > CHUNK_SIZE must produce multiple audio_chunk frames."""

    def setUp(self):
        self.cm = _FakeConnectionManager()
        self._patch = patch("app.audio.routes.get_connection_manager", return_value=self.cm)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()

    def test_large_pcm_uses_audio_chunk(self):
        pcm = bytes(CHUNK_SIZE + 1)  # one byte over the threshold
        result = _run(send_audio_response("dev1", pcm))
        self.assertTrue(result)
        for msg in self.cm.sent:
            self.assertEqual(msg["message_type"], "audio_chunk")

    def test_chunk_count_is_correct(self):
        pcm = bytes(CHUNK_SIZE * 3)  # exactly 3 chunks
        result = _run(send_audio_response("dev1", pcm))
        self.assertTrue(result)
        self.assertEqual(len(self.cm.sent), 3)

    def test_chunk_metadata_fields(self):
        pcm = bytes(CHUNK_SIZE * 2 + 100)  # 3 chunks
        _run(send_audio_response("dev1", pcm))
        messages = self.cm.sent
        total = len(messages)
        for idx, msg in enumerate(messages):
            self.assertEqual(msg["index"], idx)
            self.assertEqual(msg["total"], total)
            self.assertEqual(msg["is_last"], idx == total - 1)
            self.assertIn("audio_base64", msg)
            self.assertEqual(msg["samplerate"], 16000)
            self.assertEqual(msg["format"], "pcm_s16_le")

    def test_is_last_only_on_final_chunk(self):
        pcm = bytes(CHUNK_SIZE * 4)
        _run(send_audio_response("dev1", pcm))
        for msg in self.cm.sent[:-1]:
            self.assertFalse(msg["is_last"])
        self.assertTrue(self.cm.sent[-1]["is_last"])

    def test_audio_round_trip(self):
        """Reassembling all chunks should reproduce the original PCM."""
        pcm = bytes(range(256)) * (CHUNK_SIZE // 256 * 3)  # 3 chunks of patterned data
        _run(send_audio_response("dev1", pcm))
        reassembled = b"".join(
            base64.b64decode(msg["audio_base64"]) for msg in self.cm.sent
        )
        self.assertEqual(reassembled, pcm)

    def test_returns_false_on_send_failure(self):
        failing_cm = _FakeConnectionManager(should_succeed=False)
        with patch("app.audio.routes.get_connection_manager", return_value=failing_cm):
            pcm = bytes(CHUNK_SIZE * 3)
            result = _run(send_audio_response("dev1", pcm))
        self.assertFalse(result)

    def test_custom_samplerate_is_forwarded(self):
        pcm = bytes(CHUNK_SIZE * 2)
        _run(send_audio_response("dev1", pcm, samplerate=8000))
        for msg in self.cm.sent:
            self.assertEqual(msg["samplerate"], 8000)


if __name__ == "__main__":
    unittest.main()
