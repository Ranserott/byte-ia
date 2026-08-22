<div align="center">
  <img alt="Byte IA" src="assets/OpenJarvis_Horizontal_Logo.png" width="400">

  <p><i>🤖 JARVIS asistente de voz open source en español</i></p>

  <p>
    <a href="https://github.com/open-jarvis/OpenJarvis"><img src="https://img.shields.io/badge/forked%20from-OpenJarvis-blue" alt="Forked from OpenJarvis"></a>
    <a href="https://github.com/Ranserott/byte-ia/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License"></a>
    <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue" alt="Python">
    <img src="https://img.shields.io/badge/languages-8-orange" alt="Languages">
    <img src="https://img.shields.io/badge/macOS-native-blue" alt="macOS Native">
  </p>

  <p>
    <strong>🎤 "Oye Byte, cuánto vendimos hoy?"</strong> · <strong>🎵 "Pon música de Coldplay"</strong> · <strong>📅 "Qué tengo hoy?"</strong>
  </p>
</div>

---

## 🎉 Byte IA — Tu JARVIS en español

**Byte IA** es un fork mejorado de [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) optimizado para el mercado hispanohablante y con integraciones nativas de macOS.

### 🌟 Mejoras sobre OpenJarvis original

| # | Mejora | Descripción |
|---|---|---|
| 🇪🇸 | **Español completo** | STT, TTS, prompts y responses — todo en español por defecto |
| 🎤 | **Wake word "Oye Jarvis"** | Detector con `openWakeWord` + fallback a text matching + push-to-talk |
| 🔌 | **Skill ERP Cafetería** | Controla tu ERP por voz: ventas, mesas, asistencia, reportes |
| 🎨 | **Orb customizado** | 4 estados con colores (idle/listening/thinking/speaking) |
| 🎵 | **Skills nativos macOS** | Spotify, Apple Calendar, Apple Music vía AppleScript (sin OAuth) |
| 🖥️ | **Setup wizard** | Configuración guiada para macOS (idioma, permisos, LLM) |
| 🧠 | **Memoria semántica** | Embeddings multilingües + auto-extract de memorias |

### 🗣️ Ejemplos de uso

```
"Oye Jarvis, cómo van las ventas hoy?"
→ "Llevas 15 boletas, $234.500, top: Espresso"

"Oye Jarvis, pon música de Coldplay"
→ "Reproduciendo Coldplay en Spotify"

"Oye Jarvis, qué tengo hoy?"
→ "Reunión con equipo 10am, almuerzo 13:30"

"Oye Jarvis, abre los reportes"
→ Abre http://localhost:3000/reportes en el navegador
```

### 🚀 Instalación rápida

```bash
# 1. Clonar
git clone https://github.com/Ranserott/byte-ia.git
cd byte-ia

# 2. Instalar dependencias
uv sync --extra dev
pip install openwakeword sentence-transformers rumps

# 3. Levantar Ollama (gratis)
ollama serve
ollama pull llama3.1:8b

# 4. Setup wizard (primera vez)
./scripts/setup_wizard.py

# 5. Hablarle 🎤
jarvis start
```

### 🏗️ Stack

- **STT**: Whisper (local) con detección automática de idioma
- **TTS**: macOS `say` nativo + Kokoro/Piper TTS
- **Wake word**: openWakeWord (ONNX, local)
- **LLM**: Ollama local (gratis) o Claude/OpenAI (cloud)
- **Memoria**: SQLite FTS5 + sentence-transformers
- **Skills**: 30+ connectors (Gmail, Calendar, etc) + 4 nuevos (ERP, Spotify, Calendar, Music)
- **UI**: Frontend Next.js + Orb customizado con Canvas API

### 📋 Skills incluidos

| Skill | Plataforma | OAuth/API |
|---|---|---|
| Gmail, Calendar, Drive | Google | Sí (OAuth) |
| Apple Notes, Calendar, Music, Reminders | macOS | No (nativo) |
| WhatsApp, Slack, iMessage | Multi | Varía |
| **ERP Cafetería** (nuevo) | Web (httpx) | No |
| **Spotify** (nuevo) | macOS | No (AppleScript) |
| **Apple Calendar nativo** (nuevo) | macOS | No (AppleScript) |
| **Apple Music nativo** (nuevo) | macOS | No (AppleScript) |

### 🌍 Idiomas soportados

- 🇪🇸 Español (default)
- 🇬🇧 English
- 🇧🇷 Português
- 🇫🇷 Français
- 🇮🇹 Italiano
- 🇩🇪 Deutsch
- 🇨🇳 中文
- 🇯🇵 日本語

### 📄 Licencia

Apache 2.0 — ver [LICENSE](LICENSE)

### 🙏 Agradecimientos

- [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) — el proyecto original
- [Stanford AI Lab](https://openjarvis.stanford.edu/) — research
- Anthropic, OpenAI, Ollama, Whisper, sentence-transformers — las herramientas que hacen esto posible

---

<p align="center">
  Hecho con 🍌 por Platanito · Fork personal mantenido activamente
</p>
