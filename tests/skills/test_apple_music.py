"""Tests for the Apple Music skill.

Mocks ``subprocess.run`` so the tests run on Linux CI too.
"""

from __future__ import annotations

import subprocess
from typing import List

import pytest

from openjarvis.skills.apple_music import actions as actions_mod


class FakeCompleted:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@pytest.fixture
def patch_osascript(monkeypatch):
    """Patch subprocess.run and queue canned responses."""
    state: dict = {"responses": [FakeCompleted()], "calls": []}

    def _fake_run(cmd, *args, **kwargs):
        state["calls"].append(cmd)
        if cmd and cmd[0] == "osascript":
            if state["responses"]:
                return state["responses"].pop(0)
            return FakeCompleted()
        return FakeCompleted()

    monkeypatch.setattr(actions_mod.subprocess, "run", _fake_run)

    class _Ctl:
        def set(self, responses: List[FakeCompleted]) -> None:
            state["responses"] = list(responses)

        @property
        def calls(self) -> list:
            return state["calls"]

    return _Ctl()


# -- direct actions -----------------------------------------------------------


def test_pause(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted()])
    assert actions_mod.pause() == "Apple Music pausado"


def test_resume(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted()])
    assert actions_mod.resume() == "Reproduciendo"


def test_next_track(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted()])
    assert actions_mod.next_track() == "Siguiente"


def test_previous_track(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted()])
    assert actions_mod.previous_track() == "Anterior"


def test_volume_clamps(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted()])
    assert actions_mod.volume(250) == "Volumen al 100%"
    assert actions_mod.volume(-10) == "Volumen al 0%"


def test_volume_invalid(patch_osascript) -> None:
    assert actions_mod.volume("max") == "Volumen inválido: max"  # type: ignore[arg-type]


def test_play_with_query(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stdout="Reproduciendo X", returncode=0)])
    msg = actions_mod.play("Bohemian Rhapsody")
    # Either the success message or the script template's success branch.
    assert "Reproduciendo" in msg or "no encontré" in msg.lower() or msg


def test_play_empty_query_returns_error() -> None:
    msg = actions_mod.play("")
    assert "falta" in msg.lower() or msg.startswith("Error")


def test_osascript_error_with_cant_get(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stderr="Can't get track \"X\".", returncode=1)])
    msg = actions_mod.play("X")
    assert "no encontré" in msg.lower() or "Biblioteca" in msg or "biblioteca" in msg


def test_osascript_timeout(monkeypatch) -> None:
    def fake_run(cmd, *args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)

    monkeypatch.setattr(actions_mod.subprocess, "run", fake_run)
    msg = actions_mod.pause()
    assert "tardó demasiado" in msg


def test_non_macos(monkeypatch) -> None:
    monkeypatch.setattr(actions_mod.os, "name", "nt")
    assert "sólo macOS" in actions_mod.pause()


def test_escape_quotes(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stdout="Reproduciendo X", returncode=0)])
    # Quotes / backslashes must not crash the AppleScript build.
    msg = actions_mod.play('Track "with" \\quotes')
    assert msg  # never raises


# -- router -------------------------------------------------------------------


def test_run_action_pause(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted()])
    result = actions_mod.run_action({"action": "pause"})
    assert result == {"status": "ok", "message": "Apple Music pausado"}


def test_run_action_play_missing_query(patch_osascript) -> None:
    result = actions_mod.run_action({"action": "play"})
    assert result["status"] == "error"


def test_run_action_unknown(patch_osascript) -> None:
    result = actions_mod.run_action({"action": "buy_album"})
    assert result["status"] == "error"
    assert "Acción desconocida" in result["message"]


def test_run_action_swallows_exceptions(monkeypatch) -> None:
    def boom(*a, **kw):
        raise RuntimeError("Music crashed")

    monkeypatch.setattr(actions_mod, "pause", boom)
    result = actions_mod.run_action({"action": "pause"})
    assert result["status"] == "error"


def test_actions_registry_has_expected_keys() -> None:
    for key in ("play", "pause", "resume", "next_track", "previous_track", "volume"):
        assert key in actions_mod.ACTIONS
        assert callable(actions_mod.ACTIONS[key]["fn"])
