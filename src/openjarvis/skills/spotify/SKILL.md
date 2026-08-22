# Spotify Skill

Controla Spotify desde comandos de voz o chat usando AppleScript nativo.
No necesita OAuth ni API keys — sólo la app de Spotify instalada.

## Requisitos

- **macOS** (AppleScript no está disponible en otros OS).
- **App de Spotify** instalada y al menos abierta una vez (para registrar
  el bundle en Launch Services).
- Sin dependencias de Python. Si querés usar la Spotify Web API en su
  lugar, instalá `spotipy` opcionalmente:
  ```bash
  pip install spotipy
  ```

## Acciones

| Acción | Descripción | Frases |
| --- | --- | --- |
| `play` | Reproduce artista o canción | "reproduce X", "pon Y" |
| `pause` | Pausa reproducción | "pausá", "pausa" |
| `resume` | Reanuda reproducción | "seguí", "reanudá" |
| `next_track` | Siguiente canción | "siguiente", "next" |
| `previous_track` | Canción anterior | "anterior", "previous" |
| `volume` | Volumen 0-100 | "volumen al 50", "bajá a 30" |

## Uso programático

```python
from openjarvis.skills.spotify import play, pause, volume

play("Bad Bunny")
pause()
volume(50)
```

## Detalles de implementación

- Backend: AppleScript (`tell application "Spotify"`).
- Si el track no está en tu librería, hace fallback a `search` y reproduce
  el primer resultado.
- El volumen se clampea a 0-100 incluso si el LLM manda valores fuera de
  rango.
- Las acciones nunca lanzan excepciones — devuelven strings de error
  listos para que el agente de voz se los diga al usuario.
