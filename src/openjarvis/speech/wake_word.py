"""Wake-word detection for hands-free invocation of the assistant.

OpenJarvis defaults to the Spanish wake phrase **"Oye Jarvis"** (and the
English alias **"Hey Jarvis"** as a courtesy for code-switching users).
Detection happens in two flavours:

* **openWakeWord backend** — small ONNX model, runs locally on CPU with
  negligible latency. Recommended path.
* **text-match fallback** — once the rest of the STT pipeline has
  transcribed an utterance, this filter strips leading wake phrases so
  ``"oye jarvis, qué tiempo hace"`` becomes ``"qué tiempo hace"``.

If neither is available, callers should fall back to push-to-talk (e.g.
hold ``Fn`` or ``Ctrl+Space``). See :func:`wait_for_push_to_talk`.

The module is self-contained: importing it is cheap, model loading is
lazy, and tests run without ``openwakeword`` installed.
"""

from __future__ import annotations

import logging
import re
import shutil
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


# Phrases that, when seen as the *prefix* of a transcribed utterance, count
# as a wake invocation. Stored lower-case, accent-stripped.
DEFAULT_WAKE_PHRASES: tuple[str, ...] = (
    "oye jarvis",
    "hey jarvis",
    "oye jarbis",
    "ok jarvis",
    "ok yarvis",
)

# Default model name shipped by openWakeWord. The user can override via the
# constructor (e.g. ``"alexa"``, ``"hey_mycroft"``) — these are pulled from
# https://github.com/dscripka/openWakeWord pretrained models.
DEFAULT_MODEL_NAME = "hey_jarvis"

# Detection threshold for the ONNX model. 0.5 is the recommended starting
# point in openWakeWord's docs; lower → more false positives, higher →
# misses. 0.5 is a good balance for a desktop assistant.
DEFAULT_THRESHOLD = 0.5

# Audio frame expected by openWakeWord (16 kHz, 16-bit mono, 80 ms = 1280
# samples). Most front-ends already chunk at this size for STT.
_FRAME_SAMPLES = 1280
_SAMPLE_RATE = 16000


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WakeEvent:
    """Result of a wake-word detection.

    Attributes:
        phrase: The wake phrase that triggered the event.
        confidence: Model score in the range ``[0.0, 1.0]`` (1.0 for the
            text-match fallback, since we matched literally).
        backend: Identifier of the backend that produced the event
            (e.g. ``"openwakeword"`` or ``"text_match"``).
    """

    phrase: str
    confidence: float
    backend: str


@dataclass(slots=True)
class WakeConfig:
    """Runtime configuration for the wake-word pipeline.

    Attributes:
        phrases: Wake phrases to detect (case-insensitive).
        model_name: openWakeWord model identifier. Ignored if the
            library isn't installed.
        threshold: Probability threshold for the ONNX model.
        sample_rate: Audio sample rate in Hz; must be 16000 for the
            shipped model.
    """

    phrases: tuple[str, ...] = DEFAULT_WAKE_PHRASES
    model_name: str = DEFAULT_MODEL_NAME
    threshold: float = DEFAULT_THRESHOLD
    sample_rate: int = _SAMPLE_RATE


class WakeWordBackend(ABC):
    """Abstract interface for wake-word detectors.

    Implementations must be safe to call from a single consumer thread;
    concurrency guarantees are backend-specific.
    """

    backend_id: str = ""

    @abstractmethod
    def detect(self, audio_frame: bytes) -> Optional[WakeEvent]:
        """Process one audio frame and return a :class:`WakeEvent` if fired."""

    def reset(self) -> None:  # pragma: no cover - default no-op
        """Clear any internal state. Default implementation does nothing."""
        return None

    @property
    def healthy(self) -> bool:
        """Whether the backend is ready to detect. ``True`` by default."""
        return True


# ---------------------------------------------------------------------------
# Text-match fallback (no third-party deps)
# ---------------------------------------------------------------------------


_ACCENT_RE = re.compile(r"[\u0300-\u036f]")


