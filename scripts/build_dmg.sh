#!/bin/bash
# build_dmg.sh - Build simple para Byte IA (JARVIS liviano)
# Crea un .app que es un webview apuntando al index.html incluido

set -euo pipefail

# ============================================
# CONFIGURACIÓN
# ============================================
APP_NAME="byte-ia"
DISPLAY_NAME="Byte IA"
VERSION="1.0.1"
BUNDLE_ID="com.ranserott.byteia"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
DMG_DIR="$BUILD_DIR/dmg"
APP_DIR="$BUILD_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
DIST_DIR="$ROOT_DIR/dist"

# ============================================
# LIMPIEZA
# ============================================
echo "🧹 Limpiando..."
rm -rf "$BUILD_DIR"
rm -rf "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR" "$DMG_DIR"

# ============================================
# PASO 1: Crear estructura .app
# ============================================
echo ""
echo "📦 [1/4] Creando .app bundle..."
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

# Info.plist
cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$DISPLAY_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$DISPLAY_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Byte IA necesita el micrófono para escucharte.</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>Byte IA necesita accesibilidad para controlarte las apps.</string>
</dict>
</plist>
EOF

echo "APPL????" > "$CONTENTS_DIR/PkgInfo"

# ============================================
# PASO 2: Launcher (Swift nativo que abre Safari)
# ============================================
echo ""
echo "🔧 [2/4] Creando launcher nativo (Swift)..."

cat > "$MACOS_DIR/byte-ia" << 'LAUNCHER_EOF'
#!/bin/bash
# Byte IA - Lanzador nativo
# Este launcher abre index.html en Safari (no requiere permisos especiales)

# Detectar la app bundle
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_BUNDLE="$(cd "$SCRIPT_DIR/../.." && pwd)"
INDEX="$APP_BUNDLE/Contents/Resources/index.html"
TTS_HELPER="$APP_BUNDLE/Contents/Resources/byte-ia-tts.sh"

# Abrir el HTML en Safari (modo kiosko-like con la barra visible)
open -a "Safari" "$INDEX"

echo "Byte IA launched"
exit 0
LAUNCHER_EOF

chmod +x "$MACOS_DIR/byte-ia"
echo "   ✅ Launcher creado"

# ============================================
# PASO 3: Copiar recursos
# ============================================
echo ""
echo "📁 [3/4] Copiando recursos..."

# Copiar HTML
cp "$ROOT_DIR/resources/index.html" "$RESOURCES_DIR/index.html"

# Copiar TTS helper
cp "$ROOT_DIR/resources/byte-ia-tts.sh" "$RESOURCES_DIR/byte-ia-tts.sh"
chmod +x "$RESOURCES_DIR/byte-ia-tts.sh"

# Copiar assets
[ -d "$ROOT_DIR/assets" ] && cp -R "$ROOT_DIR/assets" "$RESOURCES_DIR/assets"

# Docs
mkdir -p "$RESOURCES_DIR/docs"
[ -f "$ROOT_DIR/README.md" ] && cp "$ROOT_DIR/README.md" "$RESOURCES_DIR/docs/"

# Tamaño del bundle
echo "   Bundle: $(du -sh "$APP_DIR" | cut -f1)"

# ============================================
# PASO 4: Code sign + DMG
# ============================================
echo ""
echo "🔏 Firmando..."

# Intentar múltiples métodos de firma
SIGNED=false

# Método 1: Developer ID si existe (con timeout para no colgarse)
DEV_ID=""
if command -v security &> /dev/null; then
    DEV_ID=$(security find-identity -v -p codesigning 2>/dev/null < /dev/null | grep "Developer ID Application" | head -1 | awk -F'"' '{print $2}' || echo "")
fi
if [ -n "$DEV_ID" ]; then
    echo "   Usando Developer ID: $DEV_ID"
    if codesign --force --deep --sign "$DEV_ID" --options runtime "$APP_DIR" 2>&1 | tail -3; then
        SIGNED=true
    fi
fi

# Método 2: Ad-hoc si no hay Developer ID
if [ "$SIGNED" = false ]; then
    echo "   Usando firma ad-hoc (sin Apple Developer ID)"
    codesign --force --deep --sign - "$APP_DIR" 2>&1 | tail -2 || true
    SIGNED=true
fi

# Verificar firma
echo "   Verificando firma..."
codesign --verify --verbose "$APP_DIR" 2>&1 | head -3 || true

echo "   ✅ Listo"
echo ""
echo "💿 [4/4] Creando .dmg..."

DMG_PATH="$DIST_DIR/$APP_NAME-$VERSION.dmg"

mkdir -p "$DMG_DIR"
cp -R "$APP_DIR" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Applications"

# Background opcional
mkdir -p "$DMG_DIR/.background"
# (Aquí podrías poner una imagen .png 600x400 si querés)

hdiutil create -volname "$DISPLAY_NAME" \
    -srcfolder "$DMG_DIR" \
    -ov -format UDZO \
    -fs HFS+J \
    "$DMG_PATH" 2>&1 | tail -2

if [ -f "$DMG_PATH" ]; then
    SIZE=$(du -h "$DMG_PATH" | cut -f1)
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ DMG CREADO"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📦 $DMG_PATH"
    echo "📏 Tamaño: $SIZE"
    echo "🏷️  Versión: $VERSION"
    echo ""
    echo "Para usar:"
    echo "  1. Abre el .dmg"
    echo "  2. Arrastra 'Byte IA.app' a /Applications"
    echo "  3. Abrela (se abrirá Safari con el JARVIS)"
    echo "  4. Click en ⚙ y pega tu API key de MiniMax"
    echo "  5. Click en el círculo para hablar"
else
    echo "❌ Error"
    exit 1
fi
