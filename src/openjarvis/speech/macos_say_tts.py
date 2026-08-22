"""macOS ``say`` command TTS backend.

Uses the native ``say`` CLI available on every macOS install. Supports
Spanish voices (``"Monica"``, ``"Juan"``, ``"Paulina"``) and any other
language the OS ships voices for. Writes audio to a temporary ``.aiff``
file (since ``say`` doesn't stream to stdout) and returns the bytes.

This backend is intentionally a thin wrapper around ``subprocess`` so it
has no third-party dependencies — it degrades gracefully to ``False`` on
``health()`` on non-macOS hosts and on systems where ``say`` is missing
(e.g. inside the CI sandbox).
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from openjarvis.core.registry import TTSRegistry
from openjarvis.speech.language import default_voice_for, macos_voices_for
from openjarvis.speech.tts import TTSBackend, TTSResult

logger = logging.getLogger(__name__)

# Default speed matches normal human speech rate. ``say`` accepts a
# number of words-per-minute; ~175 wpm is roughly 1.0×.
_DEFAULT_WPM = 175

# AIFF is the most portable format ``say`` writes (no extra encoders).
_AUDIO_FORMAT = "aiff"


@TTSRegistry.register("macos_say")
class MacOSSayTTSBackend(TTSBackend):
    """TTS backend that shells out to macOS ``say``.

    Args:
        default_voice: Optional voice override. If unset, the backend
            picks a sensible per-language voice (Monica for Spanish,
            Samantha for English, …) using :mod:`openjarvis.speech.language`.
        default_wpm: Words-per-minute; clamped to the range ``[80, 360]``
            which is what ``say`` accepts without distortion.
    """

    backend_id = "macos_say"

    def __init__(
        self,
        *,
        default_voice: str = "",
        default_wpm: int = _DEFAULT_WPM,
    ) -> None:
        self._default_voice = default_voice
        self._default_wpm = max(80, min(360, default_wpm))

    # ------------------------------------------------------------------
    # TTSBackend protocol
    # ------------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        *,
        voice_id: str = "",
        speed: float = 1.0,
        output_format: str = _AUDIO_FORMAT,
    ) -> TTSResult:
        """Speak *text* via macOS ``say`` and return the recorded audio."""
        if not self._is_macos():
            raise RuntimeError("macos_say backend is only available on macOS")

        if not text or not text.strip():
            raise ValueError("text must be a non-empty string")

        # ``say`` only writes to a file, so we route through a tempdir.
        suffix = f".{output_format}" if not output_format.startswith(".") else output_format
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)

        voice = voice_id or self._default_voice or self._pick_default_voice(text)
        wpm = max(80, min(360, int(self._default_wpm * speed)))

        cmd = ["say", "-v", voice, "-o", str(tmp_path), "--rate", str(wpm)]
        if voice.startswith("es_") or voice.lower() in {
            "monica", "juan", "paulina", "diego"
        }:
            # Some macOS voices benefit from explicit quality flags.
            cmd.extend(["-q", "127"])  # high quality AAC-encoded AIFF

        logger.debug("Running TTS command: %s", cmd)
        try:
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                check=False,
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                stderr = proc.stderr.decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"macOS 'say' failed (rc={proc.returncode}): {stderr.strip()}"
                )
            audio = tmp_path.read_bytes()
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass

        return TTSResult(
            audio=audio,
            format=output_format,
            duration_seconds=self._estimate_duration(text, wpm),
            voice_id=voice,
            sample_rate=22050,
            metadata={"backend": "macos_say", "wpm": wpm},
        )

    def available_voices(self) -> List[str]:
        """Return the list of macOS voices (filtered to supported languages)."""
        if not self._is_macos():
            return []
        try:
            out = subprocess.run(
                ["say", "-v", "?"],
                check=False,
                capture_output=True,
                timeout=5,
                text=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Could not enumerate macOS voices: %s", exc)
            return []

        voices: List[str] = []
        for line in out.stdout.splitlines():
            # Format: ``Name  lang  # Sample phrase``
            line = line.strip()
            if not line:
                continue
            name = line.split("  ", 1)[0].strip()
            if name:
                voices.append(name)
        return voices

    def health(self) -> bool:
        """Return True only on macOS hosts where ``say`` exists."""
        return self._is_macos() and shutil.which("say") is not None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_macos() -> bool:
        return platform.system() == "Darwin"

    def _pick_default_voice(self, text: str) -> str:
        """Pick a sensible default voice based on the input text."""
        from openjarvis.speech.language import detect_language_from_text

        detection = detect_language_from_text(text)
        code = detection.code if detection.confidence >= 0.35 else "es"
        voices = list(macos_voices_for(code))
        if voices:
            return voices[0]
        # Fall back to the system default ("Alex" on macOS).
        return default_voice_for(code, "macos_say") or "Alex"

    @staticmethod
    def _estimate_duration(text: str, wpm: int) -> float:
        """Rough audio duration estimate based on word count and rate."""
        words = max(1, len(text.split()))
        return round(words / max(1, wpm) * 60.0, 2)


__all__ = ["MacOSSayTTSBackend"]


def _ensure_registered() -> None:  # pragma: no cover - import hook
    """Ensure :class:`MacOSSayTTSBackend` is registered even if the
    ``openjarvis.speech`` package-level importer missed us."""
    from openjarvis.core.registry import TTSRegistry

    if not TTSRegistry.contains("macos_say"):
        TTSRegistry.register_value("macos_say", MacOSSayTTSBackend)


_ensure_registered()
