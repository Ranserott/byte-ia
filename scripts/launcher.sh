#!/bin/bash
# launcher.sh - Lanzador minimalista de Byte IA
# Este script abre una terminal y corre los comandos para que el usuario vea
# qué está pasando (debug-friendly).

set -e

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_BUNDLE="$(cd "$SCRIPT_DIR/../.." && pwd)"

LOG_DIR="$HOME/Library/Logs/byte-ia"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/launcher.log"

echo "[$(date)] Launcher started from $SCRIPT_DIR" >> "$LOG_FILE"

# Mensaje amigable al usuario
osascript <<EOF 2>> "$LOG_FILE"
display dialog "Byte IA necesita inicializar la primera vez. Se abrirá una terminal para instalar las dependencias. Esto puede tardar 2-3 minutos." buttons {"OK"} default button "OK" with title "Byte IA"
EOF

# Abrir Terminal.app y correr el instalador
osascript <<EOF 2>> "$LOG_FILE"
tell application "Terminal"
    activate
    do script "clear; echo '🛠️  Byte IA - Setup Wizard'; echo ''; cd '$APP_BUNDLE/Contents/Resources' && bash scripts/install.sh 2>&1 | tee -a '$LOG_FILE'; echo ''; echo '✅ Setup completado. Ya puedes cerrar esta terminal y abrir Byte IA desde Launchpad.'"
end tell
EOF

echo "[$(date)] Installer launched in Terminal" >> "$LOG_FILE"