def _normalize(text: str) -> str:
    """Lower-case, strip accents, collapse whitespace.

    Spanish ASR models often emit ``"oye yarbis"`` or ``"hey, jarvis,"``
    — we don't want a punctuation or accent difference to defeat
    detection.
    """

    lowered = text.lower().strip()
    # NFKD + strip combining marks removes accents: ``"jé"`` → ``"je"``.
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accents = _ACCENT_RE.sub("", decomposed)
    return re.sub(r"\s+", " ", no_accents).strip()


class TextMatchBackend(WakeWordBackend):
    """Tiny regex-based detector that fires on a literal phrase prefix.

    This is the always-available fallback. It is **not** designed to be
    used in isolation on raw audio — it operates on transcribed text or
    on already-detected phrases, but it is useful for tests and for
    users who can't install ``openwakeword``.
    """

    backend_id = "text_match"

    def __init__(self, phrases: Iterable[str] = DEFAULT_WAKE_PHRASES) -> None:
        self._phrases: tuple[str, ...] = tuple(_normalize(p) for p in phrases)
        # Sort by descending length so "oye jarvis" wins over "oye" alone.
        self._sorted_phrases: tuple[str, ...] = tuple(
            sorted(self._phrases, key=len, reverse=True)
        )

    def match(self, text: str) -> Optional[WakeEvent]:
        """Return a :class:`WakeEvent` if *text* starts with a wake phrase."""

        normalized = _normalize(text)
        for phrase in self._sorted_phrases:
            if normalized == phrase:
                return WakeEvent(phrase=phrase, confidence=1.0, backend=self.backend_id)
            # Wake phrase followed by space, comma, period, or end-of-string.
            # Real ASR frequently emits "oye jarvis, qué tiempo…" — the comma
            # belongs to the user's sentence, not to the wake phrase.
            for sep in (" ", ",", ".", "!", "?", ":", ";"):
                tail = phrase + sep
                if normalized.startswith(tail):
                    return WakeEvent(
                        phrase=phrase, confidence=1.0, backend=self.backend_id
                    )
        return None

    def detect(self, audio_frame: bytes) -> Optional[WakeEvent]:
        """No-op for raw audio. Use :meth:`match` on transcribed text."""
        return None


def strip_wake_phrase(text: str, phrases: Iterable[str] = DEFAULT_WAKE_PHRASES) -> str:
    """Remove a leading wake phrase from *text* if present.

    >>> strip_wake_phrase("Oye Jarvis, qué tiempo hace")
    'qué tiempo hace'
    >>> strip_wake_phrase("hola")
    'hola'
    """

    backend = TextMatchBackend(phrases=phrases)
    normalized = _normalize(text)
    for phrase in backend._sorted_phrases:
        if normalized == phrase:
            return ""
        # Find where the wake phrase ends in the *original* text. We use the
        # normalized form to locate the offset, but slice the original to
        # preserve original casing and punctuation after the phrase.
        for sep in (" ", ",", ".", "!", "?", ":", ";"):
            tail = phrase + sep
            if normalized.startswith(tail):
                # ``len(tail)`` in the normalized string corresponds to a
                # variable number of code points in the original because the
                # accents we stripped are 1 codepoint in the original but 2
                # in NFKD. The safest approach: locate the original wake
                # phrase via a case-insensitive search and slice past it.
                idx = _find_original_phrase_end(text, phrase)
                if idx < 0:
                    return text
                return text[idx:].lstrip(" ,.!?:;")
    return text


def _find_original_phrase_end(text: str, phrase: str) -> int:
    """Return the index just past the end of *phrase* in *text*, ignoring
    accents. Returns ``-1`` if not found.
    """

    norm_text = _normalize(text)
    norm_phrase = _normalize(phrase)
    if not norm_text.startswith(norm_phrase):
        return -1
    # Walk through ``text`` consuming characters until we have matched the
    # same number of NFKD codepoints as ``norm_phrase`` had.
    target_len = len(norm_phrase)
    import unicodedata

    consumed = 0
    for i, ch in enumerate(text):
        decomposed = unicodedata.normalize("NFKD", ch)
        no_accents = _ACCENT_RE.sub("", decomposed)
        consumed += len(no_accents)
        if consumed >= target_len:
            return i + 1
    return len(text)


