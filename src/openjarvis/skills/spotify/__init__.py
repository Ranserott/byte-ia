"""Spotify skill actions.

Voice/chat control of the Spotify desktop app via AppleScript. No OAuth or
API keys required — the Spotify app handles its own auth. Pair with the
``spotify.toml`` manifest in ``openjarvis/skills/data``.
"""

from __future__ import annotations

from openjarvis.skills.spotify.actions import (
    ACTIONS,
    next_track,
    pause,
    play,
    previous_track,
    resume,
    run_action,
    volume,
)

SKILL = {
    "name": "spotify",
    "version": "1.0.0",
    "platform": ["macos"],
    "actions": ACTIONS,
    "run_action": run_action,
}

__all__ = [
    "ACTIONS",
    "SKILL",
    "next_track",
    "pause",
    "play",
    "previous_track",
    "resume",
    "run_action",
    "volume",
]
