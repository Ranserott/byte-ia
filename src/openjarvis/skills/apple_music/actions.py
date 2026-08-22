"""Apple Music control via AppleScript (no configuration needed).

The Music app (formerly iTunes) ships with a powerful AppleScript API. We
use it to play tracks from the user's library, pause/resume playback, and
skip tracks. No API keys, no OAuth — the user just needs the Music app
and a populated library.

This skill is intentionally separate from :mod:`openjarvis.skills.spotify`
so the voice agent can disambiguate ``"reproduce X en Apple Music"`` from
``"reproduce X en Spotify"`` without guessing at user intent.

Like Spotify, all actions are defensive and return informative strings on
failure rather than raising.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any, Dict

logger = logging.getLogger(__name__)

_OSASCRIPT_TIMEOUT = 5.0
_VOLUME_MIN = 0
_VOLUME_MAX = 100


def _osascript(script: str, *, timeout: float = _OSASCRIPT_TIMEOUT) -> str:
    """Execute AppleScript against the Music app. Never raises."""
    if os.name != "posix":
        return "Error: AppleScript sólo está disponible en macOS."
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Error: Music tardó demasiado en responder."
    except FileNotFoundError:
        return "Error: osascript no disponible."
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.debug("Music AppleScript failed: %s", stderr)
        if "Can't get" in stderr or "not found" in stderr.lower():
            return "No encontré ese track en tu biblioteca."
        return f"Error de Music: {stderr or 'desconocido'}"
    return (result.stdout or "").strip()


def _escape(value: str) -> str:
    """Escape a string for inclusion in an AppleScript literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


# -- public actions ----------------------------------------------------------


def play(query: str) -> str:
    """Play a track whose name contains ``query`` from the user's library.

    Apple Music's AppleScript exposes ``library playlist 1`` (the master
    "Library" playlist) and a ``whose name contains`` filter, so we can
    search across the entire library without hitting the iTunes Store API.
    """
    if not query or not query.strip():
        return "Error: falta el nombre del track."
    safe = _escape(query)
    script = (
        'tell application "Music"\n'
        "    activate\n"
        f'    set found to (some track of library playlist 1 whose name contains "{safe}")\n'
        "    if found is not missing value then\n"
        "        play found\n"
        f'        return "Reproduciendo {query}"\n'
        "    else\n"
        f'        return "No encontré {query} en tu biblioteca"\n'
        "    end if\n"
        "end tell"
    )
    return _osascript(script)


def pause() -> str:
    """Pause playback."""
    _osascript('tell application "Music" to pause')
    return "Apple Music pausado"


def resume() -> str:
    """Resume playback."""
    _osascript('tell application "Music" to play')
    return "Reproduciendo"


def next_track() -> str:
    """Skip to the next track."""
    _osascript('tell application "Music" to next track')
    return "Siguiente"


def previous_track() -> str:
    """Return to the previous track."""
    _osascript('tell application "Music" to previous track')
    return "Anterior"


def volume(percent: int) -> str:
    """Set Music's volume (0-100)."""
    try:
        pct = int(percent)
    except (TypeError, ValueError):
        return f"Volumen inválido: {percent}"
    pct = max(_VOLUME_MIN, min(_VOLUME_MAX, pct))
    _osascript(f'set sound volume to {pct}')
    return f"Volumen al {pct}%"


# -- router -------------------------------------------------------------------


def run_action(payload: Dict[str, Any]) -> Dict[str, str]:
    """Dispatch a single ``{action, ...}`` payload."""
    action = str(payload.get("action", "")).strip().lower()
    try:
        if action == "play":
            query = str(payload.get("query", "")).strip()
            if not query:
                return {"status": "error", "message": "Falta el query para reproducir."}
            return {"status": "ok", "message": play(query)}
        if action == "pause":
            return {"status": "ok", "message": pause()}
        if action == "resume":
            return {"status": "ok", "message": resume()}
        if action in ("next", "next_track"):
            return {"status": "ok", "message": next_track()}
        if action in ("previous", "previous_track"):
            return {"status": "ok", "message": previous_track()}
        if action == "volume":
            return {"status": "ok", "message": volume(payload.get("percent", 50))}
        return {"status": "error", "message": f"Acción desconocida: {action}"}
    except Exception as exc:  # noqa: BLE001
        logger.debug("Apple Music action %s failed", action, exc_info=True)
        return {"status": "error", "message": f"Error: {exc}"}


ACTIONS: Dict[str, Dict[str, Any]] = {
    "play": {
        "fn": play,
        "description": "Reproduce un track de la biblioteca de Apple Music",
        "examples": ["reproduce X en Apple Music", "pon Y"],
        "args": ["query: string"],
    },
    "pause": {
        "fn": pause,
        "description": "Pausa Apple Music",
        "examples": ["pausá", "pausa Apple Music"],
    },
    "resume": {
        "fn": resume,
        "description": "Reanuda Apple Music",
        "examples": ["reanudá", "seguí"],
    },
    "next_track": {
        "fn": next_track,
        "description": "Salta a la siguiente canción",
        "examples": ["siguiente", "next"],
    },
    "previous_track": {
        "fn": previous_track,
        "description": "Vuelve a la canción anterior",
        "examples": ["anterior", "previous"],
    },
    "volume": {
        "fn": volume,
        "description": "Cambia el volumen de Music (0-100)",
        "examples": ["volumen al 50", "bajá el volumen"],
        "args": ["percent: int"],
    },
}


__all__ = [
    "ACTIONS",
    "next_track",
    "pause",
    "play",
    "previous_track",
    "resume",
    "run_action",
    "volume",
]