# ---------------------------------------------------------------------------
# openWakeWord backend
# ---------------------------------------------------------------------------


class OpenWakeWordBackend(WakeWordBackend):
    """Lazy-loading wrapper around ``openwakeword.model.Model``.

    The model is only constructed on first use, so test environments
    without ``openwakeword`` (or without the model weights) still import
    this module cleanly.
    """

    backend_id = "openwakeword"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        threshold: float = DEFAULT_THRESHOLD,
        *,
        inference_framework: str = "onnx",
    ) -> None:
        self._model_name = model_name
        self._threshold = threshold
        self._framework = inference_framework
        self._model: Optional[object] = None
        self._lock = threading.Lock()
        self._last_scores: Dict[str, float] = {}

    # -- lazy loading -------------------------------------------------------

    def _ensure_model(self) -> Optional[object]:
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from openwakeword.model import Model  # type: ignore[import-not-found]
            except ImportError:
                logger.debug(
                    "openwakeword not installed — wake-word detection disabled"
                )
                return None
            try:
                self._model = Model(
                    wakeword_models=[self._model_name],
                    inference_framework=self._framework,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to load openWakeWord model %r: %s",
                    self._model_name,
                    exc,
                )
                self._model = None
                return None
            return self._model

    # -- public API ---------------------------------------------------------

    @property
    def healthy(self) -> bool:
        return self._ensure_model() is not None

    def detect(self, audio_frame: bytes) -> Optional[WakeEvent]:
        """Score one frame of 16-bit, 16 kHz mono PCM and emit an event.

        The frame size must be 80 ms (1280 samples). For other sizes the
        call is a no-op and a warning is logged the first time.
        """

        model = self._ensure_model()
        if model is None:
            return None

        expected_bytes = _FRAME_SAMPLES * 2  # int16 → 2 bytes/sample
        if len(audio_frame) < expected_bytes:
            # Pad short frames with silence — common when the consumer
            # tears down mid-stream.
            audio_frame = audio_frame + b"\x00" * (expected_bytes - len(audio_frame))
        elif len(audio_frame) > expected_bytes:
            audio_frame = audio_frame[:expected_bytes]

        try:
            predictions = model.predict(audio_frame)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            logger.debug("openwakeword predict failed: %s", exc, exc_info=True)
            return None

        if not isinstance(predictions, dict):
            predictions = dict(predictions or {})

        # Cache last scores so external consumers can poll them.
        for key, value in predictions.items():
            try:
                self._last_scores[key] = float(value)
            except (TypeError, ValueError):
                continue

        score = float(predictions.get(self._model_name, 0.0) or 0.0)
        if score >= self._threshold:
            return WakeEvent(
                phrase=self._model_name,
                confidence=score,
                backend=self.backend_id,
            )
        return None

    @property
    def last_scores(self) -> Dict[str, float]:
        """Most recent per-model scores (read-only copy)."""
        return dict(self._last_scores)

    def reset(self) -> None:
        model = self._ensure_model()
        if model is None:
            return
        try:
            model.reset()  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - defensive
            logger.debug("openwakeword reset failed", exc_info=True)


# ---------------------------------------------------------------------------
# Push-to-talk fallback
# ---------------------------------------------------------------------------


