"""ERP Cafetería skill actions.

HTTP actions for talking to the local Cafetería ERP. Pair with the
``erp-cafeteria.toml`` manifest in ``openjarvis/skills/data``.
"""

from __future__ import annotations

from openjarvis.skills.erp_cafeteria.actions import (
    ACTIONS,
    DEFAULT_BASE_URL,
    DEFAULT_PASSWORD,
    DEFAULT_TIMEOUT,
    DEFAULT_USERNAME,
    ERPCafeteriaActions,
    abrir_admin,
    abrir_mesas,
    abrir_reportes,
    asistencia_hoy,
    estado_mesas,
    ventas_hoy,
)

SKILL = {
    "name": "erp-cafeteria",
    "version": "1.0.0",
    "actions": ACTIONS,
}

__all__ = [
    "ACTIONS",
    "DEFAULT_BASE_URL",
    "DEFAULT_PASSWORD",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USERNAME",
    "ERPCafeteriaActions",
    "SKILL",
    "abrir_admin",
    "abrir_mesas",
    "abrir_reportes",
    "asistencia_hoy",
    "estado_mesas",
    "ventas_hoy",
]