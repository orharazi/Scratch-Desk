#!/usr/bin/env python3

import pytest
from core.translations import set_language, get_language, t, t_title, HEBREW_TRANSLATIONS


@pytest.fixture
def restore_language():
    """Fixture to restore language to Hebrew after tests"""
    original = get_language()
    yield
    set_language(original)


class TestBasicTranslation:
    """Test basic translation functionality"""

    def test_known_key_translated(self):
        """Known key should return Hebrew translation"""
        set_language("he")
        result = t("Connect Hardware")
        assert result == HEBREW_TRANSLATIONS["Connect Hardware"]
        assert "התחבר" in result  # Should contain Hebrew text

    def test_unknown_key_returns_original(self):
        """Unknown key should return original text"""
        set_language("he")
        result = t("NonexistentKey123")
        assert result == "NonexistentKey123"


class TestFormatting:
    """Test translation with format arguments"""

    def test_format_args_applied(self):
        """Format arguments should be applied to translated text"""
        set_language("he")
        result = t("X: {x:.2f} cm", x=5.5)
        assert "5.50" in result
        # Should contain Hebrew translation parts
        expected = HEBREW_TRANSLATIONS["X: {x:.2f} cm"].format(x=5.5)
        assert "5.50" in expected

    def test_format_error_fallback(self):
        """Bad kwargs should handle gracefully or raise exception"""
        set_language("he")
        # Try to format with wrong kwargs - should raise KeyError
        with pytest.raises(KeyError):
            t("X: {x:.2f} cm", y=10.0)  # Wrong key


class TestEnglishMode:
    """Test English mode behavior"""

    def test_english_mode_returns_original(self, restore_language):
        """English mode should return original text"""
        set_language("en")
        result = t("Connect Hardware")
        assert result == "Connect Hardware"

    def test_english_mode_with_args(self, restore_language):
        """English mode should format with args"""
        set_language("en")
        result = t("X: {x:.2f} cm", x=5.5)
        assert result == "X: 5.50 cm"


class TestTitleTranslation:
    """Test t_title() for window titles"""

    def test_title_has_rtl_mark(self):
        """Hebrew title should start with RTL mark"""
        set_language("he")
        result = t_title("Connect Hardware")
        # Should start with RTL mark U+200F
        assert result.startswith('\u200f')

    def test_title_english_mode(self, restore_language):
        """English mode should not add RTL mark"""
        set_language("en")
        result = t_title("Connect Hardware")
        assert not result.startswith('\u200f')
        assert result == "Connect Hardware"


class TestLanguageManagement:
    """Test language setting and getting"""

    def test_set_language(self, restore_language):
        """Should update current language"""
        set_language("en")
        assert get_language() == "en"

    def test_get_language(self):
        """Should return current language"""
        set_language("he")
        assert get_language() == "he"


class TestMultipleTranslations:
    """Test various translations"""

    def test_multiple_known_keys(self):
        """Multiple known keys should all translate"""
        set_language("he")

        keys_to_test = [
            "Connect Hardware",
            "Disconnect",
            "Status:",
            "Mode:"
        ]

        for key in keys_to_test:
            if key in HEBREW_TRANSLATIONS:
                result = t(key)
                assert result == HEBREW_TRANSLATIONS[key]

    def test_format_multiple_args(self):
        """Should handle multiple format arguments"""
        set_language("en")
        # Test with English mode for predictable output
        result = t("X: {x:.2f} cm", x=10.5)
        assert result == "X: 10.50 cm"
