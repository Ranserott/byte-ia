#!/bin/bash
# install.sh - Instalador de Byte IA para macOS
#
# Este script se ejecuta automáticamente la primera vez que se abre
# la app Byte IA desde /Applications, o se puede correr manualmente.

set -euo pipefail

# ============================================
# CONFIGURACIÓN
# ============================================
APP_NAME="byte-ia"
APP_DISPLAY="Byte IA"
BUNDLE_ID="com.ranserott.byteia"

# Ubicaciones
if [ -d "/Applications/${APP_DISPLAY}.app" ]; then
    APP_ROOT="/Applications/${APP_DISPLAY}.app"
elif [ -d "/Applications/${APP_NAME}.app" ]; then
    APP_ROOT="/Applications/${APP_NAME}.app"
else
    # Estamos en modo desarrollo
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    APP_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

CONTENTS_DIR="$APP_ROOT/Contents"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
VENV_DIR="$RESOURCES_DIR/venv"
SRC_DIR="$RESOURCES_DIR/python-src"
BIN_DIR="$RESOURCES_DIR/bin"

LOG_DIR="$HOME/Library/Logs/byte-ia"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/install.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $@" | tee -a "$LOG_FILE"
}

error() {
    log "ERROR: $@"
    echo ""
    echo "❌ Error: $@"
    echo ""
    echo "Ver log: $LOG_FILE"
    if command -v osascript &> /dev/null; then
        osascript -e "display alert \"Byte IA - Error\" message \"$@\"" 2>/dev/null || true
    fi
    exit 1
}

# ============================================
# INICIO
# ============================================
log "Iniciando instalación de Byte IA"
log "APP_ROOT: $APP_ROOT"

# Verificar Python
log "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    error "Python 3 no encontrado. Instala Python 3.10+ desde https://python.org"
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log "Python $PYTHON_VERSION encontrado"

# Verificar que sea 3.10+
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    error "Se requiere Python 3.10+. Versión actual: $PYTHON_VERSION"
fi

# ============================================
# CREAR VENV
# ============================================
if [ ! -d "$VENV_DIR" ]; then
    log "Creando venv en $VENV_DIR..."
    python3 -m venv "$VENV_DIR" 2>&1 | tee -a "$LOG_FILE" || error "No se pudo crear el venv"
fi

# Activar venv
log "Activando venv..."
source "$VENV_DIR/bin/activate" || error "No se pudo activar el venv"

# ============================================
# INSTALAR DEPENDENCIAS
# ============================================
log "Instalando dependencias Python..."

# Upgradear pip
pip install --quiet --upgrade pip 2>&1 | tee -a "$LOG_FILE" || true

# Instalar byte-ia SIN extras (no todo el repo)
if [ -d "$SRC_DIR" ]; then
    log "Instalando byte-ia (solo core, sin extras opcionales)..."
    # Instalar pyproject.toml con --no-deps para evitar instalar TODO
    # y luego instalar manualmente lo esencial
    pip install --quiet --no-deps -e "$SRC_DIR" 2>&1 | tee -a "$LOG_FILE" || log "(install editable falló)"
    
    log "Instalando dependencias mínimas..."
    # Solo lo esencial para que arranque
    pip install --quiet "click>=8.1" "rich>=13.0" "pydantic>=2.0" "httpx>=0.25" "pyyaml>=6.0" 2>&1 | tee -a "$LOG_FILE" || log "(deps básicas fallaron)"
else
    log "⚠️  No se encontró $SRC_DIR, saltando instalación editable"
fi

# Dependencias opcionales (no fallan si no se pueden instalar)
log "Instalando dependencias opcionales..."
pip install --quiet openwakeword sentence-transformers 2>&1 | tee -a "$LOG_FILE" || log "(opcional falló)"

# ============================================
# CREAR COMANDO GLOBAL `byte-ia`
# ============================================
log "Creando comando global byte-ia..."

