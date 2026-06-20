from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel

from middleware.auth_guard import get_current_user
from services.ai_engine import get_vdb, get_llm, super_search, generate_response, generate_chat_title
from services.supabase_client import get_supabase

router = APIRouter()


# ── Modelos ───────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatPayload(BaseModel):
    historial: list[ChatMessage]
    sesion_id: str


class HistorialUpdatePayload(BaseModel):
    historial: dict


class NuevaSesionPayload(BaseModel):
    pass


# ── Helper de validación de plan ──────────────────────────────────────────────
def _validar_acceso(datos: dict) -> bool:
    """Retorna True si el usuario tiene acceso activo (Pro o Trial)."""
    hoy = (datetime.now() - timedelta(hours=3)).date()

    if datos.get("plan") == "pro" and datos.get("vencimiento_pro"):
        venc = datetime.strptime(datos["vencimiento_pro"], "%Y-%m-%d").date()
        if hoy <= venc:
            return True

    if datos.get("vencimiento_trial"):
        venc = datetime.strptime(datos["vencimiento_trial"], "%Y-%m-%d").date()
        if hoy <= venc:
            return True

    return False


# ── Endpoint principal de chat ────────────────────────────────────────────────
@router.post("/")
async def chat_endpoint(
    payload: ChatPayload,
    auth: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    user = auth["user"]

    # Obtener datos actualizados del usuario
    db_res = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    if not db_res.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    datos = db_res.data[0]

    if not _validar_acceso(datos):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Tu período de acceso ha finalizado. Activá el Plan Pro para continuar.",
        )

    historial = [m.model_dump() for m in payload.historial]
    if not historial:
        raise HTTPException(status_code=400, detail="El historial no puede estar vacío.")

    query_usuario = historial[-1]["content"]
    historial_previo = historial[:-1]

    vdb = get_vdb()
    llm = get_llm()

    # Súper búsqueda dual
    contexto, _ = await super_search(query_usuario, historial_previo, llm, vdb)

    # Generar respuesta
    respuesta = await generate_response(contexto, historial)

    # Actualizar historial en Supabase
    historial_db = datos.get("historial", {})
    sesion = payload.sesion_id

    if sesion not in historial_db:
        historial_db[sesion] = []

    historial_db[sesion] = historial
    historial_db[sesion].append({"role": "assistant", "content": respuesta})

    # Auto-renombrado en la primera interacción
    nuevo_titulo = None
    if sesion.startswith("Consulta ") and len(historial_db[sesion]) == 2:
        try:
            nuevo_titulo = await generate_chat_title(historial[0]["content"])
            if nuevo_titulo in historial_db:
                nuevo_titulo += " (1)"
            historial_db[nuevo_titulo] = historial_db.pop(sesion)
        except Exception:
            nuevo_titulo = None

    supabase.table("usuarios").update({"historial": historial_db}).eq("email", user.email).execute()

    return {
        "ok": True,
        "respuesta": respuesta,
        "nuevo_titulo": nuevo_titulo,
        "historial": historial_db,
    }


# ── Chat invitado (sin autenticación, con límite de 5) ───────────────────────
@router.post("/guest")
async def chat_guest_endpoint(payload: ChatPayload):
    """
    Endpoint para usuarios invitados. El control de límite (5 consultas)
    se valida en el frontend con localStorage, pero aquí se puede agregar
    validación adicional por IP si se desea.
    """
    historial = [m.model_dump() for m in payload.historial]
    if not historial:
        raise HTTPException(status_code=400, detail="Historial vacío.")

    query_usuario = historial[-1]["content"]
    historial_previo = historial[:-1]

    vdb = get_vdb()
    llm = get_llm()

    contexto, _ = await super_search(query_usuario, historial_previo, llm, vdb)
    respuesta = await generate_response(contexto, historial)

    return {"ok": True, "respuesta": respuesta}


# ── Gestión del historial ─────────────────────────────────────────────────────
@router.post("/nueva-sesion")
async def nueva_sesion(auth: dict = Depends(get_current_user)):
    supabase = get_supabase()
    user = auth["user"]

    db_res = supabase.table("usuarios").select("historial").eq("email", user.email).execute()
    datos = db_res.data[0] if db_res.data else {}
    historial = datos.get("historial", {})

    nueva_id = f"Consulta {len(historial) + 1}"
    historial[nueva_id] = []

    supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()

    return {"ok": True, "sesion_id": nueva_id, "historial": historial}


@router.delete("/sesion/{sesion_id:path}")
async def eliminar_sesion(sesion_id: str, auth: dict = Depends(get_current_user)):
    supabase = get_supabase()
    user = auth["user"]

    db_res = supabase.table("usuarios").select("historial").eq("email", user.email).execute()
    datos = db_res.data[0] if db_res.data else {}
    historial = datos.get("historial", {})

    if sesion_id in historial:
        del historial[sesion_id]

    if not historial:
        historial["Nueva Consulta"] = []

    supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()

    ultima = list(historial.keys())[-1]
    return {"ok": True, "sesion_activa": ultima, "historial": historial}
