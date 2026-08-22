"""Apple Music skill actions.

Voice/chat control of the macOS Music app via AppleScript. No API keys or
OAuth required. Pair with the ``apple_music.toml`` manifest in
``openjarvis/skills/data``.
"""

from __future__ import annotations

from openjarvis.skills.apple_music.actions import (
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
    "name": "apple-music",
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
