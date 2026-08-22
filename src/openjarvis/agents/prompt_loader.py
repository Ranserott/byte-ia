"""Load system prompt and few-shot overrides from $OPENJARVIS_HOME.

LLM-guided spec search (M1) proposes edits that get written to disk by appliers.
This module lets agents pick those overrides up at runtime:

- System prompts: ``$OPENJARVIS_HOME/agents/{name}/system_prompt.md``
- Few-shot exemplars: ``$OPENJARVIS_HOME/agents/{name}/few_shot.json``

Override files are templates — they may contain ``{tool_descriptions}`` and
other format placeholders that the agent fills in via ``.format()``, exactly
like the hardcoded constants.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from openjarvis.core.paths import get_config_dir

logger = logging.getLogger(__name__)


def _openjarvis_home() -> Path:
    """Resolve the OpenJarvis root, honoring OPENJARVIS_HOME / XDG_DATA_HOME."""
    return get_config_dir()


def load_system_prompt_override(agent_name: str, language: str | None = None) -> str | None:
    """Return the override prompt for *agent_name*, or ``None``.

    Resolution order:

    1. ``$OPENJARVIS_HOME/agents/<agent_name>/system_prompt.<lang>.md``
       (e.g. ``system_prompt.es.md``) — language-specific override.
    2. ``$OPENJARVIS_HOME/agents/<agent_name>/system_prompt.md`` — default.
    3. ``None`` if neither exists.

    ``language`` defaults to the project's :data:`DEFAULT_LANGUAGE`
    (``"es"``) when omitted. ``OPENJARVIS_HOME`` defaults to
    ``~/.openjarvis`` when unset.
    """
    from openjarvis.speech.language import DEFAULT_LANGUAGE

    home = _openjarvis_home()
    agent_dir = home / "agents" / agent_name

    if language:
        lang_path = agent_dir / f"system_prompt.{language}.md"
        if lang_path.exists():
            try:
                content = lang_path.read_text(encoding="utf-8")
                logger.info(
                    "Loaded %s system prompt for %s from %s",
                    language,
                    agent_name,
                    lang_path,
                )
                return content
            except Exception:
                logger.warning(
                    "Failed to read language-specific system prompt at %s",
                    lang_path,
                    exc_info=True,
                )

    # Fall back to the default language if nothing was found for the
    # requested language (still preferring a per-language file).
    if language != DEFAULT_LANGUAGE:
        lang_path = agent_dir / f"system_prompt.{DEFAULT_LANGUAGE}.md"
        if lang_path.exists():
            try:
                content = lang_path.read_text(encoding="utf-8")
                logger.info(
                    "Loaded fallback %s system prompt for %s from %s",
                    DEFAULT_LANGUAGE,
                    agent_name,
                    lang_path,
                )
                return content
            except Exception:
                logger.warning(
                    "Failed to read fallback system prompt at %s",
                    lang_path,
                    exc_info=True,
                )

    prompt_path = agent_dir / "system_prompt.md"
    if not prompt_path.exists():
        return None
    try:
        content = prompt_path.read_text(encoding="utf-8")
        logger.info(
            "Loaded system prompt override for %s from %s", agent_name, prompt_path
        )
        return content
    except Exception:
        logger.warning(
            "Failed to read system prompt override at %s", prompt_path, exc_info=True
        )
        return None


def load_few_shot_exemplars(
    agent_name: str,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Return few-shot exemplars for *agent_name*, or empty list.

    Looks for (in priority order):

    1. ``$OPENJARVIS_HOME/agents/<agent_name>/few_shot.<lang>.json``
    2. ``$OPENJARVIS_HOME/agents/<agent_name>/few_shot.json``

    Expected format: ``[{"input": "Q", "output": "A"}, ...]``.
    """
    from openjarvis.speech.language import DEFAULT_LANGUAGE

    home = _openjarvis_home()
    agent_dir = home / "agents" / agent_name

    if language:
        lang_path = agent_dir / f"few_shot.{language}.json"
        if lang_path.exists():
            data = _read_json_list(lang_path)
            if data is not None:
                return data

    if language != DEFAULT_LANGUAGE:
        lang_path = agent_dir / f"few_shot.{DEFAULT_LANGUAGE}.json"
        if lang_path.exists():
            data = _read_json_list(lang_path)
            if data is not None:
                return data

    fs_path = agent_dir / "few_shot.json"
    if not fs_path.exists():
        return []
    data = _read_json_list(fs_path)
    return data or []


def _read_json_list(path: Path) -> list[dict[str, Any]] | None:
    """Read a JSON list from *path*, returning ``None`` on any failure."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning(
            "Failed to read few-shot exemplars at %s", path, exc_info=True
        )
        return None
    if not isinstance(data, list):
        logger.warning("few_shot file at %s is not a list", path)
        return None
    logger.info(
        "Loaded %d few-shot exemplars from %s", len(data), path
    )
    return data
