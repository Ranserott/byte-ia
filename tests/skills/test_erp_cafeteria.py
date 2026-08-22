"""Tests for the ERP Cafetería skill actions.

Mocks all HTTP calls via ``respx`` so we never touch the real ERP. The
actions are deliberately defensive — these tests verify both the happy
path and a few of the failure modes (server down, non-JSON response,
HTTP errors).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from openjarvis.skills.erp_cafeteria import ERPCafeteriaActions, actions as actions_mod

BASE = "http://localhost:3000"


@pytest.fixture
def erp() -> ERPCafeteriaActions:
    return ERPCafeteriaActions(base_url=BASE)


class TestLogin:
    @pytest.mark.asyncio
    @respx.mock
    async def test_login_runs_per_call(self, erp: ERPCafeteriaActions) -> None:
        login_route = respx.post(f"{BASE}/api/login").mock(
            return_value=httpx.Response(200, text="ok")
        )
        mesas_route = respx.get(f"{BASE}/mesas").mock(
            return_value=httpx.Response(
                200,
                text="<div class='mesa'>M1 LIBRE</div><div class='mesa'>M2 OCUPADA</div>",
            )
        )

        msg = await erp.get_estado_mesas()

        assert login_route.called
        assert mesas_route.called
        assert "1 mesas libres" in msg
        assert "1 ocupadas" in msg


class TestVentasHoy:
    @pytest.mark.asyncio
    @respx.mock
    async def test_json_payload_is_summarised(self, erp: ERPCafeteriaActions) -> None:
        respx.post(f"{BASE}/api/login").mock(return_value=httpx.Response(200))
        respx.get(f"{BASE}/api/reportes/excel").mock(
            return_value=httpx.Response(
                200,
                json={"total": 12500.5, "count": 42},
                headers={"content-type": "application/json"},
            )
        )

        msg = await erp.get_ventas_hoy()

        assert "Total: $12500.5" in msg
        assert "42 ventas" in msg

    @pytest.mark.asyncio
    @respx.mock
    async def test_non_json_falls_back_to_dashboard_message(
        self, erp: ERPCafeteriaActions
    ) -> None:
        respx.post(f"{BASE}/api/login").mock(return_value=httpx.Response(200))
        respx.get(f"{BASE}/api/reportes/excel").mock(
            return_value=httpx.Response(
                200,
                content=b"PK\x03\x04not-really-json",
                headers={"content-type": "application/vnd.ms-excel"},
            )
        )
        respx.get(f"{BASE}/dashboard").mock(return_value=httpx.Response(200, text=""))

        msg = await erp.get_ventas_hoy()

        assert "Reporte generado" in msg
        assert f"{BASE}/reportes" in msg

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_error_returns_friendly_message(
        self, erp: ERPCafeteriaActions
    ) -> None:
        respx.post(f"{BASE}/api/login").mock(return_value=httpx.Response(200))
        respx.get(f"{BASE}/api/reportes/excel").mock(
            side_effect=httpx.ConnectError("ERP is down")
        )

        msg = await erp.get_ventas_hoy()

        assert "No pude contactar el ERP" in msg


class TestEstadoMesas:
    @pytest.mark.asyncio
    @respx.mock
    async def test_counts_libres_and_ocupadas(self, erp: ERPCafeteriaActions) -> None:
        respx.post(f"{BASE}/api/login").mock(return_value=httpx.Response(200))
        respx.get(f"{BASE}/mesas").mock(
            return_value=httpx.Response(
                200,
                text=(
                    "<tr><td>1</td><td>LIBRE</td></tr>"
                    "<tr><td>2</td><td>OCUPADA</td></tr>"
                    "<tr><td>3</td><td>OCUPADA</td></tr>"
                ),
            )
        )

        msg = await erp.get_estado_mesas()

        assert "1 mesas libres" in msg
        assert "2 ocupadas" in msg

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_html_reports_no_data(
        self, erp: ERPCafeteriaActions
    ) -> None:
        respx.post(f"{BASE}/api/login").mock(return_value=httpx.Response(200))
        respx.get(f"{BASE}/mesas").mock(return_value=httpx.Response(200, text=""))

        msg = await erp.get_estado_mesas()

        assert "No encontré datos" in msg

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_surfaces_status(
        self, erp: ERPCafeteriaActions
    ) -> None:
        respx.post(f"{BASE}/api/login").mock(return_value=httpx.Response(200))
        respx.get(f"{BASE}/mesas").mock(return_value=httpx.Response(500, text="boom"))

        msg = await erp.get_estado_mesas()

        assert "HTTP 500" in msg


class TestAsistenciaHoy:
    @pytest.mark.asyncio
    @respx.mock
    async def test_counts_entradas_and_salidas(
        self, erp: ERPCafeteriaActions
    ) -> None:
        respx.post(f"{BASE}/api/login").mock(return_value=httpx.Response(200))
        respx.get(f"{BASE}/asistencia").mock(
            return_value=httpx.Response(
                200,
                text=(
                    "<tr><td>Ana</td><td>ENTRADA 09:00</td></tr>"
                    "<tr><td>Beto</td><td>ENTRADA 09:15</td></tr>"
                    "<tr><td>Ana</td><td>SALIDA 17:00</td></tr>"
                ),
            )
        )

        msg = await erp.get_asistencia_hoy()

        assert "2 entradas" in msg
        assert "1 salidas" in msg

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_marks_reports_cleanly(
        self, erp: ERPCafeteriaActions
    ) -> None:
        respx.post(f"{BASE}/api/login").mock(return_value=httpx.Response(200))
        respx.get(f"{BASE}/asistencia").mock(return_value=httpx.Response(200, text=""))

        msg = await erp.get_asistencia_hoy()

        assert "No se detectaron marcas" in msg


class TestOpenUrls:
    def test_abrir_reportes(self, erp: ERPCafeteriaActions) -> None:
        assert erp.abrir_reportes() == f"{BASE}/reportes"

    def test_abrir_mesas(self, erp: ERPCafeteriaActions) -> None:
        assert erp.abrir_mesas() == f"{BASE}/mesas"

    def test_abrir_admin(self, erp: ERPCafeteriaActions) -> None:
        assert erp.abrir_admin() == f"{BASE}/admin"


class TestActionsMap:
    def test_module_level_functions_match_map(self) -> None:
        # All callable actions are registered with descriptions and examples.
        assert set(actions_mod.ACTIONS) == {
            "ventas_hoy",
            "estado_mesas",
            "asistencia_hoy",
            "abrir_reportes",
            "abrir_mesas",
            "abrir_admin",
        }
        for name, entry in actions_mod.ACTIONS.items():
            assert callable(entry["fn"]), f"{name} fn must be callable"
            assert entry["description"], f"{name} must have a description"

    @pytest.mark.asyncio
    @respx.mock
    async def test_module_level_ventas_hoy_uses_default(self) -> None:
        # Hits the DEFAULT_BASE_URL. We mock both it and the localhost alias
        # so the test works whether or not actions_mod._default was touched.
        for base in (actions_mod.DEFAULT_BASE_URL,):
            respx.post(f"{base}/api/login").mock(return_value=httpx.Response(200))
            respx.get(f"{base}/api/reportes/excel").mock(
                return_value=httpx.Response(
                    200,
                    json={"total": 100, "count": 1},
                    headers={"content-type": "application/json"},
                )
            )

        msg = await actions_mod.ventas_hoy()

        assert "Total: $100" in msg

    def test_open_helpers_return_strings(self) -> None:
        assert actions_mod.abrir_reportes().startswith("http")
        assert actions_mod.abrir_mesas().startswith("http")
        assert actions_mod.abrir_admin().startswith("http")