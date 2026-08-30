#!/usr/bin/env python3
"""
Byte IA - Lanzador de la app
=============================
Este script es el entry point de la app .app en macOS.
Detecta dónde está instalado y lanza el comando correcto.

Funciona en dos modos:
  1. Modo producción: cuando está en /Applications/Byte IA.app
  2. Modo desarrollo: cuando se ejecuta desde el repo
"""

import os
import sys
import subprocess
from pathlib import Path


def get_app_root() -> Path:
    """Encuentra el directorio raíz de la app."""
    # Si está dentro de un .app bundle (modo producción)
    # /Applications/Byte IA.app/Contents/MacOS/byte-ia -> /Applications/Byte IA.app
    me = Path(__file__).resolve()
    if me.parent.name == "MacOS" and me.parent.parent.name == "Contents":
        return me.parent.parent.parent

    # Modo desarrollo: estamos en scripts/
    return Path(__file__).resolve().parent.parent


def get_venv_python() -> str | None:
    """Busca Python del venv creado por el instalador."""
    app_root = get_app_root()
    candidates = [
        # Si está en el bundle
        app_root / "Contents" / "Resources" / "venv" / "bin" / "python3",
        # Si está en /Applications con estructura plana (legacy)
        app_root / "venv" / "bin" / "python3",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def get_jarvis_main() -> str | None:
    """Busca el entry point de JARVIS."""
    app_root = get_app_root()
    candidates = [
        # Si está en el bundle
        app_root
        / "Contents"
        / "Resources"
        / "python-src"
        / "src"
        / "openjarvis"
        / "cli"
        / "main.py",
        # Si está en /Applications con estructura plana
        app_root / "python-src" / "src" / "openjarvis" / "cli" / "main.py",
        # Modo desarrollo
        app_root / "src" / "openjarvis" / "cli" / "main.py",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def show_error_and_exit():
    """Muestra error amigable al usuario."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Byte IA - Error de instalación",
        "No se encontró el entorno Python de Byte IA.\n\n"
        "Por favor ejecuta el instalador:\n"
        "  bash /Applications/Byte\\ IA.app/Contents/Resources/scripts/install.sh\n\n"
        "O reinstala la app desde:\n"
        "  https://github.com/Ranserott/byte-ia/releases",
    )
    sys.exit(1)


def main():
    """Entry point principal."""
    # Verificar venv
    venv_python = get_venv_python()
    if not venv_python:
        show_error_and_exit()

    # Verificar JARVIS
    jarvis_main = get_jarvis_main()
    if not jarvis_main:
        show_error_and_exit()

    # Lanzar JARVIS con el Python del venv
    # Pasar todos los args al JARVIS
    # type: ignore[arg-type]  # venv_python y jarvis_main son no-None verificados arriba
    os.execv(venv_python, [venv_python, jarvis_main, *sys.argv[1:]])


if __name__ == "__main__":
    main()
