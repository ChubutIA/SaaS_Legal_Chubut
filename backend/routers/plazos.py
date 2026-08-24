"""
plazos.py

Calculadora de plazos procesales judiciales con detalle diario para calendario visual.
"""

import urllib.parse
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/plazos", tags=["plazos"])

# Feriados Nacionales (2026 aproximado)
FERIADOS_NACIONALES = {
    date(2026, 1, 1): "Año Nuevo",
    date(2026, 3, 24): "Día de la Memoria",
    date(2026, 4, 2): "Día del Veterano y Malvinas",
    date(2026, 5, 1): "Día del Trabajador",
    date(2026, 5, 25): "Revolución de Mayo",
    date(2026, 6, 20): "Paso a la Inmortalidad Gral. Belgrano",
    date(2026, 7, 9): "Día de la Independencia",
    date(2026, 8, 17): "Paso a la Inmortalidad Gral. San Martín",
    date(2026, 10, 12): "Día del Respeto a la Diversidad Cultural",
    date(2026, 11, 20): "Día de la Soberanía Nacional",
    date(2026, 12, 8): "Inmaculada Concepción",
    date(2026, 12, 25): "Navidad"
}

# Feriados Locales (2026)
FERIADOS_LOCALES = {
    "Comodoro Rivadavia": {date(2026, 2, 23): "Aniversario Comodoro", date(2026, 12, 13): "Día del Petróleo"},
    "Trelew": {date(2026, 10, 20): "Aniversario Trelew"},
    "Puerto Madryn": {date(2026, 7, 28): "Aniversario Puerto Madryn / Gesta Galesa"},
    "Gaiman": {date(2026, 8, 14): "Aniversario Gaiman"},
    "Rio Mayo": {date(2026, 8, 22): "Aniversario Río Mayo"}
}

# Suspensiones Judiciales
SUSPENSIONES_JUDICIALES = {
    date(2026, 7, 27): "Suspensión de términos",
    date(2026, 7, 31): "Suspensión de términos",
    date(2026, 8, 6): "Suspensión de términos",
    date(2026, 8, 13): "Suspensión de términos",
    date(2026, 8, 21): "Suspensión de términos"
}

class PlazoRequest(BaseModel):
    fecha_notificacion: date
    dias_habiles: int
    ciudad: str = "Comodoro Rivadavia"

class DiaDetalle(BaseModel):
    fecha: date
    tipo: str  # "inicio", "vigencia", "inhabíl", "vencimiento"
    descripcion: str

class PlazoResponse(BaseModel):
    fecha_notificacion: date
    dias_habiles: int
    ciudad: str
    fecha_vencimiento: date
    google_calendar_url: str
    detalle_calendario: List[DiaDetalle]

@router.post("/", response_model=PlazoResponse)
def calcular_plazo(req: PlazoRequest):
    if req.dias_habiles <= 0:
        raise HTTPException(status_code=400, detail="Los días hábiles deben ser mayores a 0.")
    
    feriados_locales_ciudad = FERIADOS_LOCALES.get(req.ciudad, {})
    
    dias_contados = 0
    fecha_actual = req.fecha_notificacion
    detalle_calendario = []
    
    # Agregamos el día de inicio
    detalle_calendario.append(DiaDetalle(
        fecha=fecha_actual, 
        tipo="inicio", 
        descripcion="Inicio del plazo (Notificación)"
    ))
    
    while dias_contados < req.dias_habiles:
        fecha_actual += timedelta(days=1)
        weekday = fecha_actual.weekday()
        
        # Revisamos qué tipo de día es
        if weekday == 5:
            detalle_calendario.append(DiaDetalle(fecha=fecha_actual, tipo="inhabíl", descripcion="Sábado"))
        elif weekday == 6:
            detalle_calendario.append(DiaDetalle(fecha=fecha_actual, tipo="inhabíl", descripcion="Domingo"))
        elif fecha_actual in FERIADOS_NACIONALES:
            detalle_calendario.append(DiaDetalle(fecha=fecha_actual, tipo="inhabíl", descripcion=FERIADOS_NACIONALES[fecha_actual]))
        elif fecha_actual in feriados_locales_ciudad:
            detalle_calendario.append(DiaDetalle(fecha=fecha_actual, tipo="inhabíl", descripcion=feriados_locales_ciudad[fecha_actual]))
        elif fecha_actual in SUSPENSIONES_JUDICIALES:
            detalle_calendario.append(DiaDetalle(fecha=fecha_actual, tipo="inhabíl", descripcion=SUSPENSIONES_JUDICIALES[fecha_actual]))
        else:
            # Es un día hábil
            dias_contados += 1
            if dias_contados == req.dias_habiles:
                detalle_calendario.append(DiaDetalle(fecha=fecha_actual, tipo="vencimiento", descripcion="Vencimiento del Plazo (Primeras 2 hs)"))
            else:
                detalle_calendario.append(DiaDetalle(fecha=fecha_actual, tipo="vigencia", descripcion="Plazo en vigencia"))
            
    # ARMADO DEL LINK DE GOOGLE CALENDAR
    start_time = fecha_actual.strftime("%Y%m%dT110000Z") 
    end_time = fecha_actual.strftime("%Y%m%dT130000Z") 
    titulo = urllib.parse.quote(f"⚠️ Vencimiento de Plazo ({req.dias_habiles} días)")
    detalles = urllib.parse.quote(f"Notificado el: {req.fecha_notificacion.strftime('%d/%m/%Y')}\nJurisdicción: {req.ciudad}\n\nCalculado por Chubut.IA ⚖️")
    gcal_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={titulo}&dates={start_time}/{end_time}&details={detalles}"
    
    return PlazoResponse(
        fecha_notificacion=req.fecha_notificacion,
        dias_habiles=req.dias_habiles,
        ciudad=req.ciudad,
        fecha_vencimiento=fecha_actual,
        google_calendar_url=gcal_url,
        detalle_calendario=detalle_calendario
    )
