"""Speech subsystem — speech-to-text and text-to-speech backends."""

import importlib

# Optional STT backends — each registers itself via @SpeechRegistry.register()
for _mod in ("faster_whisper", "openai_whisper", "deepgram"):
    try:
        importlib.import_module(f".{_mod}", __name__)
    except ImportError:
        pass

# Optional TTS backends — each registers itself via @TTSRegistry.register()
for _mod in ("cartesia_tts", "kokoro_tts", "openai_tts", "macos_say_tts"):
    try:
        importlib.import_module(f".{_mod}", __name__)
    except ImportError:
        pass

# Language helpers are pure Python and always importable.
from openjarvis.speech.language import (  # noqa: E402,F401
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    LanguageDetection,
    default_voice_for,
    detect_language_from_text,
    kokoro_voice_prefix,
    language_name,
    macos_voices_for,
    resolve_stt_language,
)
