"""
FinTech Nova - Suite de Pruebas Automáticas
Sesión 14: CI/CD y DevSecOps

Estas pruebas se ejecutan automáticamente dentro del pipeline CI/CD.
Si alguna prueba falla, el pipeline se detiene (rompe el build).

Ejecutar localmente:
    pytest app/test_main.py -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app, db_cuentas, db_transacciones

# ─── Cliente de pruebas (simula peticiones HTTP sin servidor real) ───────────
client = TestClient(app)


# ════════════════════════════════════════════════════════════
# BLOQUE 1: Pruebas de Endpoints Básicos
# ════════════════════════════════════════════════════════════

class TestEndpointsBasicos:
    """Verifica que los endpoints principales responden correctamente."""

    def test_raiz_retorna_200(self):
        """El endpoint raíz debe estar disponible y retornar 200 OK."""
        respuesta = client.get("/")
        assert respuesta.status_code == 200

    def test_raiz_contiene_nombre_servicio(self):
        """La raíz debe identificar el servicio como 'FinTech Nova API'."""
        respuesta = client.get("/")
        datos = respuesta.json()
        assert datos["servicio"] == "FinTech Nova API"

    def test_health_check_retorna_healthy(self):
        """El health check debe reportar estado 'healthy'."""
        respuesta = client.get("/health")
        assert respuesta.status_code == 200
        assert respuesta.json()["status"] == "healthy"

    def test_listar_cuentas_retorna_lista(self):
        """El endpoint de cuentas debe retornar una lista no vacía."""
        respuesta = client.get("/cuentas")
        assert respuesta.status_code == 200
        cuentas = respuesta.json()
        assert isinstance(cuentas, list)
        assert len(cuentas) > 0


# ════════════════════════════════════════════════════════════
# BLOQUE 2: Pruebas de Consulta de Cuentas
# ════════════════════════════════════════════════════════════

class TestConsultaCuentas:
    """Verifica la lógica de consulta de cuentas individuales."""

    def test_obtener_cuenta_existente(self):
        """Debe retornar datos correctos para una cuenta que existe."""
        respuesta = client.get("/cuentas/ACC-001")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["titular"] == "María García"
        assert datos["saldo"] == 5000.00

    def test_obtener_cuenta_inexistente_retorna_404(self):
        """Una cuenta que no existe debe retornar error 404."""
        respuesta = client.get("/cuentas/ACC-999")
        assert respuesta.status_code == 404

    def test_cuenta_tiene_campos_requeridos(self):
        """La respuesta de una cuenta debe incluir titular, saldo y moneda."""
        respuesta = client.get("/cuentas/ACC-002")
        datos = respuesta.json()
        assert "titular" in datos
        assert "saldo" in datos
        assert "moneda" in datos


# ════════════════════════════════════════════════════════════
# BLOQUE 3: Pruebas de Transferencias
# ════════════════════════════════════════════════════════════

class TestTransferencias:
    """Verifica la lógica de negocio de las transferencias."""

    def setup_method(self):
        """Resetea el estado de las cuentas antes de cada prueba."""
        db_cuentas["ACC-001"]["saldo"] = 5000.00
        db_cuentas["ACC-002"]["saldo"] = 3200.50
        db_cuentas["ACC-003"]["saldo"] = 12800.75
        db_transacciones.clear()

    def test_transferencia_exitosa(self):
        """Una transferencia válida debe completarse y retornar 201."""
        payload = {
            "cuenta_origen": "ACC-001",
            "cuenta_destino": "ACC-002",
            "monto": 500.00,
            "descripcion": "Prueba de transferencia"
        }
        respuesta = client.post("/transferencias", json=payload)
        assert respuesta.status_code == 201
        datos = respuesta.json()
        assert datos["estado"] == "completada"
        assert datos["monto"] == 500.00

    def test_transferencia_descuenta_saldo_origen(self):
        """El saldo de la cuenta origen debe reducirse por el monto transferido."""
        saldo_inicial = db_cuentas["ACC-001"]["saldo"]
        monto = 200.00
        payload = {
            "cuenta_origen": "ACC-001",
            "cuenta_destino": "ACC-002",
            "monto": monto
        }
        client.post("/transferencias", json=payload)
        assert db_cuentas["ACC-001"]["saldo"] == saldo_inicial - monto

    def test_transferencia_acredita_saldo_destino(self):
        """El saldo de la cuenta destino debe aumentar por el monto transferido."""
        saldo_inicial = db_cuentas["ACC-002"]["saldo"]
        monto = 300.00
        payload = {
            "cuenta_origen": "ACC-001",
            "cuenta_destino": "ACC-002",
            "monto": monto
        }
        client.post("/transferencias", json=payload)
        assert db_cuentas["ACC-002"]["saldo"] == saldo_inicial + monto

    def test_transferencia_saldo_insuficiente_retorna_400(self):
        """Transferir más del saldo disponible debe retornar error 400."""
        payload = {
            "cuenta_origen": "ACC-001",
            "cuenta_destino": "ACC-002",
            "monto": 99999.00  # Mucho más que el saldo de ACC-001
        }
        respuesta = client.post("/transferencias", json=payload)
        assert respuesta.status_code == 400
        assert "insuficiente" in respuesta.json()["detail"].lower()

    def test_transferencia_cuenta_origen_inexistente(self):
        """Transferir desde una cuenta inexistente debe retornar 404."""
        payload = {
            "cuenta_origen": "ACC-FANTASMA",
            "cuenta_destino": "ACC-002",
            "monto": 100.00
        }
        respuesta = client.post("/transferencias", json=payload)
        assert respuesta.status_code == 404

    def test_transferencia_cuenta_destino_inexistente(self):
        """Transferir a una cuenta inexistente debe retornar 404."""
        payload = {
            "cuenta_origen": "ACC-001",
            "cuenta_destino": "ACC-FANTASMA",
            "monto": 100.00
        }
        respuesta = client.post("/transferencias", json=payload)
        assert respuesta.status_code == 404

    def test_transferencia_monto_negativo_rechazado(self):
        """Un monto negativo o cero debe ser rechazado por validación."""
        payload = {
            "cuenta_origen": "ACC-001",
            "cuenta_destino": "ACC-002",
            "monto": -50.00
        }
        respuesta = client.post("/transferencias", json=payload)
        assert respuesta.status_code == 422  # Unprocessable Entity (validación Pydantic)

    def test_transferencia_se_registra_en_historial(self):
        """Cada transferencia exitosa debe quedar registrada en el historial."""
        payload = {
            "cuenta_origen": "ACC-001",
            "cuenta_destino": "ACC-002",
            "monto": 100.00
        }
        client.post("/transferencias", json=payload)
        historial = client.get("/transacciones").json()
        assert historial["total"] == 1

    def test_multiples_transferencias_se_acumulan(self):
        """El historial debe crecer con cada transferencia procesada."""
        for i in range(3):
            payload = {
                "cuenta_origen": "ACC-003",
                "cuenta_destino": "ACC-001",
                "monto": 10.00
            }
            client.post("/transferencias", json=payload)
        historial = client.get("/transacciones").json()
        assert historial["total"] == 3


# ════════════════════════════════════════════════════════════
# BLOQUE 4: Pruebas de Seguridad Básicas
# ════════════════════════════════════════════════════════════

class TestSeguridadBasica:
    """Verifica que la API maneja casos límite de manera segura."""

    def test_endpoint_inexistente_retorna_404(self):
        """Un endpoint que no existe debe retornar 404, no un error del servidor."""
        respuesta = client.get("/ruta/que/no/existe")
        assert respuesta.status_code == 404

    def test_transferencia_sin_payload_retorna_422(self):
        """Una petición POST sin cuerpo debe ser rechazada correctamente."""
        respuesta = client.post("/transferencias")
        assert respuesta.status_code == 422

    def test_respuesta_no_expone_datos_internos(self):
        """El listado de cuentas no debe exponer el saldo (datos sensibles)."""
        respuesta = client.get("/cuentas")
        for cuenta in respuesta.json():
            assert "saldo" not in cuenta, "El saldo no debe ser visible en el listado público"
