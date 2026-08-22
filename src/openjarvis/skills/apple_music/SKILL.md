# Apple Music Skill

Controla la app Music de macOS desde comandos de voz o chat usando
AppleScript nativo. No necesita configuración.

## Requisitos

- **macOS** (AppleScript no está disponible en otros OS).
- App **Music** con al menos un track en la biblioteca.
- Sin dependencias de Python.

## Acciones

| Acción | Descripción | Frases |
| --- | --- | --- |
| `play` | Busca y reproduce un track de tu biblioteca | "reproduce X", "pon Y" |
| `pause` | Pausa reproducción | "pausá", "pausa" |
| `resume` | Reanuda reproducción | "reanudá", "seguí" |
| `next_track` | Siguiente canción | "siguiente", "next" |
| `previous_track` | Canción anterior | "anterior" |
| `volume` | Volumen 0-100 | "volumen al 50", "bajá a 30" |

## Uso programático

```python
from openjarvis.skills.apple_music import play, pause, volume

play("Bohemian Rhapsody")
pause()
volume(40)
```

## Diferencias con el skill de Spotify

| | Spotify | Apple Music |
| --- | --- | --- |
| Backend | AppleScript | AppleScript |
| API keys | No | No |
| Búsqueda | `play track` (library) + fallback `search` | `library playlist 1 whose name contains` |
| Multi-cuenta | Sí (vía Spotify Connect) | Sí (vía Family Sharing) |

## Detalles de implementación

- La búsqueda usa `library playlist 1` (la playlist "Library" maestra) y
  filtra con `whose name contains` — funciona con bibliotecas grandes.
- Si no encuentra el track, devuelve "No encontré X en tu biblioteca"
  sin levantar excepción.
- El volumen se clampea a 0-100.