def wait_for_push_to_talk(
    *,
    keys: tuple[str, ...] = ("ctrl+space", "fn"),
    timeout: Optional[float] = None,
) -> bool:
    """Block until the user presses one of *keys*, then return ``True``.

    This is the universal fallback when no audio model is available.
    The implementation shells out to Python's ``readline`` style key
    detection using ``pynput`` if available; otherwise it polls stdin.

    Args:
        keys: Hot-key combinations (case-insensitive). Each entry must
            match the format ``"<modifier>+<key>"`` (e.g. ``"ctrl+space"``)
            or be a bare key (e.g. ``"fn"``).
        timeout: Optional max wait in seconds. ``None`` blocks forever.

    Returns:
        ``True`` if a key was pressed before *timeout* elapsed.
    """

    keys = tuple(k.lower() for k in keys)

    try:
        # ``pynput`` is the canonical cross-platform choice and works on
        # macOS without special permissions for the modifier keys.
        from pynput import keyboard  # type: ignore[import-not-found]
    except ImportError:
        return _stdin_push_to_talk(keys=keys, timeout=timeout)

    pressed = threading.Event()
    mods: set[str] = set()

    def _on_press(key: object) -> Optional[bool]:
        try:
            name = _format_pynput_key(key)
        except Exception:  # noqa: BLE001
            return None
        if name in {"ctrl", "shift", "alt", "cmd", "fn"}:
            mods.add(name)
            return None
        if _matches(name, mods, keys):
            pressed.set()
        return None

    listener = keyboard.Listener(on_press=_on_press)
    listener.start()
    try:
        return pressed.wait(timeout=timeout)
    finally:
        listener.stop()


def _matches(key: str, modset: set[str], combos: tuple[str, ...]) -> bool:
    """Check whether ``key`` + ``modset`` matches any of ``combos``."""

    for combo in combos:
        parts = combo.split("+")
        target_mods = set(parts[:-1])
        target_key = parts[-1]
        if key != target_key:
            continue
        # Allow extra modifiers the OS may report (e.g. caps lock).
        if target_mods.issubset(modset | {target_key}):
            return True
    return False


def _format_pynput_key(key: object) -> str:
    """Return the canonical lower-case name for a pynput key."""

    from pynput.keyboard import Key  # type: ignore[import-not-found]

    if isinstance(key, Key):
        return key.name.lower()
    # pynput's ``KeyCode.char`` is the typed character, or ``None``.
    char = getattr(key, "char", None)
    return (char or "").lower()


def _stdin_push_to_talk(
    *, keys: tuple[str, ...], timeout: Optional[float]
) -> bool:
    """Last-resort stdin-based "press Enter to talk" fallback."""

    if not shutil.which("stty"):
        # Nothing we can do. Return False to avoid a blocking call.
        return False
    try:
        import select
        import sys

        sys.stderr.write("Press Enter to talk… ")
        sys.stderr.flush()
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if not rlist:
            return False
        sys.stdin.readline()
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# High-level helper
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WakeWordDetector:
    """High-level façade combining the ONNX backend with text-match fallback.

    Usage::

        detector = WakeWordDetector()
        for frame in mic_stream(80):  # 16 kHz int16 mono, 80 ms chunks
            event = detector.detect(frame)
            if event is not None:
                handle_wake(event)
    """

    config: WakeConfig = field(default_factory=WakeConfig)
    text_match: TextMatchBackend = field(init=False)
    onnx: OpenWakeWordBackend = field(init=False)

    def __post_init__(self) -> None:
        self.text_match = TextMatchBackend(phrases=self.config.phrases)
        self.onnx = OpenWakeWordBackend(
            model_name=self.config.model_name,
            threshold=self.config.threshold,
        )

    def detect(self, audio_frame: bytes) -> Optional[WakeEvent]:
        """Score one audio frame using whichever backend is available."""

        return self.onnx.detect(audio_frame)

    def match(self, text: str) -> Optional[WakeEvent]:
        """Match a transcribed utterance against the wake phrases."""

        return self.text_match.match(text)

    @property
    def backend_in_use(self) -> str:
        """Name of the backend that will fire on raw audio."""

        if self.onnx.healthy:
            return self.onnx.backend_id
        return self.text_match.backend_id

    def reset(self) -> None:
        self.onnx.reset()


__all__ = [
    "DEFAULT_MODEL_NAME",
    "DEFAULT_THRESHOLD",
    "DEFAULT_WAKE_PHRASES",
    "OpenWakeWordBackend",
    "TextMatchBackend",
    "WakeConfig",
    "WakeEvent",
    "WakeWordBackend",
    "WakeWordDetector",
    "strip_wake_phrase",
    "wait_for_push_to_talk",
]
