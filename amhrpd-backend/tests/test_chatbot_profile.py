"""Unit tests for the chatbot_profile module."""
import sys
import os
import unittest

# Ensure the project root (amhrpd-backend/) is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.audio.chatbot_profile import (
    get_chatbot_profile,
    is_profile_question,
    get_profile_stats,
    PROFILE_DATA,
    _FLAT_PROFILE,
)


class TestGetChatbotProfile(unittest.TestCase):
    """Tests for get_chatbot_profile()."""

    # --- Identity queries ---
    def test_who_are_you(self):
        answer = get_chatbot_profile("Who are you?")
        self.assertIsNotNone(answer)
        self.assertIn("Chetan", answer)

    def test_what_is_your_name(self):
        answer = get_chatbot_profile("What is your name?")
        self.assertIsNotNone(answer)
        self.assertIn("Chetan", answer)

    def test_tell_me_about_yourself(self):
        answer = get_chatbot_profile("Tell me about yourself")
        self.assertIsNotNone(answer)
        self.assertIn("Chetan", answer)

    def test_what_are_you(self):
        answer = get_chatbot_profile("What are you?")
        self.assertIsNotNone(answer)

    def test_introduce_yourself(self):
        answer = get_chatbot_profile("Introduce yourself")
        self.assertIsNotNone(answer)
        self.assertIn("Chetan", answer)

    # --- Capabilities queries ---
    def test_what_can_you_do(self):
        answer = get_chatbot_profile("What can you do?")
        self.assertIsNotNone(answer)

    def test_what_are_your_capabilities(self):
        answer = get_chatbot_profile("What are your capabilities?")
        self.assertIsNotNone(answer)

    def test_list_your_features(self):
        answer = get_chatbot_profile("List your features")
        self.assertIsNotNone(answer)

    def test_what_commands_can_i_give(self):
        answer = get_chatbot_profile("What commands can I give?")
        self.assertIsNotNone(answer)

    # --- Creator queries ---
    def test_who_made_you(self):
        answer = get_chatbot_profile("Who made you?")
        self.assertIsNotNone(answer)
        self.assertIn("Abhishek", answer)

    def test_who_created_you(self):
        answer = get_chatbot_profile("Who created you?")
        self.assertIsNotNone(answer)
        self.assertIn("Abhishek", answer)

    def test_who_built_you(self):
        answer = get_chatbot_profile("Who built you?")
        self.assertIsNotNone(answer)
        self.assertIn("Abhishek", answer)

    def test_who_is_your_developer(self):
        answer = get_chatbot_profile("Who is your developer?")
        self.assertIsNotNone(answer)
        self.assertIn("Abhishek", answer)

    def test_tell_me_about_your_creator(self):
        answer = get_chatbot_profile("Tell me about your creator")
        self.assertIsNotNone(answer)
        self.assertIn("Abhishek", answer)

    # --- Collaboration queries ---
    def test_what_can_we_do_together(self):
        answer = get_chatbot_profile("What can we do together?")
        self.assertIsNotNone(answer)

    def test_what_is_your_purpose(self):
        answer = get_chatbot_profile("What is your purpose?")
        self.assertIsNotNone(answer)

    def test_how_can_you_help_me(self):
        answer = get_chatbot_profile("How can you help me?")
        self.assertIsNotNone(answer)

    def test_how_can_i_use_you(self):
        answer = get_chatbot_profile("How can I use you?")
        self.assertIsNotNone(answer)

    # --- Help & Guidance queries ---
    def test_help_me_get_started(self):
        answer = get_chatbot_profile("Help me get started")
        self.assertIsNotNone(answer)

    def test_how_do_i_use_you(self):
        answer = get_chatbot_profile("How do I use you?")
        self.assertIsNotNone(answer)

    def test_guide_me(self):
        answer = get_chatbot_profile("Guide me")
        self.assertIsNotNone(answer)

    def test_tell_me_more_about_you(self):
        answer = get_chatbot_profile("Tell me more about you")
        self.assertIsNotNone(answer)
        self.assertIn("Chetan", answer)

    def test_how_do_i_talk_to_you(self):
        answer = get_chatbot_profile("How do I talk to you?")
        self.assertIsNotNone(answer)

    # --- Case / whitespace insensitivity ---
    def test_case_insensitive_match(self):
        self.assertIsNotNone(get_chatbot_profile("WHO ARE YOU"))
        self.assertIsNotNone(get_chatbot_profile("who are you"))
        self.assertIsNotNone(get_chatbot_profile("Who Are You?"))

    def test_extra_whitespace(self):
        answer = get_chatbot_profile("  who  are  you  ")
        self.assertIsNotNone(answer)

    # --- No-match cases ---
    def test_empty_query_returns_none(self):
        self.assertIsNone(get_chatbot_profile(""))

    def test_whitespace_only_returns_none(self):
        self.assertIsNone(get_chatbot_profile("   "))

    def test_none_input_returns_none(self):
        self.assertIsNone(get_chatbot_profile(None))  # type: ignore[arg-type]

    def test_unrelated_query_returns_none(self):
        # A clearly unrelated query should not match any profile entry
        self.assertIsNone(get_chatbot_profile("xyzzy plugh irrelevant zork"))


class TestIsProfileQuestion(unittest.TestCase):
    """Tests for is_profile_question()."""

    def test_identity_detected(self):
        self.assertTrue(is_profile_question("Who are you?"))

    def test_capability_detected(self):
        self.assertTrue(is_profile_question("What can you do?"))

    def test_creator_detected(self):
        self.assertTrue(is_profile_question("Who made you?"))

    def test_collaboration_detected(self):
        self.assertTrue(is_profile_question("What can we do together?"))

    def test_unrelated_not_detected(self):
        self.assertFalse(is_profile_question("xyzzy plugh irrelevant zork"))

    def test_empty_not_detected(self):
        self.assertFalse(is_profile_question(""))


class TestGetProfileStats(unittest.TestCase):
    """Tests for get_profile_stats()."""

    def test_returns_dict(self):
        stats = get_profile_stats()
        self.assertIsInstance(stats, dict)

    def test_has_required_keys(self):
        stats = get_profile_stats()
        self.assertIn("total_profile_pairs", stats)
        self.assertIn("categories", stats)
        self.assertIn("status", stats)

    def test_total_pairs_is_30(self):
        stats = get_profile_stats()
        self.assertEqual(stats["total_profile_pairs"], 30)

    def test_all_five_categories_present(self):
        stats = get_profile_stats()
        expected = {"identity", "capabilities", "creator", "collaboration", "help"}
        self.assertEqual(set(stats["categories"].keys()), expected)

    def test_status_is_ready(self):
        stats = get_profile_stats()
        self.assertIn("Ready", stats["status"])


class TestProfileDataIntegrity(unittest.TestCase):
    """Structural checks on PROFILE_DATA and _FLAT_PROFILE."""

    def test_flat_profile_length_matches_data(self):
        total = sum(len(v) for v in PROFILE_DATA.values())
        self.assertEqual(len(_FLAT_PROFILE), total)

    def test_every_entry_has_required_fields(self):
        for entry in _FLAT_PROFILE:
            self.assertIn("category", entry)
            self.assertIn("query", entry)
            self.assertIn("answer", entry)
            self.assertTrue(entry["answer"].strip(), "Answer must not be empty")

    def test_no_duplicate_queries(self):
        queries = [e["query"] for e in _FLAT_PROFILE]
        self.assertEqual(len(queries), len(set(queries)), "Duplicate queries found")


if __name__ == "__main__":
    unittest.main()
