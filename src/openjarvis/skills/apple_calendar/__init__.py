"""Apple Calendar skill actions.

Read-only access to the user's macOS Calendar via AppleScript. Pair with
the ``apple_calendar.toml`` manifest in ``openjarvis/skills/data``.
"""

from __future__ import annotations

from openjarvis.skills.apple_calendar.actions import (
    ACTIONS,
    eventos_esta_semana,
    eventos_hoy,
    eventos_manana,
    run_action,
)

SKILL = {
    "name": "apple-calendar",
    "version": "1.0.0",
    "platform": ["macos"],
    "actions": ACTIONS,
    "run_action": run_action,
}

__all__ = [
    "ACTIONS",
    "SKILL",
    "eventos_esta_semana",
    "eventos_hoy",
    "eventos_manana",
    "run_action",
]
