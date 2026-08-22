<div align="center">
  <img alt="Byte IA" src="assets/OpenJarvis_Horizontal_Logo.png" width="400">

  <p><i>🤖 JARVIS asistente de voz open source en español - Liviano, solo 6.5MB</i></p>

  <p>
    <a href="https://github.com/Ranserott/byte-ia/releases/latest"><img src="https://img.shields.io/badge/descargar-DMG-orange" alt="Download"></a>
    <a href="https://github.com/open-jarvis/OpenJarvis"><img src="https://img.shields.io/badge/forked%20from-OpenJarvis-blue" alt="Forked from OpenJarvis"></a>
    <a href="https://github.com/Ranserott/byte-ia/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License"></a>
    <img src="https://img.shields.io/badge/python-not%20required-blueviolet" alt="No Python">
    <img src="https://img.shields.io/badge/size-6.5MB-success" alt="Size">
  </p>
</div>

---

## 🎉 Byte IA — JARVIS liviano

**Byte IA** es un JARVIS minimalista que usa tu **propia API key de MiniMax** (o cualquier API compatible con OpenAI). Sin Python, sin venv, sin 1GB de ML libs. Solo 6.5MB.

### ✨ Features

- 🎙️ **STT con Web Speech API** del navegador (gratis, sin instalar nada)
- 🤖 **LLM con tu API key** (MiniMax, OpenAI, Anthropic, etc)
- 🔊 **TTS con macOS `say`** nativo (voces en español de alta calidad)
- 💬 **Chat con historial** visible
- ⚙️ **Configuración** guardada en localStorage
- 🌐 **100% en el navegador** - no requiere backend corriendo
- 🇪🇸 **Español completo** - prompts y UI

### 📦 Instalación

1. Descarga [`byte-ia-1.0.1.dmg`](https://github.com/Ranserott/byte-ia/releases/latest)
2. Ábrelo y arrastra `Byte IA.app` a `/Applications`
3. Abre `Byte IA` (se abrirá Safari con la UI)
4. Click en ⚙ arriba a la derecha
5. Pega tu API key de MiniMax
6. Click en el círculo central para hablar 🎤

### 🎯 Comandos rápidos

- 👋 "Hola" / "Hola JARVIS"
- 🕐 "¿Qué hora es?"
- 📺 "Abrir YouTube"
- 😄 "Cuéntame un chiste"
- ❓ "Ayuda"
- Cualquier pregunta → la pasa al LLM

### 🛠️ Stack técnico

- **HTML/CSS/JS** puro (sin frameworks)
- **Web Speech API** para reconocimiento de voz
- **macOS `say`** para síntesis (voces nativas)
- **fetch()** a la API de MiniMax (compatible OpenAI)
- **localStorage** para configuración
- **Safari como webview** (nativo, no Electron/Tauri)

### 🎨 UI

- **Dark mode** nativo
- **Orb central** con animaciones según estado:
  - 🟠 Idle: naranja (listo)
  - 🔵 Listening: cyan (escuchando)
  - 🟡 Thinking: amarillo (procesando)
  - 🟢 Speaking: verde (hablando)
- **Transcript** en tiempo real
- **Quick commands** con un click

### 🌍 Multi-idioma

- 🇪🇸 Español (default, optimizado)
- 🇺🇸 English (cambiar STT lang en consola)

### 🔧 Configuración avanzada

Click en ⚙ para:
- API key (MiniMax, OpenAI, etc)
- Modelo (MiniMax-Text-01, GPT-4, Claude, etc)
- Voz TTS (Monica, Paulina, Juan, Diego, auto)
- System prompt (personalidad de JARVIS)

### 📋 Requisitos

- macOS 14+ (Apple Silicon recomendado)
- Micrófono
- API key de LLM (MiniMax recomendada)
- Conexión a internet (para la API)

### 🎬 Demo flow

```
[Click en ⚙] → Pega "sk-..." → Guarda
[Click en 🎙] → "Hola JARVIS, ¿qué puedes hacer?"
[Orb azul escucha] → [Orb amarillo piensa] → 
[Respuesta del LLM] → [Orb verde habla] → Voz macOS
```

### 📊 Stats

| Métrica | Valor |
|---|---|
| Tamaño DMG | **6.5 MB** |
| Dependencias | **0** (cero) |
| Python | No requiere |
| npm install | No requiere |
| Tiempo de setup | **30 segundos** |

### 🙏 Agradecimientos

- [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) - el proyecto original
- [MiniMax](https://MiniMax.com) - por la API de LLM compatible con OpenAI
- macOS `say` - por las voces nativas en español

### 📄 Licencia

Apache 2.0

---

<p align="center">
  Hecho con 🍌 por Platanito · <a href="https://github.com/Ranserott/byte-ia">Ver en GitHub</a>
</p>
