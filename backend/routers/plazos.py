"""
plazos.py

Calculadora de plazos procesales judiciales.
Saltea fines de semana, feriados nacionales y locales, y genera link a Google Calendar.
"""

import urllib.parse
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/plazos", tags=["plazos"])

# Diccionario base de feriados (Año 2026/2027 aproximado para pruebas)
FERIADOS_NACIONALES = [
    date(2026, 1, 1), date(2026, 3, 24), date(2026, 4, 2), date(2026, 5, 1),
    date(2026, 5, 25), date(2026, 6, 20), date(2026, 7, 9), 
    date(2026, 8, 17), # Paso Inmortalidad Gral San Martín (Visto en tu captura)
    date(2026, 10, 12), date(2026, 11, 20), date(2026, 12, 8), date(2026, 12, 25)
]

FERIADOS_LOCALES = {
    "Comodoro Rivadavia": [date(2026, 2, 23), date(2026, 12, 13)],
    "Trelew": [date(2026, 10, 20)],
    "Puerto Madryn": [date(2026, 7, 28)], # Aniversario Pto Madryn / Gesta Galesa
    "Gaiman": [date(2026, 8, 14)],        # Aniversario Gaiman (Visto en tu captura)
    "Rio Mayo": [date(2026, 8, 22)]       # Aniversario Río Mayo (Visto en tu captura)
}

# Suspensiones de términos judiciales (Ejemplo de las que vimos en tu captura)
SUSPENSIONES_JUDICIALES = [
    date(2026, 7, 27), date(2026, 7, 31), date(2026, 8, 6), 
    date(2026, 8, 13), date(2026, 8, 21)
]

class PlazoRequest(BaseModel):
    fecha_notificacion: date
    dias_habiles: int
    ciudad: str = "Comodoro Rivadavia"

class PlazoResponse(BaseModel):
    fecha_notificacion: date
    dias_habiles: int
    ciudad: str
    fecha_vencimiento: date
    google_calendar_url: str

@router.post("/", response_model=PlazoResponse)
def calcular_plazo(req: PlazoRequest):
    if req.dias_habiles <= 0:
        raise HTTPException(status_code=400, detail="Los días hábiles deben ser mayores a 0.")
    
    dias_contados = 0
    fecha_actual = req.fecha_notificacion
    
    # Unificamos todos los feriados aplicables para esa ciudad
    feriados_aplicables = set(FERIADOS_NACIONALES + FERIADOS_LOCALES.get(req.ciudad, []) + SUSPENSIONES_JUDICIALES)

    # Contamos hacia adelante salteando inhábiles
    while dias_contados < req.dias_habiles:
        fecha_actual += timedelta(days=1)
        # 0 = Lunes, ..., 4 = Viernes. Sábados (5) y Domingos (6) no se cuentan.
        if fecha_actual.weekday() < 5 and fecha_actual not in feriados_aplicables:
            dias_contados += 1
            
    # ARMADO DEL LINK DE GOOGLE CALENDAR (Evento configurado para las 08:00 AM)
    # Formato requerido por Google: YYYYMMDDTHHMMSSZ (En UTC. 11:00 UTC = 08:00 ARG)
    start_time = fecha_actual.strftime("%Y%m%dT110000Z") 
    end_time = fecha_actual.strftime("%Y%m%dT130000Z") # Termina 10:00 ARG
    
    titulo = urllib.parse.quote(f"⚠️ Vencimiento de Plazo ({req.dias_habiles} días)")
    detalles = urllib.parse.quote(f"Notificado el: {req.fecha_notificacion.strftime('%d/%m/%Y')}\n\nCalculado automáticamente por Chubut.IA ⚖️")
    
    gcal_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={titulo}&dates={start_time}/{end_time}&details={detalles}"
    
    return PlazoResponse(
        fecha_notificacion=req.fecha_notificacion,
        dias_habiles=req.dias_habiles,
        ciudad=req.ciudad,
        fecha_vencimiento=fecha_actual,
        google_calendar_url=gcal_url
    )
