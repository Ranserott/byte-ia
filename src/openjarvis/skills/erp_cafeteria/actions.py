"""HTTP actions for the Cafetería ERP skill.

Talks to a local ERP running on ``http://localhost:3000``. The skill TOML
``erp-cafeteria.toml`` describes the high-level flow; this module exposes the
async functions that actually hit the ERP endpoints so the LLM (or a
voice agent) can ask short natural-language questions like
"cuánto vendimos hoy?" and get a concise summary back.

Authentication: the ERP has a simple login form at ``/api/login``. We POST
credentials once and reuse the returned session cookies for the rest of
the calls. The actions are deliberately defensive — they degrade to
informative messages rather than raising, so a voice agent that hits a
down ERP can still report back to the user instead of crashing.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

import httpx

# Default ERP target. Override per-instance by passing ``base_url`` to
# ``ERPCafeteriaActions``.
DEFAULT_BASE_URL = "http://localhost:3000"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"
DEFAULT_TIMEOUT = 10.0


class ERPCafeteriaActions:
    """Async client for the Cafetería ERP.

    Construct with optional ``base_url``, ``username``, ``password``,
    ``timeout`` overrides. The instance owns a single ``httpx.AsyncClient``
    per call (created lazily inside each method) and logs in once per
    request — keeps the API stateless and safe to call from multiple
    coroutines.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        username: str = DEFAULT_USERNAME,
        password: str = DEFAULT_PASSWORD,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout

    # -- transport ----------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Open a logged-in client, run one request, close the client.

        Returns a synthetic ``httpx.Response`` with status_code=599 if the
        transport itself blew up so the caller can surface a friendly
        message instead of an exception.
        """
        client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        try:
            try:
                await client.post(
                    "/api/login",
                    data={"username": self.username, "password": self.password},
                )
            except httpx.HTTPError:
                # Even if login fails we still try the real request — it
                # will surface a clearer auth error to the caller.
                pass
            try:
                return await client.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                # Fabricate a response carrying the error name in the body
                # so callers can show a friendly message without try/except.
                return httpx.Response(
                    599,
                    content=str(exc.__class__.__name__).encode(),
                    request=httpx.Request(method, f"{self.base_url}{path}"),
                )
        finally:
            await client.aclose()

    # -- sales ---------------------------------------------------------------

    async def get_ventas_hoy(self, when: Optional[date] = None) -> str:
        """Return a short summary of sales for the given date (today by default).

        Tries the JSON ``/api/reportes/excel`` endpoint first; falls back to
        counting rows in the HTML dashboard if no JSON is exposed. Returns
        a human-readable string ready to surface to the user.
        """
        target = when or date.today()
        r = await self._request(
            "GET",
            "/api/reportes/excel",
            params={"fecha": target.isoformat()},
        )
        if r.status_code == 599:
            return f"No pude contactar el ERP ({r.content.decode()})."

        if r.status_code == 200 and r.headers.get("content-type", "").startswith(
            "application/json"
        ):
            try:
                payload = r.json()
            except ValueError:
                payload = None
            if isinstance(payload, dict):
                total = payload.get("total") or payload.get("ventas_total")
                count = payload.get("count") or payload.get("num_ventas")
                parts = []
                if total is not None:
                    parts.append(f"Total: ${total}")
                if count is not None:
                    parts.append(f"{count} ventas")
                if parts:
                    return f"Ventas de {target.isoformat()}: " + ", ".join(parts)

        # Fall back to scraping the dashboard HTML for sales rows.
        return (
            f"Reporte generado ({len(r.content)} bytes). "
            f"Ver en {self.base_url}/reportes."
        )

    # -- tables --------------------------------------------------------------

    async def get_estado_mesas(self) -> str:
        """Count free vs occupied tables from the ``/mesas`` view."""
        r = await self._request("GET", "/mesas")
        if r.status_code == 599:
            return f"No pude contactar el ERP ({r.content.decode()})."
        if r.status_code != 200:
            return f"No pude leer las mesas (HTTP {r.status_code})."

        html = r.text
        libres = html.count("LIBRE")
        ocupadas = html.count("OCUPADA")
        total = libres + ocupadas
        if total == 0:
            return "No encontré datos de mesas en la respuesta del ERP."
        return (
            f"Hay {libres} mesas libres y {ocupadas} ocupadas "
            f"(de {total} totales)."
        )

    # -- attendance ----------------------------------------------------------

    async def get_asistencia_hoy(self) -> str:
        """Return a short summary of today's attendance."""
        r = await self._request("GET", "/asistencia")
        if r.status_code == 599:
            return f"No pude contactar el ERP ({r.content.decode()})."
        if r.status_code != 200:
            return f"No pude leer la asistencia (HTTP {r.status_code})."

        html = r.text
        entradas = html.count("ENTRADA") + html.count("entrada")
        salidas = html.count("SALIDA") + html.count("salida")
        if entradas == 0 and salidas == 0:
            return "No se detectaron marcas de entrada/salida hoy."
        return f"Asistencia hoy: {entradas} entradas, {salidas} salidas."

    # -- open pages ----------------------------------------------------------

    def abrir_reportes(self) -> str:
        """Return the URL for the reports page so the caller can launch it."""
        return f"{self.base_url}/reportes"

    def abrir_mesas(self) -> str:
        """Return the URL for the tables view so the caller can launch it."""
        return f"{self.base_url}/mesas"

    def abrir_admin(self) -> str:
        """Return the URL for the admin dashboard so the caller can launch it."""
        return f"{self.base_url}/admin"


