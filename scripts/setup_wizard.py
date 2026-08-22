#!/usr/bin/env python3
"""Wizard de primera ejecución para OpenJarvis en macOS.

Guía al usuario a través de 5 pasos para dejar Jarvis configurado y listo
para usar: idioma, permisos de macOS, proveedor de IA, prueba de micrófono,
y persistencia de la configuración en ``~/.openjarvis/config.yaml``.

Ejecutar con::

    python scripts/setup_wizard.py

Cada paso degrada con elegancia si las dependencias opcionales
(``sounddevice``) o el clic a "Aceptar" en Preferencias del Sistema no se
completan, de modo que el asistente nunca deja al usuario sin salida.
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path


def step_welcome() -> None:
    """Print the welcome banner and a short intro."""
    print(
        """
╔══════════════════════════════════════╗
║   Bienvenido a Jarvis v2.0          ║
║   Tu asistente personal con voz     ║
╚══════════════════════════════════════╝

Te haré 5 preguntas rápidas para configurar Jarvis.
    """
    )


def step_language() -> str:
    """Prompt the user to pick the assistant language.

    Returns
    -------
    str
        One of ``"es"``, ``"en"``, ``"pt"``. Defaults to ``"es"``.
    """
    print("\n🌍 PASO 1/5: Idioma")
    print("1. Español")
    print("2. English")
    print("3. Português")
    choice = input("Elige (1-3): ").strip()
    return {"1": "es", "2": "en", "3": "pt"}.get(choice, "es")


def step_permissions() -> None:
    """Open the macOS Microphone privacy pane and wait for confirmation.

    The click into System Settings is best-effort; if it fails (e.g. on a
    non-macOS host) the user is told to open it manually.
    """
    print("\n🔐 PASO 2/5: Permisos")
    print("Abriendo Preferencias del Sistema...")
    try:
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
            ],
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        print("(no se pudo abrir automáticamente, ábrelo manualmente)")
    input("Habilita Jarvis en Micrófono. Presiona Enter cuando termines...")


def step_llm() -> str:
    """Prompt the user to pick the LLM provider.

    Returns
    -------
    str
        One of ``"ollama"``, ``"anthropic"``, ``"openai"``. Defaults to
        ``"ollama"``.
    """
    print("\n🤖 PASO 3/5: Proveedor de IA")
    print("1. Ollama local (gratis, recomendado)")
    print("2. Claude API (requiere ANTHROPIC_API_KEY)")
    print("3. OpenAI (requiere OPENAI_API_KEY)")
    choice = input("Elige (1-3): ").strip()
    return {"1": "ollama", "2": "anthropic", "3": "openai"}.get(choice, "ollama")


def step_test_audio() -> None:
    """Record two seconds of audio and report peak volume.

    Silently degrades when ``sounddevice`` is not installed or no audio
    device is available — the user is told to verify their mic and move on.
    """
    print("\n🎤 PASO 4/5: Test de audio")
    print("Probando micrófono (2 segundos)...")
    try:
        import sounddevice as sd  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]
    except ImportError:
        print("(sounddevice no instalado, saltando test)")
        return

    try:
        recording = sd.rec(int(2 * 16000), samplerate=16000, channels=1)
        sd.wait()
        volume = float(np.abs(recording).max())
        status = "(bien)" if volume > 0.01 else "(bajo - verifica tu mic)"
        print(f"✓ Volumen detectado: {volume:.3f} {status}")
    except Exception as exc:  # noqa: BLE001 — user feedback only
        print(f"(error en test: {exc})")


def step_done() -> None:
    """Print the closing message with next-step commands."""
    print(
        """
✅ Jarvis está listo.

Para iniciar:
  $ jarvis start

Para hablarle:
  $ jarvis listen

Documentación: https://open-jarvis.github.io/OpenJarvis
    """
    )


def _write_config(language: str, llm_provider: str, path: Path) -> None:
    """Persist the user's selections to ``~/.openjarvis/config.yaml``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"language: {language}\n"
        f"llm_provider: {llm_provider}\n"
    )


def main() -> int:
    """Run the full wizard and return a shell-style exit code."""
    step_welcome()
    lang = step_language()
    step_permissions()
    llm = step_llm()
    step_test_audio()
    step_done()

    config_path = Path.home() / ".openjarvis" / "config.yaml"
    _write_config(lang, llm, config_path)
    print(f"\n✓ Config guardada en {config_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())