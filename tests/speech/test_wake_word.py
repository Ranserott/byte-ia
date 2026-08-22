"""Tests for the wake-word module.

We focus on the always-available text-match path and the push-to-talk
fallback, since the openWakeWord model weights are not present in CI.
The ONNX backend has a dedicated test that mocks ``openwakeword``.
"""

from __future__ import annotations

import sys
import threading
import types
from unittest import mock

import pytest

from openjarvis.speech import wake_word
from openjarvis.speech.wake_word import (
    DEFAULT_WAKE_PHRASES,
    OpenWakeWordBackend,
    TextMatchBackend,
    WakeConfig,
    WakeEvent,
    WakeWordDetector,
    _normalize,
    strip_wake_phrase,
)


# ---------------------------------------------------------------------------
# TextMatchBackend
# ---------------------------------------------------------------------------


class TestTextMatchBackend:
    def test_match_returns_event_for_exact_phrase(self):
        backend = TextMatchBackend()
        event = backend.match("oye jarvis")
        assert event is not None
        assert event.phrase == "oye jarvis"
        assert event.backend == "text_match"
        assert event.confidence == 1.0

    def test_match_returns_event_for_prefix(self):
        backend = TextMatchBackend()
        event = backend.match("Oye Jarvis, qué tiempo hace")
        assert event is not None
        assert event.phrase == "oye jarvis"

    def test_match_returns_none_for_unrelated_text(self):
        backend = TextMatchBackend()
        assert backend.match("hola, buen día") is None
        assert backend.match("") is None
        assert backend.match("oye") is None  # not a complete phrase

    def test_match_is_case_insensitive(self):
        backend = TextMatchBackend()
        assert backend.match("HEY JARVIS!") is not None

    def test_match_strips_accents(self):
        backend = TextMatchBackend(phrases=("oye järvis",))
        # Accented form should match because we NFKD-decompose.
        assert backend.match("oye järvis hola") is not None

    def test_match_english_alias(self):
        backend = TextMatchBackend()
        assert backend.match("hey jarvis what's the weather") is not None

    def test_detect_no_op_for_raw_audio(self):
        backend = TextMatchBackend()
        # 1280 samples of silence → still nothing.
        assert backend.detect(b"\x00" * 2560) is None

    def test_custom_phrases(self):
        backend = TextMatchBackend(phrases=("aló jarvis",))
        assert backend.match("aló jarvis, abrí el erp") is not None
        assert backend.match("oye jarvis") is None  # not in our list


# ---------------------------------------------------------------------------
# strip_wake_phrase
# ---------------------------------------------------------------------------


class TestStripWakePhrase:
    def test_strips_spanish_phrase(self):
        assert strip_wake_phrase("Oye Jarvis, qué tiempo hace") == "qué tiempo hace"

    def test_strips_with_trailing_comma(self):
        # Real ASR often emits "Jarvis," with a comma.
        assert strip_wake_phrase("oye jarvis,recordá la compra") == "recordá la compra"

    def test_no_phrase_returns_input(self):
        assert strip_wake_phrase("hola, buen día") == "hola, buen día"

    def test_just_phrase_returns_empty(self):
        assert strip_wake_phrase("oye jarvis") == ""

    def test_accepts_custom_phrases(self):
        result = strip_wake_phrase("aló jarvis traeme café", phrases=("aló jarvis",))
        assert result == "traeme café"


# ---------------------------------------------------------------------------
# Normalize helper
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_lowercases_and_strips(self):
        assert _normalize("  HELLO  ") == "hello"

    def test_strips_accents(self):
        assert _normalize("Óye Járvis") == "oye jarvis"

    def test_collapses_whitespace(self):
        assert _normalize("oye   jarvis") == "oye jarvis"


# ---------------------------------------------------------------------------
# OpenWakeWordBackend (lazy load, mocked model)
# ---------------------------------------------------------------------------


class TestOpenWakeWordBackend:
    def test_health_false_when_dependency_missing(self):
        """If openwakeword is not installed, the backend reports unhealthy."""
        backend = OpenWakeWordBackend(model_name="hey_jarvis")
        # Without openwakeword, healthy should be False.
        assert backend.healthy is False

    def test_detect_returns_none_when_unavailable(self):
        backend = OpenWakeWordBackend(model_name="hey_jarvis")
        assert backend.detect(b"\x00" * 2560) is None

    def test_detect_with_mocked_model_emits_event(self, monkeypatch):
        """Inject a fake openwakeword module and confirm detect() uses it."""

        fake_model = mock.MagicMock()
        fake_model.predict.return_value = {"hey_jarvis": 0.87, "other_model": 0.1}

        fake_module = types.ModuleType("openwakeword")
        fake_model_module = types.ModuleType("openwakeword.model")
        ModelFactory = mock.MagicMock(return_value=fake_model)
        setattr(fake_model_module, "Model", ModelFactory)
        setattr(fake_module, "model", fake_model_module)
        sys.modules["openwakeword"] = fake_module
        sys.modules["openwakeword.model"] = fake_model_module

        try:
            backend = OpenWakeWordBackend(model_name="hey_jarvis", threshold=0.5)
            assert backend.healthy is True

            frame = b"\x00" * 2560
            event = backend.detect(frame)
            assert event is not None
            assert event.phrase == "hey_jarvis"
            assert event.confidence == pytest.approx(0.87)
            assert event.backend == "openwakeword"
        finally:
            sys.modules.pop("openwakeword", None)
            sys.modules.pop("openwakeword.model", None)

    def test_detect_below_threshold_returns_none(self, monkeypatch):
        fake_model = mock.MagicMock()
        fake_model.predict.return_value = {"hey_jarvis": 0.2}

        fake_module = types.ModuleType("openwakeword")
        fake_model_module = types.ModuleType("openwakeword.model")
        ModelFactory = mock.MagicMock(return_value=fake_model)
        setattr(fake_model_module, "Model", ModelFactory)
        setattr(fake_module, "model", fake_model_module)
        sys.modules["openwakeword"] = fake_module
        sys.modules["openwakeword.model"] = fake_model_module

        try:
            backend = OpenWakeWordBackend(model_name="hey_jarvis", threshold=0.5)
            assert backend.detect(b"\x00" * 2560) is None
            assert backend.last_scores == {"hey_jarvis": 0.2}
        finally:
            sys.modules.pop("openwakeword", None)
            sys.modules.pop("openwakeword.model", None)


