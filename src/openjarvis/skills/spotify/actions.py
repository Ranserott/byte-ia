"""Spotify control via AppleScript (no OAuth).

The Spotify desktop app ships with an AppleScript dictionary that exposes
``play``, ``pause``, ``next track``, ``sound volume`` and search via the
``search`` command. We use it as the default backend because it needs zero
configuration — the user just needs the Spotify app installed and running.

For users who prefer the official Spotify Web API (e.g. headless servers),
:mod:`spotipy` is the recommended client. It is listed as an *optional*
dependency in the skill manifest and is intentionally not imported at
module load — install it only if you swap the backend.

Every action is defensive: a Spotify-down or permissions-missing scenario
must return an informative string instead of raising, so the voice agent
can report back to the user rather than crash.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Hard caps so a malicious voice prompt can't crank the system volume to
# 200% or mute everything silently.
_VOLUME_MIN = 0
_VOLUME_MAX = 100
_OSASCRIPT_TIMEOUT = 5.0


def _osascript(script: str, *, timeout: float = _OSASCRIPT_TIMEOUT) -> str:
    """Execute an AppleScript snippet against Spotify.

    Returns the script's stdout on success, or a ``"Error: …"`` message on
    failure. Never raises — call sites can pass the result straight to the
    LLM router.
    """
    if not _spotify_available():
        return "Spotify no está instalado. Abrilo y volvé a intentar."
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Error: Spotify tardó demasiado en responder."
    except FileNotFoundError:
        # ``osascript`` itself missing — we are not on macOS.
        return "Error: osascript no disponible (sólo macOS)."

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.debug("osascript failed: %s", stderr)
        # AppleScript error 1 from Spotify usually means no track was
        # found. Surface that as a friendly message.
        if "Can't get track" in stderr or "not found" in stderr.lower():
            return "No encontré ese track en Spotify."
        return f"Error de Spotify: {stderr or 'desconocido'}"
    return (result.stdout or "").strip()


def _spotify_available() -> bool:
    """Best-effort check that the Spotify app is installed.

    We probe the macOS bundle identifier rather than calling Spotify —
    avoids spawning a GUI process just to ask "are you there?".
    """
    if os.name != "posix" or not os.path.exists("/Applications/Spotify.app"):
        return False
    return True


def _escape(value: str) -> str:
    """Escape a string for safe inclusion in an AppleScript literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


# -- public actions ----------------------------------------------------------


def play(query: str) -> str:
    """Play a song or artist by ``query``.

    Tries ``play track "<query>"`` first (works if the song is already in
    the user's library). If Spotify raises an error, falls back to a
    ``search`` command and plays the first result.
    """
    safe = _escape(query)
    script = (
        'tell application "Spotify"\n'
        "    activate\n"
        f'    play track "{safe}"\n'
        "end tell"
    )
    result = _osascript(script)
    if result.startswith("No encontré") or result.startswith("Error"):
        # Fall back to search.
        search_script = (
            'tell application "Spotify"\n'
            "    activate\n"
            f'    set results to search for "{safe}"\n'
            "    if (count of results) > 0 then\n"
            "        play item 1 of results\n"
            f'        return "Reproduciendo {safe}"\n'
            "    else\n"
            f'        return "No encontré {safe}"\n'
            "    end if\n"
            "end tell"
        )
        return _osascript(search_script)
    return f"Reproduciendo {query}"


def pause() -> str:
    """Pause Spotify playback."""
    _osascript('tell application "Spotify" to pause')
    return "Reproducción pausada"


def resume() -> str:
    """Resume Spotify playback after a pause."""
    _osascript('tell application "Spotify" to play')
    return "Reproduciendo"


def next_track() -> str:
    """Skip to the next track."""
    _osascript('tell application "Spotify" to next track')
    return "Siguiente canción"


def previous_track() -> str:
    """Return to the previous track."""
    _osascript('tell application "Spotify" to previous track')
    return "Canción anterior"


def volume(percent: int) -> str:
    """Set Spotify volume (0-100). Clamps out-of-range inputs."""
    try:
        pct = int(percent)
    except (TypeError, ValueError):
        return f"Volumen inválido: {percent}"
    pct = max(_VOLUME_MIN, min(_VOLUME_MAX, pct))
    _osascript(f'set sound volume to {pct}')
    return f"Volumen al {pct}%"


# -- router -------------------------------------------------------------------


def run_action(payload: Dict[str, Any]) -> Dict[str, str]:
    """Dispatch a single action from a ``{action, ...}`` payload.

    Used by the skill manifest's ``shell_exec`` step. Returns a dict so
    the LLM can branch on ``status`` without parsing strings.
    """
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
    except Exception as exc:  # noqa: BLE001 — never crash the router
        logger.debug("Spotify action %s failed", action, exc_info=True)
        return {"status": "error", "message": f"Error: {exc}"}


# Map for the LLM router. Keys are stable — external callers depend on them.
ACTIONS: Dict[str, Dict[str, Any]] = {
    "play": {
        "fn": play,
        "description": "Reproduce un artista o canción en Spotify",
        "examples": ["reproduce Bad Bunny", "pon algo de jazz"],
        "args": ["query: string"],
    },
    "pause": {
        "fn": pause,
        "description": "Pausa la reproducción de Spotify",
        "examples": ["pausa", "pausá la música"],
    },
    "resume": {
        "fn": resume,
        "description": "Reanuda la reproducción de Spotify",
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
        "description": "Cambia el volumen (0-100)",
        "examples": ["volumen al 50", "bajá el volumen a 30"],
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