# El launcher Python
cat > "$BIN_DIR/byte-ia" << 'EOF'
#!/usr/bin/env bash
# Byte IA - Entry point global
set -e
APP_ROOT="/Applications/Byte IA.app"
if [ ! -d "$APP_ROOT" ]; then
    APP_ROOT="/Applications/byte-ia.app"
fi
if [ ! -d "$APP_ROOT" ]; then
    echo "❌ Byte IA no encontrado en /Applications"
    echo "Reinstala desde https://github.com/Ranserott/byte-ia/releases"
    exit 1
fi
VENV="$APP_ROOT/Contents/Resources/venv/bin/jarvis"
if [ -f "$VENV" ]; then
    exec "$VENV" "$@"
else
    # Fallback: usar Python del venv directamente
    VENV_PY="$APP_ROOT/Contents/Resources/venv/bin/python3"
    JARVIS_MAIN="$APP_ROOT/Contents/Resources/python-src/src/openjarvis/cli/main.py"
    if [ -f "$VENV_PY" ] && [ -f "$JARVIS_MAIN" ]; then
        exec "$VENV_PY" "$JARVIS_MAIN" "$@"
    fi
fi
echo "❌ No se encontró el binario jarvis"
exit 1
EOF
chmod +x "$BIN_DIR/byte-ia"

# Instalar symlink en /usr/local/bin
if [ -d "/usr/local/bin" ]; then
    ln -sf "$BIN_DIR/byte-ia" "/usr/local/bin/byte-ia" 2>/dev/null || true
fi

# ============================================
# CREAR APP LAUNCHER
# ============================================
LAUNCHER="$CONTENTS_DIR/MacOS/$APP_NAME"
mkdir -p "$(dirname "$LAUNCHER")"

# El launcher que macOS ejecuta
cat > "$LAUNCHER" << 'EOF'
#!/bin/bash
# Byte IA - Lanzador de la app .app
set -e

# Encontrar el bundle .app (puede estar en /Applications o en el bundle local)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_BUNDLE="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Paths importantes
RESOURCES="$APP_BUNDLE/Contents/Resources"
VENV="$RESOURCES/venv/bin/python3"
JARVIS_MAIN="$RESOURCES/python-src/src/openjarvis/cli/main.py"
LAUNCHER_PY="$RESOURCES/byte-ia-launcher.py"

# Si el venv no existe, correr instalador primero
if [ ! -f "$VENV" ] || [ ! -f "$JARVIS_MAIN" ]; then
    # Buscar instalador
    INSTALLER="$RESOURCES/scripts/install.sh"
    if [ -f "$INSTALLER" ]; then
        bash "$INSTALLER"
    else
        osascript -e 'display alert "Byte IA" message "Instalador no encontrado. Por favor reinstala la app."' 2>/dev/null
        exit 1
    fi
fi

# Ejecutar el launcher Python (que tiene lógica para detectar paths)
if [ -f "$LAUNCHER_PY" ]; then
    exec "$VENV" "$LAUNCHER_PY" "$@"
else
    # Fallback directo
    exec "$VENV" "$JARVIS_MAIN" "$@"
fi
EOF
chmod +x "$LAUNCHER"

# ============================================
# COPIAR LAUNCHER PYTHON
# ============================================
cp "$APP_ROOT/scripts/byte-ia-launcher.py" "$RESOURCES/byte-ia-launcher.py" 2>/dev/null || true

# ============================================
# CODE SIGN AD-HOC
# ============================================
log "Firmando app (ad-hoc)..."
codesign --force --deep --sign - "$APP_ROOT" 2>&1 | tee -a "$LOG_FILE" || log "(codesign falló)"

# ============================================
# FINAL
# ============================================
log "✅ Instalación completada"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Byte IA instalado correctamente"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Ubicación: $APP_ROOT"
echo "🐍 Python: $VENV_DIR/bin/python3"
echo "🛠️  Comando: byte-ia"
echo ""
echo "Para usar:"
echo "  • Doble click en Byte IA.app"
echo "  • O desde terminal: byte-ia"
echo ""
echo "Config:"
echo "  bash $RESOURCES/scripts/setup_wizard.py"
echo ""
