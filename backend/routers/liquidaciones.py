"""
liquidaciones.py

Router de consulta para el módulo de Liquidaciones del frontend.

Endpoints:
    GET /api/liquidaciones/canasta   -> valor de Canasta Básica de Crianza
    GET /api/liquidaciones/interes   -> cálculo de intereses sobre un monto

Ambos endpoints están simulados (datos mock / fórmulas placeholder) para que
liquidaciones.js pueda integrarse ya mismo. Reemplazá las secciones marcadas
con TODO por las consultas reales a Supabase / tasas del BCRA cuando estén
disponibles.
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
# TODO: reemplazar por la consulta real a Supabase
# (tabla canasta_basica_crianza cargada por admin_scraper.py)
# ---------------------------------------------------------------------------
_MOCK_CANASTA_DB: dict[tuple[str, str], float] = {
    ("2026-06", "menor_1_anio"): 500000.50,
    ("2026-06", "1_a_3"): 480000.00,
    ("2026-06", "4_a_5"): 460000.00,
    ("2026-06", "6_a_12"): 440000.00,
    ("2026-07", "menor_1_anio"): 545683.00,
    ("2026-07", "1_a_3"): 520000.00,
    ("2026-07", "4_a_5"): 500000.00,
    ("2026-07", "6_a_12"): 470000.00,
}

# TODO: reemplazar por la tasa diaria real (scraping BCRA / tabla propia).
# Estos son valores placeholder solo para poder calcular algo mientras
# se conecta la fuente real.
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
    """
    Devuelve el valor de la Canasta Básica de Crianza para un período y
    tramo de edad específicos.

    TODO: reemplazar el diccionario mock por:
        resp = (
            supabase.table("canasta_basica_crianza")
            .select("valor")
            .eq("periodo", mes_anio)
            .eq("tramo", tramo_edad)
            .single()
            .execute()
        )
    """
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
    """
    Calcula el interés simple sobre `monto` entre `fecha_desde` y
    `fecha_hasta`, usando la tasa diaria correspondiente a `tasa_id`.

    TODO: reemplazar _MOCK_TASAS_DIARIAS por la tasa real vigente en cada
    día del período (lo correcto es acumular día a día si la tasa varía,
    no aplicar una tasa fija promedio como acá).
    """
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
"""
liquidaciones.py

Router de consulta para el módulo de Liquidaciones del frontend.

Endpoints:
    GET /api/liquidaciones/canasta   -> valor de Canasta Básica de Crianza
    GET /api/liquidaciones/interes   -> cálculo de intereses sobre un monto

Ambos endpoints están simulados (datos mock / fórmulas placeholder) para que
liquidaciones.js pueda integrarse ya mismo. Reemplazá las secciones marcadas
con TODO por las consultas reales a Supabase / tasas del BCRA cuando estén
disponibles.
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
# TODO: reemplazar por la consulta real a Supabase
# (tabla canasta_basica_crianza cargada por admin_scraper.py)
# ---------------------------------------------------------------------------
_MOCK_CANASTA_DB: dict[tuple[str, str], float] = {
    ("2026-06", "menor_1_anio"): 500000.50,
    ("2026-06", "1_a_3"): 480000.00,
    ("2026-06", "4_a_5"): 460000.00,
    ("2026-06", "6_a_12"): 440000.00,
    ("2026-07", "menor_1_anio"): 545683.00,
    ("2026-07", "1_a_3"): 520000.00,
    ("2026-07", "4_a_5"): 500000.00,
    ("2026-07", "6_a_12"): 470000.00,
}

# TODO: reemplazar por la tasa diaria real (scraping BCRA / tabla propia).
# Estos son valores placeholder solo para poder calcular algo mientras
# se conecta la fuente real.
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
    """
    Devuelve el valor de la Canasta Básica de Crianza para un período y
    tramo de edad específicos.

    TODO: reemplazar el diccionario mock por:
        resp = (
            supabase.table("canasta_basica_crianza")
            .select("valor")
            .eq("periodo", mes_anio)
            .eq("tramo", tramo_edad)
            .single()
            .execute()
        )
    """
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
    """
    Calcula el interés simple sobre `monto` entre `fecha_desde` y
    `fecha_hasta`, usando la tasa diaria correspondiente a `tasa_id`.

    TODO: reemplazar _MOCK_TASAS_DIARIAS por la tasa real vigente en cada
    día del período (lo correcto es acumular día a día si la tasa varía,
    no aplicar una tasa fija promedio como acá).
    """
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
