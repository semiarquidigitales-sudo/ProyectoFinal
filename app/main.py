"""
FinTech Nova - API Principal
Sesión 14: CI/CD y DevSecOps

Esta API simula operaciones financieras básicas para demostrar
el pipeline CI/CD con controles de seguridad integrados.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime

# ─── Inicialización de la aplicación ────────────────────────────────────────
app = FastAPI(
    title="FinTech Nova API",
    description="API de operaciones financieras - Demo CI/CD DevSecOps",
    version="1.0.0"
)

# ─── Base de datos en memoria (solo para demo) ───────────────────────────────
db_cuentas = {
    "ACC-001": {"titular": "María García",    "saldo": 5000.00, "moneda": "USD"},
    "ACC-002": {"titular": "Carlos López",    "saldo": 3200.50, "moneda": "USD"},
    "ACC-003": {"titular": "Ana Martínez",    "saldo": 12800.75, "moneda": "USD"},
}
db_transacciones = []

# ─── Modelos de datos ────────────────────────────────────────────────────────
class Transferencia(BaseModel):
    cuenta_origen: str = Field(..., example="ACC-001")
    cuenta_destino: str = Field(..., example="ACC-002")
    monto: float = Field(..., gt=0, example=100.00)
    descripcion: Optional[str] = Field(None, example="Pago de servicios")

class RespuestaTransferencia(BaseModel):
    id_transaccion: str
    estado: str
    timestamp: str
    monto: float
    cuenta_origen: str
    cuenta_destino: str

# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/")
def raiz():
    """Endpoint de bienvenida - verifica que la API está activa."""
    return {
        "servicio": "FinTech Nova API",
        "version": "1.0.0",
        "estado": "operacional",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
def health_check():
    """Health check - usado por el pipeline para verificar que la app inicia."""
    return {
        "status": "healthy",
        "cuentas_registradas": len(db_cuentas),
        "transacciones_procesadas": len(db_transacciones)
    }

@app.get("/cuentas/{id_cuenta}")
def obtener_cuenta(id_cuenta: str):
    """Obtiene información de una cuenta por su ID."""
    if id_cuenta not in db_cuentas:
        raise HTTPException(status_code=404, detail=f"Cuenta {id_cuenta} no encontrada")
    cuenta = db_cuentas[id_cuenta].copy()
    cuenta["id"] = id_cuenta
    return cuenta

@app.get("/cuentas")
def listar_cuentas():
    """Lista todas las cuentas disponibles (sin datos sensibles)."""
    return [
        {"id": k, "titular": v["titular"], "moneda": v["moneda"]}
        for k, v in db_cuentas.items()
    ]

@app.post("/transferencias", response_model=RespuestaTransferencia, status_code=201)
def crear_transferencia(transferencia: Transferencia):
    """
    Procesa una transferencia entre dos cuentas.
    Valida saldo suficiente y existencia de cuentas.
    """
    # Validar que las cuentas existen
    if transferencia.cuenta_origen not in db_cuentas:
        raise HTTPException(status_code=404, detail=f"Cuenta origen {transferencia.cuenta_origen} no encontrada")
    if transferencia.cuenta_destino not in db_cuentas:
        raise HTTPException(status_code=404, detail=f"Cuenta destino {transferencia.cuenta_destino} no encontrada")

    # Validar saldo suficiente
    saldo_origen = db_cuentas[transferencia.cuenta_origen]["saldo"]
    if saldo_origen < transferencia.monto:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo insuficiente. Disponible: ${saldo_origen:.2f}, Requerido: ${transferencia.monto:.2f}"
        )

    # Procesar la transferencia
    db_cuentas[transferencia.cuenta_origen]["saldo"] -= transferencia.monto
    db_cuentas[transferencia.cuenta_destino]["saldo"]  += transferencia.monto

    # Registrar la transacción
    id_tx = f"TX-{str(uuid.uuid4())[:8].upper()}"
    timestamp = datetime.utcnow().isoformat()
    db_transacciones.append({
        "id": id_tx,
        "origen": transferencia.cuenta_origen,
        "destino": transferencia.cuenta_destino,
        "monto": transferencia.monto,
        "descripcion": transferencia.descripcion,
        "timestamp": timestamp
    })

    return RespuestaTransferencia(
        id_transaccion=id_tx,
        estado="completada",
        timestamp=timestamp,
        monto=transferencia.monto,
        cuenta_origen=transferencia.cuenta_origen,
        cuenta_destino=transferencia.cuenta_destino
    )

@app.get("/transacciones")
def listar_transacciones():
    """Lista el historial de transacciones procesadas."""
    return {"total": len(db_transacciones), "transacciones": db_transacciones}
