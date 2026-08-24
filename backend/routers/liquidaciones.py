"""
liquidaciones.py

Router de consulta para el módulo de Liquidaciones del frontend.
Lee automáticamente la Canasta Básica desde Excel y las Tasas (BNA y Chubut) desde PDFs.
"""

import logging
import os
import re
from datetime import date, timedelta, datetime
from typing import Literal

import pandas as pd
import PyPDF2
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

logger = logging.getLogger("liquidaciones")

router = APIRouter(prefix="/api/liquidaciones", tags=["liquidaciones"])

TramoEdad = Literal["menor_1_anio", "1_a_3", "4_a_5", "6_a_12"]
TasaId = Literal["tasa_activa_bna", "tasa_chubut_uss"]

TRAMO_LABELS: dict[str, str] = {
    "menor_1_anio": "Menor de 1 año",
    "1_a_3": "1 a 3 años",
    "4_a_5": "4 a 5 años",
    "6_a_12": "6 a 12 años",
}

TASA_LABELS: dict[str, str] = {
    "tasa_activa_bna": "Tasa activa Banco Nación",
    "tasa_chubut_uss": "Tasa activa Banco Chubut U$S",
}

def buscar_archivo(nombre_archivo):
    rutas_posibles = [
        nombre_archivo,
        os.path.join("backend", nombre_archivo),
        os.path.join(os.path.dirname(__file__), "..", nombre_archivo),
        os.path.join(os.path.dirname(__file__), "..", "..", nombre_archivo)
    ]
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            return ruta
    return nombre_archivo

def cargar_canasta():
    db = {}
    ruta = buscar_archivo("serie_canasta_crianza.xlsx")
    try:
        df = pd.read_excel(ruta, sheet_name=0, header=None)
        df[0] = df[0].ffill()
        meses_es = {
            "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04", "Mayo": "05", "Junio": "06",
            "Julio": "07", "Agosto": "08", "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
        }
        for idx, row in df.iloc[7:].iterrows():
            if pd.isna(row[1]): continue
            try:
                year = int(row[0])
                month = meses_es.get(str(row[1]).strip())
                if not month: continue
                period = f"{year}-{month}"
                db[(period, "menor_1_anio")] = round(float(row[4]), 2)
                db[(period, "1_a_3")] = round(float(row[7]), 2)
                db[(period, "4_a_5")] = round(float(row[10]), 2)
                db[(period, "6_a_12")] = round(float(row[13]), 2)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error cargando Excel de Canasta: {e}")
    return db

def cargar_tasas(nombre_pdf):
    tasas = []
    ruta = buscar_archivo(nombre_pdf)
    try:
        reader = PyPDF2.PdfReader(ruta)
        texto = "".join(page.extract_text() + "\n" for page in reader.pages)
        patron = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4}|vigente)\s+([\d\.]+)%')
        for match in patron.findall(texto):
            desde_str, hasta_str, tasa_str = match
            desde_date = datetime.strptime(desde_str, "%d/%m/%Y").date()
            if hasta_str.lower() == 'vigente':
                hasta_date = date.today() + timedelta(days=365)
            else:
                hasta_date = datetime.strptime(hasta_str, "%d/%m/%Y").date()
            tasas.append({
                "desde": desde_date, 
                "hasta": hasta_date, 
                "tasa_mensual": float(tasa_str)
            })
    except Exception as e:
        logger.error(f"Error cargando PDF {nombre_pdf}: {e}")
    return tasas

# Cargamos todo a memoria al iniciar el servidor
CANASTA_DB = cargar_canasta()
TASAS_BNA = cargar_tasas("reporteTasa.pdf")
TASAS_CHUBUT = cargar_tasas("reporteTasa chubut.pdf")

class CanastaResponse(BaseModel):
    periodo: str
    tramo: str
    tramo_label: str
    valor: float

class InteresRequest(BaseModel):
    monto: float
    tasa: TasaId
    desde: date
    hasta: date

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
    mes_anio: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    tramo_edad: TramoEdad = Query(...),
) -> CanastaResponse:
    clave = (mes_anio, tramo_edad)
    valor = CANASTA_DB.get(clave)
    if valor is None:
        raise HTTPException(status_code=404, detail="Período no encontrado.")
    return CanastaResponse(
        periodo=mes_anio, tramo=tramo_edad,
        tramo_label=TRAMO_LABELS[tramo_edad], valor=valor
    )

@router.post("/interes", response_model=InteresResponse)
async def calcular_interes(req: InteresRequest) -> InteresResponse:
    if req.desde > req.hasta:
        raise HTTPException(status_code=400, detail="Fechas inválidas.")
    
    # Seleccionamos qué base de tasas usar según lo que eligió el usuario
    if req.tasa == "tasa_chubut_uss":
        base_tasas = TASAS_CHUBUT
    else:
        base_tasas = TASAS_BNA

    interes_acumulado = 0.0
    dias_totales = (req.hasta - req.desde).days
    
    for i in range(dias_totales):
        dia_actual = req.desde + timedelta(days=i)
        tasa_mensual_vigente = 5.0
        
        for periodo in base_tasas:
            if periodo["desde"] <= dia_actual <= periodo["hasta"]:
                tasa_mensual_vigente = periodo["tasa_mensual"]
                break
                
        tasa_diaria = (tasa_mensual_vigente / 100.0) / 30.0
        interes_acumulado += req.monto * tasa_diaria

    interes_redondeado = round(interes_acumulado, 2)
    monto_total = round(req.monto + interes_redondeado, 2)

    return InteresResponse(
        monto_base=req.monto,
        tasa_id=req.tasa,
        tasa_label=TASA_LABELS.get(req.tasa, req.tasa),
        fecha_desde=req.desde,
        fecha_hasta=req.hasta,
        dias=dias_totales,
        interes=interes_redondeado,
        monto_total=monto_total,
    )
