"""
liquidaciones.py

Router de consulta para el módulo de Liquidaciones del frontend.

Endpoints:
    GET /api/liquidaciones/canasta   -> valor de Canasta Básica de Crianza
    GET /api/liquidaciones/interes   -> cálculo de intereses sobre un monto
"""

import logging
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

logger = logging.getLogger("liquidaciones")

router = APIRouter(prefix="/api/liquidaciones", tags=["liquidaciones"])

TramoEdad = Literal["menor_1_anio", "1_a_3", "4_a_5", "6_a_12"]
TasaId = Literal["tasa_activa_bna", "tasa_pasiva_bna", "ipc"]

TRAMO_LABELS: dict[str, str] = {
    "menor_1_anio": "Menor de 1 año",
    "1_a_3": "1 a 3 años",
    "4_a_5": "4 a 5 años",
    "6_a_12": "6 a 12 años",
}

TASA_LABELS: dict[str, str] = {
    "tasa_activa_bna": "Tasa activa Banco Nación",
    "tasa_pasiva_bna": "Tasa pasiva Banco Nación",
    "ipc": "Índice de Precios al Consumidor (IPC)",
}

# ---------------------------------------------------------------------------
# BASE DE DATOS DE PRUEBA (Valores INDEC extraídos manualmente para la demo)
# ---------------------------------------------------------------------------
_MOCK_CANASTA_DB: dict[tuple[str, str], float] = {
    # === DATOS DE 2026 (Completos hasta Julio) ===
    ("2026-01", "menor_1_anio"): 476230.00,
    ("2026-01", "1_a_3"): 567124.00,
    ("2026-01", "4_a_5"): 483497.00,
    ("2026-01", "6_a_12"): 607848.00,
    ("2026-02", "menor_1_anio"): 480463.00,
    ("2026-02", "1_a_3"): 572590.00,
    ("2026-02", "4_a_5"): 490459.00,
    ("2026-02", "6_a_12"): 616484.00,
    ("2026-03", "menor_1_anio"): 494367.00,
    ("2026-03", "1_a_3"): 589099.00,
    ("2026-03", "4_a_5"): 504267.00,
    ("2026-03", "6_a_12"): 633857.00,
    ("2026-04", "menor_1_anio"): 511763.00,
    ("2026-04", "1_a_3"): 609574.00,
    ("2026-04", "4_a_5"): 520413.00,
    ("2026-04", "6_a_12"): 654221.00,
    ("2026-05", "menor_1_anio"): 520569.00,
    ("2026-05", "1_a_3"): 620125.00,
    ("2026-05", "4_a_5"): 529756.00,
    ("2026-05", "6_a_12"): 665950.00,
    ("2026-06", "menor_1_anio"): 529539.00,
    ("2026-06", "1_a_3"): 630926.00,
    ("2026-06", "4_a_5"): 539612.00,
    ("2026-06", "6_a_12"): 678308.00,
    ("2026-07", "menor_1_anio"): 545683.00,
    ("2026-07", "1_a_3"): 649935.00,
    ("2026-07", "4_a_5"): 554646.00,
    ("2026-07", "6_a_12"): 697268.00,

    # === ALGUNOS DATOS VIEJOS DE EJEMPLO PARA PROBAR ===
    ("2020-01", "menor_1_anio"): 17963.00,
    ("2020-01", "1_a_3"): 21208.00,
    ("2020-01", "4_a_5"): 17085.00,
    ("2020-01", "6_a_12"): 21425.00,
    
    ("2023-01", "menor_1_anio"): 74985.00,
    ("2023-01", "1_a_3"): 88446.00,
    ("2023-01", "4_a_5"): 70793.00,
    ("2023-01", "6_a_12"): 89156.00,
    
    ("2025-01", "menor_1_anio"): 393523.00,
    ("2025-01", "1_a_3"): 467113.00,
    ("2025-01", "4_a_5"): 390009.00,
    ("2025-01", "6_a_12"): 490614.00,
}

_MOCK_TASAS_DIARIAS: dict[str, float] = {
    "tasa_activa_bna": 0.0025,   # ~0.25% diario
    "tasa_pasiva_bna": 0.0012,   # ~0.12% diario
    "ipc": 0.0009,               # ~0.09% diario equivalente
}

class CanastaResponse(BaseModel):
    periodo: str
    tramo: str
    tramo_label: str
    valor: float

class InteresResponse(BaseModel):
    monto_base: float
    tasa_id: str
    tasa_label: str
    fecha_desde: date
    fecha_hasta: date
    dias: int
    interes: float
    monto_total: float

@router.get("/canasta", response_model=CanastaResponse)
async def obtener_valor_canasta(
    mes_anio: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="Formato YYYY-MM"),
    tramo_edad: TramoEdad = Query(...),
) -> CanastaResponse:
    clave = (mes_anio, tramo_edad)
    valor = _MOCK_CANASTA_DB.get(clave)

    if valor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No hay valor cargado de Canasta Básica de Crianza para "
                f"el período {mes_anio} y tramo {TRAMO_LABELS[tramo_edad]}."
            ),
        )

    return CanastaResponse(
        periodo=mes_anio,
        tramo=tramo_edad,
        tramo_label=TRAMO_LABELS[tramo_edad],
        valor=valor,
    )

@router.get("/interes", response_model=InteresResponse)
async def calcular_interes(
    monto: float = Query(..., gt=0),
    tasa_id: TasaId = Query(...),
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
) -> InteresResponse:
    if fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser posterior a fecha_hasta.",
        )

    dias = (fecha_hasta - fecha_desde).days
    tasa_diaria = _MOCK_TASAS_DIARIAS[tasa_id]

    interes = round(monto * tasa_diaria * dias, 2)
    monto_total = round(monto + interes, 2)

    return InteresResponse(
        monto_base=monto,
        tasa_id=tasa_id,
        tasa_label=TASA_LABELS[tasa_id],
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        dias=dias,
        interes=interes,
        monto_total=monto_total,
    )
