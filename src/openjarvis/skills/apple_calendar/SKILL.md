# Apple Calendar Skill

Lee los eventos del calendario de macOS desde comandos de voz o chat
usando AppleScript nativo. **Sólo lectura** — nunca crea, modifica ni
borra eventos.

## Requisitos

- **macOS** (AppleScript no está disponible en otros OS).
- La app **Calendar** debe estar disponible (se abre automáticamente al
  primer comando, pero la primera llamada puede tardar unos segundos).
- Sin dependencias de Python.

## Acciones

| Acción | Descripción | Frases |
| --- | --- | --- |
| `eventos_hoy` | Eventos de hoy | "qué tengo hoy", "agenda de hoy" |
| `eventos_manana` | Eventos de mañana | "qué tengo mañana", "reuniones de mañana" |
| `eventos_esta_semana` | Próximos 7 días | "agenda semanal", "qué tengo esta semana" |

## Uso programático

```python
from openjarvis.skills.apple_calendar import eventos_hoy

print(eventos_hoy())
# "Reunión de equipo (Sala A) — 10:00:00 AM\n..."
```

## Detalles de implementación

- Backend: AppleScript (`tell application "Calendar"`).
- Soporta múltiples calendarios: enumera eventos de **todos** ellos.
- Si un evento tiene ubicación, se incluye entre paréntesis.
- Devuelve "Sin eventos X" cuando el día está vacío.
- Las acciones nunca lanzan excepciones — devuelven strings de error
  listos para que el agente de voz se los diga al usuario.
