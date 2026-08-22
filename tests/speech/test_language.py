"""Tests for the speech language-detection helpers (Mejora 1)."""

from __future__ import annotations

import pytest

from openjarvis.speech.language import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    LanguageDetection,
    default_voice_for,
    detect_language_from_text,
    kokoro_voice_prefix,
    macos_voices_for,
    resolve_stt_language,
)


class TestDetectLanguage:
    """detect_language_from_text() should pick the right code with confidence."""

    def test_empty_returns_default(self) -> None:
        det = detect_language_from_text("")
        assert det.code == DEFAULT_LANGUAGE
        assert det.confidence == 0.0

    def test_whitespace_returns_default(self) -> None:
        det = detect_language_from_text("    \n\t   ")
        assert det.code == DEFAULT_LANGUAGE
        assert det.confidence == 0.0

    def test_spanish_diacritics_signal_strongly(self) -> None:
        # A single Spanish diacritic is enough signal to detect Spanish.
        det = detect_language_from_text("sí")
        assert det.code == "es"
        assert det.matched_tokens >= 1

    def test_spanish_phrase(self) -> None:
        det = detect_language_from_text("¿cuánto vendimos hoy? por favor")
        assert det.code == "es"
        assert det.confidence > 0.3

    def test_english_phrase(self) -> None:
        det = detect_language_from_text("How much did we sell today, please?")
        assert det.code == "en"
        assert det.confidence > 0.3

    def test_portuguese_phrase(self) -> None:
        # "obrigado" is a uniquely Portuguese word.
        det = detect_language_from_text("obrigado, ficou ótimo")
        assert det.code == "pt"
        assert det.confidence > 0.3

    def test_returns_language_detection_dataclass(self) -> None:
        det = detect_language_from_text("Hola, gracias")
        assert isinstance(det, LanguageDetection)
        assert det.code in SUPPORTED_LANGUAGES
        assert 0.0 <= det.confidence <= 1.0


class TestResolveSttLanguage:
    """resolve_stt_language() precedence order."""

    def test_explicit_wins_over_everything(self) -> None:
        # Even if transcribed text is clearly Spanish, explicit "en" wins.
        assert (
            resolve_stt_language(
                explicit="en",
                transcribed_text="¿cómo estás?",
                configured_default="pt",
            )
            == "en"
        )

    def test_transcribed_text_used_when_no_explicit(self) -> None:
        assert (
            resolve_stt_language(
                transcribed_text="¿cuánto vendimos hoy?",
            )
            == "es"
        )

    def test_configured_default_used_when_no_signal(self) -> None:
        # gibberish that triggers no detection -> use configured default
        assert (
            resolve_stt_language(
                transcribed_text="asdf",
                configured_default="pt",
            )
            == "pt"
        )

    def test_fallback_to_project_default(self) -> None:
        assert resolve_stt_language() == DEFAULT_LANGUAGE

    def test_explicit_with_region_truncated(self) -> None:
        # "es-MX" should be accepted as "es".
        assert resolve_stt_language(explicit="es-MX") == "es"
        assert resolve_stt_language(explicit="es_es") == "es"

    def test_unknown_explicit_falls_through(self) -> None:
        # Unknown explicit code shouldn't raise — fall through to default.
        assert resolve_stt_language(explicit="klingon") == DEFAULT_LANGUAGE


class TestVoiceHelpers:
    """default_voice_for(), kokoro_voice_prefix(), macos_voices_for()."""

    def test_kokoro_spanish_voice(self) -> None:
        assert kokoro_voice_prefix("es") == "e"
        assert default_voice_for("es", "kokoro") == "ef_dora"

    def test_kokoro_english_voice(self) -> None:
        assert default_voice_for("en", "kokoro") == "af_heart"

    def test_kokoro_portuguese_voice(self) -> None:
        assert default_voice_for("pt", "kokoro") == "pf_lumia"

    def test_macos_voices_for_spanish(self) -> None:
        voices = list(macos_voices_for("es"))
        assert "Monica" in voices
        assert "Juan" in voices

    def test_macos_default_voice(self) -> None:
        assert default_voice_for("es", "macos_say") == "Monica"
        assert default_voice_for("en", "macos_say") == "Samantha"

    def test_unknown_language_falls_back(self) -> None:
        # An unknown code should return *something* without raising.
        assert default_voice_for("xx", "kokoro") == "af_heart"
        assert list(macos_voices_for("xx")) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
