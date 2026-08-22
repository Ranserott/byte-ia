#!/bin/bash
# byte-ia-tts.sh - TTS usando macOS say nativo
# Llamado por la web app via shell protocol

TEXT="$1"
VOICE="${2:-Monica}"
RATE="${3:-200}" # words per minute

if [ -z "$TEXT" ]; then
    exit 1
fi

# Escapar comillas
ESCAPED_TEXT=$(echo "$TEXT" | sed "s/'/\\\\'/g")

# Usar la voz seleccionada
say -v "$VOICE" -r "$RATE" "$ESCAPED_TEXT"
