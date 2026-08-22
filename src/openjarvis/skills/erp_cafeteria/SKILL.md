# ERP Cafetería Skill

Conectas con el ERP corriendo en `http://localhost:3000` para responder
preguntas rápidas del equipo por voz o chat.

## Credenciales

- **Usuario**: `admin`
- **Password**: `admin123`

(Se pueden sobreescribir pasando `username`/`password` al construir
`ERPCafeteriaActions`.)

## Acciones disponibles

| Acción | Descripción | Frases |
| --- | --- | --- |
| `ventas_hoy` | Reporte de ventas del día | "cuánto vendimos", "ventas hoy" |
| `estado_mesas` | Conteo mesas libres/ocupadas | "estado mesas", "mesas disponibles" |
| `asistencia_hoy` | Asistencia del día | "quién trabaja hoy", "asistencia" |
| `abrir_reportes` | Abre página de reportes | "abrir reportes", "ver reportes" |
| `abrir_mesas` | Abre vista de mesas | "abrir mesas", "ver mesas" |
| `abrir_admin` | Abre dashboard admin | "abrir admin", "ver dashboard" |

## Frases que entiendo

- "Jarvis, cuánto vendimos hoy?" → `ventas_hoy`
- "Jarvis, cómo van las mesas?" → `estado_mesas`
- "Jarvis, abre los reportes" → `abrir_reportes`
- "Jarvis, quién está trabajando hoy?" → `asistencia_hoy`
- "Jarvis, abre el admin" → `abrir_admin`

## Uso programático

```python
from openjarvis.skills.erp_cafeteria import ERPCafeteriaActions

actions = ERPCafeteriaActions()  # default localhost:3000
print(await actions.get_ventas_hoy())
print(await actions.get_estado_mesas())
print(actions.abrir_reportes())  # URL string
```

## Endpoints usados

- `POST /api/login` — autenticación por form (cookies de sesión)
- `GET /api/reportes/excel?fecha=YYYY-MM-DD` — ventas del día (JSON o binario)
- `GET /dashboard` — fallback de scraping HTML
- `GET /mesas` — vista de mesas (HTML con tokens `LIBRE`/`OCUPADA`)
- `GET /asistencia` — marcas de entrada/salida del día
- `/reportes`, `/mesas`, `/admin` — páginas a abrir en el navegador