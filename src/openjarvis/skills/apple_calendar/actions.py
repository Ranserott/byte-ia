"""Apple Calendar read-only access via AppleScript.

The Calendar app exposes a rich AppleScript dictionary, including
``every event of every calendar whose start date ≥ ...``. We use that to
list today's and tomorrow's events for the user on demand.

All access is read-only: this skill never creates, modifies, or deletes
events. Future enhancements (create, delete, RSVP) would need explicit
user consent and a write-capable manifest flag.

The module is defensive on three axes:

1. ``osascript`` may not exist (non-macOS hosts).
2. The Calendar app may not be running — AppleScript auto-launches it,
   but the very first call can take seconds.
3. The user may have no calendars or no events — return a friendly
   "no events" string instead of an empty list.
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict

logger = logging.getLogger(__name__)

_OSASCRIPT_TIMEOUT = 15.0  # Calendar cold-start can be slow


def _osascript(script: str, *, timeout: float = _OSASCRIPT_TIMEOUT) -> str:
    """Execute an AppleScript snippet, swallowing errors as strings."""
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
        return "Error: Calendar tardó demasiado en responder."
    except FileNotFoundError:
        return "Error: osascript no disponible."
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.debug("Calendar AppleScript failed: %s", stderr)
        return f"Error leyendo Calendar: {stderr or 'desconocido'}"
    return (result.stdout or "").strip()


def _day_window(offset_days: int) -> str:
    """Build an AppleScript snippet for ``start_date``/``end_date``.

    ``offset_days`` is 0 for today, 1 for tomorrow, etc. We always work in
    the user's local timezone (the Calendar app does the same).
    """
    # Compute in Python (local TZ) and embed as ISO-ish strings so
    # AppleScript can parse them unambiguously.
    now = datetime.now().replace(microsecond=0)
    start = (now - timedelta(hours=now.hour, minutes=now.minute, seconds=now.second)
             + timedelta(days=offset_days))
    end = start + timedelta(days=1)
    # AppleScript ``date`` parses ISO-ish strings reliably when given a
    # full YYYY-MM-DD HH:MM:SS form.
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f'set startDate to date "{start_str}"\n'
        f'set endDate to date "{end_str}"\n'
    )


_LIST_EVENTS_TEMPLATE = """
tell application "Calendar"
    set theEvents to (every event of every calendar) whose start date ≥ startDate and start date ≤ endDate
    set out to ""
    repeat with anEvent in theEvents
        set eventName to summary of anEvent
        set eventStart to start date of anEvent
        set eventLoc to ""
        try
            set eventLoc to location of anEvent
        end try
        set out to out & eventName
        if eventLoc is not "" then
            set out to out & " (" & eventLoc & ")"
        end if
        set out to out & " — " & (time string of eventStart) & linefeed
    end repeat
    if out is "" then
        return "__EMPTY__"
    else
        return out
    end if
end tell
"""


def eventos_hoy() -> str:
    """Return a short, line-separated list of today's events."""
    window = _day_window(0)
    script = window + _LIST_EVENTS_TEMPLATE
    raw = _osascript(script)
    return _format(raw, fallback="Sin eventos hoy")


def eventos_manana() -> str:
    """Return a short, line-separated list of tomorrow's events."""
    window = _day_window(1)
    script = window + _LIST_EVENTS_TEMPLATE
    raw = _osascript(script)
    return _format(raw, fallback="Sin eventos mañana")


def _format(raw: str, *, fallback: str) -> str:
    """Format raw AppleScript output for the user."""
    if not raw:
        return fallback
    if raw == "__EMPTY__":
        return fallback
    if raw.startswith("Error"):
        return raw
    # Trim trailing newline for cleanliness.
    return raw.rstrip("\n")


def eventos_esta_semana() -> str:
    """Return a short list of events for the next 7 days (summary)."""
    window = _day_window(0)
    extra = (
        f'set endDate to date "{((datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d 23:59:59"))}"\n'
    )
    raw = _osascript(window + extra + _LIST_EVENTS_TEMPLATE)
    return _format(raw, fallback="Sin eventos esta semana")


# -- router -------------------------------------------------------------------


def run_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a single ``{action, ...}`` payload."""
    action = str(payload.get("action", "")).strip().lower()
    try:
        if action in ("eventos_hoy", "today"):
            return {"status": "ok", "message": eventos_hoy()}
        if action in ("eventos_manana", "tomorrow"):
            return {"status": "ok", "message": eventos_manana()}
        if action in ("eventos_semana", "week"):
            return {"status": "ok", "message": eventos_esta_semana()}
        return {"status": "error", "message": f"Acción desconocida: {action}"}
    except Exception as exc:  # noqa: BLE001
        logger.debug("Calendar action %s failed", action, exc_info=True)
        return {"status": "error", "message": f"Error: {exc}"}


ACTIONS: Dict[str, Dict[str, Any]] = {
    "eventos_hoy": {
        "fn": eventos_hoy,
        "description": "Lista los eventos del calendario de hoy",
        "examples": ["qué tengo hoy", "eventos de hoy", "agenda de hoy"],
    },
    "eventos_manana": {
        "fn": eventos_manana,
        "description": "Lista los eventos del calendario de mañana",
        "examples": ["qué tengo mañana", "reuniones de mañana"],
    },
    "eventos_esta_semana": {
        "fn": eventos_esta_semana,
        "description": "Lista los próximos 7 días",
        "examples": ["qué tengo esta semana", "agenda semanal"],
    },
}

__all__ = [
    "ACTIONS",
    "eventos_esta_semana",
    "eventos_hoy",
    "eventos_manana",
    "run_action",
]
