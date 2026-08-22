"""Tests for the Spotify skill (AppleScript backend).

We never shell out to ``osascript`` during tests — the ``_osascript``
helper is patched so each action gets a deterministic stdout/stderr. That
also makes these tests runnable on Linux CI (where osascript is missing).
"""

from __future__ import annotations

import subprocess
from typing import Tuple

import pytest

from openjarvis.skills.spotify import actions as actions_mod


class FakeCompleted:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@pytest.fixture
def patch_osascript(monkeypatch):
    """Patch ``subprocess.run`` for osascript calls.

    Returns a function the test can call to set the next response.
    """
    state = {"next": FakeCompleted()}

    def _fake_run(cmd, *args, **kwargs):
        # Only intercept osascript calls; let anything else through.
        if cmd and cmd[0] == "osascript":
            return state["next"]
        return FakeCompleted(returncode=0)

    monkeypatch.setattr(actions_mod.subprocess, "run", _fake_run)

    def _set(stdout: str = "", stderr: str = "", returncode: int = 0):
        state["next"] = FakeCompleted(stdout=stdout, stderr=stderr, returncode=returncode)

    return _set


def test_pause_sends_pause_command(patch_osascript) -> None:
    patch_osascript(stdout="")
    msg = actions_mod.pause()
    assert msg == "Reproducción pausada"


def test_resume_sends_play_command(patch_osascript) -> None:
    patch_osascript(stdout="")
    msg = actions_mod.resume()
    assert msg == "Reproduciendo"


def test_next_track(patch_osascript) -> None:
    patch_osascript(stdout="")
    msg = actions_mod.next_track()
    assert msg == "Siguiente canción"


def test_previous_track(patch_osascript) -> None:
    patch_osascript(stdout="")
    msg = actions_mod.previous_track()
    assert msg == "Canción anterior"


def test_volume_clamps_high(patch_osascript) -> None:
    patch_osascript(stdout="")
    msg = actions_mod.volume(999)
    # 999 must be clamped to 100.
    assert msg == "Volumen al 100%"


def test_volume_clamps_low(patch_osascript) -> None:
    patch_osascript(stdout="")
    msg = actions_mod.volume(-5)
    assert msg == "Volumen al 0%"


def test_volume_invalid_string(patch_osascript) -> None:
    patch_osascript(stdout="")
    msg = actions_mod.volume("loud")  # type: ignore[arg-type]
    assert msg.startswith("Volumen inválido")


def test_play_success(patch_osascript) -> None:
    patch_osascript(stdout="")
    msg = actions_mod.play("Bad Bunny")
    assert "Reproduciendo Bad Bunny" in msg


def test_play_falls_back_to_search_on_error(patch_osascript) -> None:
    # First call (play track) errors with "Can't get track" → falls back to search.
    # Second call returns the success string.
    responses = iter([
        FakeCompleted(stdout="", stderr="Can't get track \"X\"", returncode=1),
        FakeCompleted(stdout="Reproduciendo X", returncode=0),
    ])

    def fake_run(cmd, *args, **kwargs):
        return next(responses)

    actions_mod.subprocess.run = fake_run  # type: ignore[assignment]
    msg = actions_mod.play("X")
    assert msg == "Reproduciendo X"


def test_play_returns_friendly_error_on_missing_app(monkeypatch) -> None:
    # Pretend we're on a Linux box without Spotify installed.
    monkeypatch.setattr(actions_mod.os.path, "exists", lambda p: False)
    msg = actions_mod.play("anything")
    assert "Spotify no está instalado" in msg


def test_osascript_timeout_returns_error(monkeypatch) -> None:
    def fake_run(cmd, *args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)

    monkeypatch.setattr(actions_mod.subprocess, "run", fake_run)
    # Need Spotify "installed" so we get past the availability check.
    monkeypatch.setattr(actions_mod.os.path, "exists", lambda p: True)
    msg = actions_mod.pause()
    assert "tardó demasiado" in msg


def test_osascript_missing_returns_error(monkeypatch) -> None:
    def fake_run(cmd, *args, **kwargs):
        raise FileNotFoundError("osascript missing")

    monkeypatch.setattr(actions_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(actions_mod.os.path, "exists", lambda p: True)
    msg = actions_mod.pause()
    assert "sólo macOS" in msg or "osascript no disponible" in msg


# -- router -------------------------------------------------------------------


def test_run_action_dispatches_pause(patch_osascript) -> None:
    patch_osascript(stdout="")
    result = actions_mod.run_action({"action": "pause"})
    assert result == {"status": "ok", "message": "Reproducción pausada"}


def test_run_action_dispatches_play(patch_osascript) -> None:
    patch_osascript(stdout="")
    result = actions_mod.run_action({"action": "play", "query": "Drake"})
    assert result["status"] == "ok"
    assert "Drake" in result["message"]


def test_run_action_play_requires_query(patch_osascript) -> None:
    patch_osascript(stdout="")
    result = actions_mod.run_action({"action": "play"})
    assert result["status"] == "error"


def test_run_action_unknown(patch_osascript) -> None:
    result = actions_mod.run_action({"action": "launch_missiles"})
    assert result["status"] == "error"
    assert "Acción desconocida" in result["message"]


def test_run_action_swallows_exceptions(monkeypatch) -> None:
    def boom(*a, **kw):
        raise RuntimeError("osascript exploded")

    monkeypatch.setattr(actions_mod, "pause", boom)
    result = actions_mod.run_action({"action": "pause"})
    assert result["status"] == "error"
    assert "Error" in result["message"]


def test_escape_quotes_in_query(patch_osascript) -> None:
    patch_osascript(stdout="")
    # Should not raise even with quotes/backslashes in the query.
    msg = actions_mod.play('Artist "with" \\quotes')
    assert "Reproduciendo" in msg


def test_actions_registry_has_expected_keys() -> None:
    for key in ("play", "pause", "resume", "next_track", "previous_track", "volume"):
        assert key in actions_mod.ACTIONS
        assert callable(actions_mod.ACTIONS[key]["fn"])