# ---------------------------------------------------------------------------
# WakeWordDetector façade
# ---------------------------------------------------------------------------


class TestWakeWordDetector:
    def test_uses_onnx_when_available(self):
        # Mark the ONNX backend as healthy via a stub instead of patching the
        # read-only property (mock.patch.object requires a setter).
        backend = OpenWakeWordBackend(model_name="hey_jarvis", threshold=0.5)

        class _StubHealthy:
            def __init__(self, real_backend):
                self._real = real_backend

            def __getattr__(self, name):
                return getattr(self._real, name)

            @property
            def healthy(self):  # type: ignore[override]
                return True

        detector = WakeWordDetector()
        detector.onnx = _StubHealthy(detector.onnx)  # type: ignore[assignment]
        assert detector.backend_in_use == "openwakeword"

    def test_falls_back_to_text_match(self):
        detector = WakeWordDetector()
        # On a CI host openwakeword is rarely installed → text_match path.
        assert detector.backend_in_use in {"openwakeword", "text_match"}

    def test_match_delegates_to_text_match(self):
        detector = WakeWordDetector()
        event = detector.match("oye jarvis, hola")
        assert event is not None
        assert event.backend == "text_match"

    def test_detect_with_no_audio_returns_none_when_no_onnx(self):
        detector = WakeWordDetector()
        # When openwakeword is missing, detect() returns None.
        with mock.patch.object(detector.onnx, "detect", return_value=None):
            assert detector.detect(b"\x00" * 2560) is None


# ---------------------------------------------------------------------------
# Push-to-talk fallback
# ---------------------------------------------------------------------------


class TestPushToTalk:
    def test_pynput_path_returns_immediately_when_pressed(self):
        """Pretend pynput is installed and the user presses Ctrl+Space."""

        # Use sentinel-style Key instances so the isinstance check in
        # ``_format_pynput_key`` works on the fake module too.
        class _Key:
            ctrl = "ctrl"
            shift = "shift"
            alt = "alt"
            space = "space"

            def __init__(self, name: str) -> None:
                self.name = name

            def __eq__(self, other: object) -> bool:
                return isinstance(other, _Key) and self.name == other.name

            def __hash__(self) -> int:
                return hash(self.name)

        class _KeyCode:
            char = None

        class _Listener:
            def __init__(self, on_press):
                self._on_press = on_press

            def start(self):
                # Simulate the user hitting Ctrl+Space on a background thread.
                def _fire():
                    self._on_press(_Key("ctrl"))
                    self._on_press(_Key("space"))

                threading.Thread(target=_fire, daemon=True).start()

            def stop(self):
                pass

        fake_keyboard = types.ModuleType("pynput.keyboard")
        setattr(fake_keyboard, "Key", _Key)
        setattr(fake_keyboard, "KeyCode", _KeyCode)
        setattr(fake_keyboard, "Listener", _Listener)

        fake_pkg = types.ModuleType("pynput")
        setattr(fake_pkg, "keyboard", fake_keyboard)
        sys.modules["pynput"] = fake_pkg
        sys.modules["pynput.keyboard"] = fake_keyboard

        try:
            assert wake_word.wait_for_push_to_talk(timeout=1.0) is True
        finally:
            sys.modules.pop("pynput", None)
            sys.modules.pop("pynput.keyboard", None)

    def test_returns_false_when_timeout_expires(self):
        # No pynput + non-interactive stdin → should not block; with no
        # input available it returns False.
        result = wake_word.wait_for_push_to_talk(timeout=0.0)
        assert result is False


# ---------------------------------------------------------------------------
# WakeConfig defaults
# ---------------------------------------------------------------------------


def test_default_wake_config():
    config = WakeConfig()
    assert "oye jarvis" in config.phrases
    assert "hey jarvis" in config.phrases
    assert config.threshold == 0.5
    assert config.model_name == "hey_jarvis"


def test_default_wake_phrases_constant():
    # Sanity check — the default tuple is exposed.
    assert "oye jarvis" in DEFAULT_WAKE_PHRASES