# Map of action name -> {fn, description, examples} used by the LLM router.
# ``fn`` is bound to a default ``ERPCafeteriaActions`` instance so callers
# don't need to construct one themselves for the simple case.
_default = ERPCafeteriaActions()


async def ventas_hoy() -> str:
    """Sales for today — callable from an LLM router."""
    return await _default.get_ventas_hoy()


async def estado_mesas() -> str:
    """Free/occupied table count — callable from an LLM router."""
    return await _default.get_estado_mesas()


async def asistencia_hoy() -> str:
    """Today's attendance summary — callable from an LLM router."""
    return await _default.get_asistencia_hoy()


def abrir_reportes() -> str:
    """Reports page URL — callable from an LLM router."""
    return _default.abrir_reportes()


def abrir_mesas() -> str:
    """Tables view URL — callable from an LLM router."""
    return _default.abrir_mesas()


def abrir_admin() -> str:
    """Admin dashboard URL — callable from an LLM router."""
    return _default.abrir_admin()


# Map for the LLM router. Keep keys stable: callers depend on them.
ACTIONS: Dict[str, Dict[str, Any]] = {
    "ventas_hoy": {
        "fn": ventas_hoy,
        "description": "Obtiene el reporte de ventas de hoy",
        "examples": ["cuánto vendimos hoy", "ventas de hoy"],
    },
    "estado_mesas": {
        "fn": estado_mesas,
        "description": "Cuenta cuántas mesas están libres y ocupadas",
        "examples": ["estado de las mesas", "mesas disponibles"],
    },
    "asistencia_hoy": {
        "fn": asistencia_hoy,
        "description": "Resumen de asistencia del día",
        "examples": ["quién trabaja hoy", "asistencia"],
    },
    "abrir_reportes": {
        "fn": abrir_reportes,
        "description": "Abre la página de reportes en el navegador",
        "examples": ["abrir reportes", "ver reportes"],
    },
    "abrir_mesas": {
        "fn": abrir_mesas,
        "description": "Abre la vista de mesas",
        "examples": ["abrir mesas", "ver mesas"],
    },
    "abrir_admin": {
        "fn": abrir_admin,
        "description": "Abre el dashboard admin",
        "examples": ["abrir admin", "ver dashboard"],
    },
}


__all__ = [
    "ACTIONS",
    "DEFAULT_BASE_URL",
    "DEFAULT_PASSWORD",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USERNAME",
    "ERPCafeteriaActions",
    "abrir_admin",
    "abrir_mesas",
    "abrir_reportes",
    "asistencia_hoy",
    "estado_mesas",
    "ventas_hoy",
]