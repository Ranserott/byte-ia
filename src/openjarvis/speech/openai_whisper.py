"""OpenAI Whisper API speech-to-text backend (cloud)."""

from __future__ import annotations

import io
import os
from typing import List, Optional

from openjarvis.core.registry import SpeechRegistry
from openjarvis.speech._stubs import SpeechBackend, TranscriptionResult
from openjarvis.speech.language import (
    DEFAULT_LANGUAGE,
    detect_language_from_text,
)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment, misc]


@SpeechRegistry.register("openai")
class OpenAIWhisperBackend(SpeechBackend):
    """Cloud speech-to-text using OpenAI Whisper API."""

    backend_id = "openai"

    def __init__(self, api_key: Optional[str] = None, default_language: str = DEFAULT_LANGUAGE) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._default_language = default_language
        self._client: Optional[OpenAI] = None
        if self._api_key and OpenAI is not None:
            self._client = OpenAI(api_key=self._api_key)

    def transcribe(
        self,
        audio: bytes,
        *,
        format: str = "wav",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using OpenAI's Whisper API."""
        if self._client is None:
            raise RuntimeError("OpenAI client not initialized (missing API key?)")

        ext = format if not format.startswith(".") else format[1:]
        audio_file = io.BytesIO(audio)
        audio_file.name = f"audio.{ext}"

        kwargs: dict = {"model": "whisper-1", "file": audio_file}
        # If the caller passed a language we forward it directly. Otherwise
        # we let Whisper auto-detect and surface its detection via
        # ``response.language``. ``verbose_json`` is already requested
        # below so we always get a language back from the API.
        if language:
            kwargs["language"] = language
        kwargs["response_format"] = "verbose_json"

        response = self._client.audio.transcriptions.create(**kwargs)

        text = getattr(response, "text", str(response))
        api_language = getattr(response, "language", None)
        # Defensive fallback: if the API omitted the language, run our
        # heuristic on the transcribed text so downstream TTS can pick
        # the right voice.
        if not api_language and text:
            api_language = detect_language_from_text(text).code

        return TranscriptionResult(
            text=text,
            language=api_language,
            confidence=None,
            duration_seconds=getattr(response, "duration", 0.0),
            segments=[],
        )

    def health(self) -> bool:
        return self._client is not None and bool(self._api_key)

    def supported_formats(self) -> List[str]:
        return ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
