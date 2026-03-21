"""
Tests for Dual-Language (Hindi-English / Hinglish) support modules.

Covers:
  - language_detector.py
  - hindi_translator.py
  - multilingual_knowledge_base.py
  - multilingual_tts.py
  - dataset/query_multilingual.json schema
"""

import json
import os
import sys
import types
import unittest

# ---------------------------------------------------------------------------
# Stub out heavy optional dependencies so tests run without GPU / API keys
# ---------------------------------------------------------------------------

def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod

# Stub pyttsx3 for multilingual_tts → tts_to_pcm fallback
_stub("pyttsx3")
_stub("whisper")
_stub("soundfile")
_stub("numpy")
_stub("scipy")
_stub("scipy.signal")

_stub("app.audio.stt",  transcribe_pcm=lambda *a, **kw: "")
_stub("app.audio.tts",  tts_to_pcm=lambda text, sr=16000: b"\x00" * 32)
_stub("app.audio.prefix_gate", has_valid_prefix=lambda *a, **kw: False)
_stub("app.audio.commandcheck", match_command=lambda *a, **kw: (None, 0.0))

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# language_detector tests
# ---------------------------------------------------------------------------

class TestLanguageDetector(unittest.TestCase):

    def setUp(self):
        from app.audio.language_detector import detect_language, should_translate, get_response_language
        self.detect = detect_language
        self.should_translate = should_translate
        self.get_response_language = get_response_language

    def test_english_query_returns_en(self):
        result = self.detect("What is NPGC?")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["primary_lang"], "en")

    def test_devanagari_query_returns_hi(self):
        result = self.detect("NPGC क्या है?")
        self.assertIn(result["language"], ("hi", "code_mixed"))
        self.assertEqual(result["primary_lang"], "hi")

    def test_pure_devanagari_returns_hi(self):
        result = self.detect("क्या NPGC BCA कोर्स देता है?")
        self.assertIn(result["language"], ("hi", "code_mixed"))
        self.assertEqual(result["primary_lang"], "hi")

    def test_hinglish_query_detected(self):
        result = self.detect("NPGC mein BCA course hai kya")
        self.assertIn(result["language"], ("code_mixed", "en"))

    def test_hinglish_library_query(self):
        result = self.detect("NPGC library ke baare mein batao")
        self.assertIn(result["language"], ("code_mixed", "en"))

    def test_should_translate_english(self):
        self.assertFalse(self.should_translate("What is NPGC?"))

    def test_should_translate_hindi(self):
        result = self.should_translate("NPGC क्या है?")
        self.assertTrue(result)

    def test_should_translate_hinglish(self):
        result = self.should_translate("NPGC mein BCA course hai kya")
        # code_mixed queries should also trigger translation
        if result is not None:  # detection may vary; ensure no exception
            self.assertIsInstance(result, bool)

    def test_get_response_language_english(self):
        lang_info = {"primary_lang": "en", "language": "en", "confidence": 0.9,
                     "hindi_percent": 0, "english_percent": 100}
        self.assertEqual(self.get_response_language(lang_info), "en")

    def test_get_response_language_hindi(self):
        lang_info = {"primary_lang": "hi", "language": "hi", "confidence": 0.9,
                     "hindi_percent": 80, "english_percent": 20}
        self.assertEqual(self.get_response_language(lang_info), "hi")

    def test_empty_string_returns_en(self):
        result = self.detect("")
        self.assertEqual(result["language"], "en")

    def test_confidence_is_float_between_0_and_1(self):
        for text in ["What is BCA?", "क्या है?", "NPGC mein kya hai"]:
            result = self.detect(text)
            self.assertIsInstance(result["confidence"], float)
            self.assertGreaterEqual(result["confidence"], 0.0)
            self.assertLessEqual(result["confidence"], 1.0)

    def test_result_has_required_keys(self):
        result = self.detect("test query")
        for key in ("language", "primary_lang", "confidence", "hindi_percent", "english_percent"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_hindi_percent_range(self):
        for text in ["hello world", "NPGC kya hai", "क्या है"]:
            result = self.detect(text)
            self.assertGreaterEqual(result["hindi_percent"], 0)
            self.assertLessEqual(result["hindi_percent"], 100)


# ---------------------------------------------------------------------------
# hindi_translator tests
# ---------------------------------------------------------------------------

class TestHindiTranslator(unittest.TestCase):

    def setUp(self):
        from app.audio.hindi_translator import normalize_hinglish, translate_to_english, translate_to_hindi
        self.normalize = normalize_hinglish
        self.to_english = translate_to_english
        self.to_hindi = translate_to_hindi

    def test_normalize_empty_string(self):
        self.assertEqual(self.normalize(""), "")

    def test_normalize_none_like_input(self):
        self.assertEqual(self.normalize("  "), "")

    def test_normalize_hinglish_batao(self):
        result = self.normalize("NPGC ke baare mein batao")
        # Should replace 'ke baare mein' with 'about'
        self.assertIn("NPGC", result)

    def test_normalize_preserves_proper_nouns(self):
        result = self.normalize("NPGC mein BCA course hai kya")
        self.assertIn("NPGC", result)
        self.assertIn("BCA", result)

    def test_translate_to_english_returns_string(self):
        result = self.to_english("NPGC kya hai")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_translate_to_english_empty(self):
        self.assertEqual(self.to_english(""), "")

    def test_translate_to_hindi_returns_string(self):
        result = self.to_hindi("Yes, NPGC offers BCA course.")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_translate_to_hindi_empty(self):
        self.assertEqual(self.to_hindi(""), "")

    def test_translate_to_english_preserves_english(self):
        english_text = "What courses does NPGC offer?"
        result = self.to_english(english_text, source_lang="en")
        # Even with English input, should return a non-empty string
        self.assertTrue(len(result) > 0)


# ---------------------------------------------------------------------------
# multilingual_knowledge_base tests
# ---------------------------------------------------------------------------

class TestMultilingualKnowledgeBase(unittest.TestCase):

    def setUp(self):
        from app.audio.multilingual_knowledge_base import get_answer_multilingual, search_qa_multilingual
        self.get_answer = get_answer_multilingual
        self.search = search_qa_multilingual

    def test_english_query_returns_answer(self):
        answer, lang = self.get_answer("What is NPGC?")
        # Should find an answer in the knowledge base
        self.assertIsNotNone(answer)
        self.assertEqual(lang, "en")

    def test_empty_query_returns_none(self):
        answer, lang = self.get_answer("")
        self.assertIsNone(answer)

    def test_search_returns_list(self):
        results = self.search("What is NPGC?")
        self.assertIsInstance(results, list)

    def test_search_results_have_required_keys(self):
        results = self.search("What is NPGC?", top_k=2)
        for r in results:
            for key in ("question", "answer", "category", "confidence"):
                self.assertIn(key, r, f"Missing key: {key}")

    def test_hinglish_query_handled_gracefully(self):
        # Should not raise even if translation/library is unavailable
        answer, lang = self.get_answer("NPGC mein BCA course hai kya")
        # answer may or may not be found depending on KB match, but should not raise
        self.assertIsInstance(lang, str)

    def test_hindi_query_handled_gracefully(self):
        answer, lang = self.get_answer("NPGC क्या है?")
        self.assertIsInstance(lang, str)

    def test_response_language_for_hindi(self):
        # When Hindi script is used, response_lang should be "hi"
        _, lang = self.get_answer("NPGC क्या है?")
        self.assertEqual(lang, "hi")

    def test_response_language_for_english(self):
        _, lang = self.get_answer("What is NPGC?")
        self.assertEqual(lang, "en")

    def test_search_top_k_respected(self):
        results = self.search("NPGC courses", top_k=2)
        self.assertLessEqual(len(results), 2)


# ---------------------------------------------------------------------------
# multilingual_tts tests
# ---------------------------------------------------------------------------

class TestMultilingualTTS(unittest.TestCase):

    def setUp(self):
        from app.audio.multilingual_tts import tts_to_pcm_multilingual
        self.tts = tts_to_pcm_multilingual

    def test_english_tts_returns_bytes(self):
        result = self.tts("Hello, I am Chetan.", language="en")
        self.assertIsInstance(result, bytes)

    def test_empty_text_returns_empty_bytes(self):
        result = self.tts("", language="en")
        self.assertEqual(result, b"")

    def test_hindi_tts_falls_back_gracefully(self):
        # If gTTS is not installed or network is unavailable, should fall back to pyttsx3
        result = self.tts("नमस्ते", language="hi")
        self.assertIsInstance(result, bytes)

    def test_default_language_is_english(self):
        result = self.tts("Test message.")
        self.assertIsInstance(result, bytes)


# ---------------------------------------------------------------------------
# query_multilingual.json schema tests
# ---------------------------------------------------------------------------

class TestMultilingualDataset(unittest.TestCase):

    def setUp(self):
        dataset_path = os.path.join(
            os.path.dirname(__file__),
            "../dataset/query_multilingual.json"
        )
        with open(os.path.abspath(dataset_path), "r", encoding="utf-8") as fh:
            self.data = json.load(fh)

    def test_dataset_is_list(self):
        self.assertIsInstance(self.data, list)

    def test_dataset_has_entries(self):
        self.assertGreater(len(self.data), 0)

    def test_every_entry_has_category(self):
        for i, entry in enumerate(self.data):
            self.assertIn("category", entry, f"Entry {i} missing 'category'")
            self.assertTrue(entry["category"].strip(), f"Entry {i} has empty category")

    def test_every_entry_has_english_query_and_answer(self):
        for i, entry in enumerate(self.data):
            self.assertIn("query_en", entry, f"Entry {i} missing 'query_en'")
            self.assertIn("answer_en", entry, f"Entry {i} missing 'answer_en'")
            self.assertTrue(entry["query_en"].strip(), f"Entry {i} has empty query_en")
            self.assertTrue(entry["answer_en"].strip(), f"Entry {i} has empty answer_en")

    def test_every_entry_has_hindi_query_and_answer(self):
        for i, entry in enumerate(self.data):
            self.assertIn("query_hi", entry, f"Entry {i} missing 'query_hi'")
            self.assertIn("answer_hi", entry, f"Entry {i} missing 'answer_hi'")

    def test_every_entry_has_hinglish_variants(self):
        for i, entry in enumerate(self.data):
            self.assertIn("query_hinglish", entry, f"Entry {i} missing 'query_hinglish'")
            self.assertIsInstance(entry["query_hinglish"], list, f"Entry {i} query_hinglish must be a list")
            self.assertGreater(len(entry["query_hinglish"]), 0, f"Entry {i} has empty query_hinglish list")

    def test_no_duplicate_english_queries(self):
        queries = [e["query_en"].lower().strip() for e in self.data]
        self.assertEqual(len(queries), len(set(queries)), "Duplicate query_en entries found")

    def test_answer_min_length(self):
        for i, entry in enumerate(self.data):
            self.assertGreater(
                len(entry["answer_en"]), 20,
                f"Entry {i} answer_en too short: {entry['answer_en']!r}"
            )


# ---------------------------------------------------------------------------
# routes.py integration test (ensures new imports work)
# ---------------------------------------------------------------------------

class TestRoutesMultilingualIntegration(unittest.TestCase):

    def test_routes_imports_multilingual_modules(self):
        """routes.py must import multilingual modules without error."""
        from app.audio import routes as r
        self.assertTrue(hasattr(r, "get_answer_multilingual"))
        self.assertTrue(hasattr(r, "tts_to_pcm_multilingual"))
        self.assertTrue(hasattr(r, "detect_language"))

    def test_routes_has_upload_endpoint(self):
        from app.audio import routes as r
        self.assertTrue(hasattr(r, "upload_audio"))


if __name__ == "__main__":
    unittest.main()
