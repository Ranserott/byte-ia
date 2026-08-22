"""Tests for the Apple Calendar skill.

Mocks ``subprocess.run`` so we never spawn ``osascript`` in CI. Linux CI
also works because the AppleScript paths are only built when the helper
runs — but we still patch the subprocess layer for determinism.
"""

from __future__ import annotations

import subprocess
from typing import List

import pytest

from openjarvis.skills.apple_calendar import actions as actions_mod


class FakeCompleted:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@pytest.fixture
def patch_osascript(monkeypatch):
    """Patch subprocess.run and queue one or more canned responses."""
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

        def calls(self) -> list:
            return state["calls"]

    return _Ctl()


def test_eventos_hoy_returns_friendly_when_empty(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stdout="__EMPTY__")])
    msg = actions_mod.eventos_hoy()
    assert msg == "Sin eventos hoy"


def test_eventos_hoy_formats_events(patch_osascript) -> None:
    patch_osascript.set(
        [FakeCompleted(stdout="Reunión (Sala A) — 10:00:00 AM\nLunch — 1:00:00 PM")]
    )
    msg = actions_mod.eventos_hoy()
    assert "Reunión" in msg
    assert "Sala A" in msg
    assert "Lunch" in msg


def test_eventos_manana_uses_tomorrow_window(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stdout="__EMPTY__")])
    msg = actions_mod.eventos_manana()
    assert msg == "Sin eventos mañana"


def test_eventos_esta_semana(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stdout="Sprint review — 3:00:00 PM")])
    msg = actions_mod.eventos_esta_semana()
    assert "Sprint review" in msg


def test_osascript_error_surfaces(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stderr="Calendar got an error", returncode=1)])
    msg = actions_mod.eventos_hoy()
    assert "Error" in msg
    assert "Calendar" in msg


def test_timeout_returns_friendly_message(monkeypatch) -> None:
    def fake_run(cmd, *args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=15)

    monkeypatch.setattr(actions_mod.subprocess, "run", fake_run)
    msg = actions_mod.eventos_hoy()
    assert "tardó demasiado" in msg


def test_non_macos_returns_message(monkeypatch) -> None:
    monkeypatch.setattr(actions_mod.os, "name", "nt")
    msg = actions_mod.eventos_hoy()
    assert "sólo está disponible en macOS" in msg


# -- router -------------------------------------------------------------------


def test_run_action_eventos_hoy(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stdout="__EMPTY__")])
    result = actions_mod.run_action({"action": "eventos_hoy"})
    assert result["status"] == "ok"
    assert "Sin eventos" in result["message"]


def test_run_action_eventos_manana(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stdout="__EMPTY__")])
    result = actions_mod.run_action({"action": "eventos_manana"})
    assert result["status"] == "ok"


def test_run_action_eventos_semana(patch_osascript) -> None:
    patch_osascript.set([FakeCompleted(stdout="Sprint planning — 9:00:00 AM")])
    result = actions_mod.run_action({"action": "eventos_semana"})
    assert result["status"] == "ok"
    assert "Sprint" in result["message"]


def test_run_action_unknown(patch_osascript) -> None:
    result = actions_mod.run_action({"action": "delete_everything"})
    assert result["status"] == "error"


def test_run_action_swallows_exceptions(monkeypatch) -> None:
    def boom(*a, **kw):
        raise RuntimeError("Calendar crashed")

    monkeypatch.setattr(actions_mod, "eventos_hoy", boom)
    result = actions_mod.run_action({"action": "eventos_hoy"})
    assert result["status"] == "error"


def test_actions_registry_has_expected_keys() -> None:
    for key in ("eventos_hoy", "eventos_manana", "eventos_esta_semana"):
        assert key in actions_mod.ACTIONS
        assert callable(actions_mod.ACTIONS[key]["fn"])


def test_day_window_offset_one_changes_date() -> None:
    """Sanity check: offset 1 must produce a different end-date than offset 0."""
    win0 = actions_mod._day_window(0)
    win1 = actions_mod._day_window(1)
    # Both contain `set endDate` — but the dates differ.
    assert "set endDate" in win0
    assert "set endDate" in win1
    assert win0 != win1
