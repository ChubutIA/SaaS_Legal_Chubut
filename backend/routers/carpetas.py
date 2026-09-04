from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.supabase_client import get_supabase

router = APIRouter(
    prefix="/api/carpetas",
    tags=["Carpetas"]
)

# Modelos de datos para recibir del Frontend
class CarpetaCreate(BaseModel):
    usuario_id: int
    nombre: str
    descripcion: str = ""

@router.post("/")
async def crear_carpeta(carpeta: CarpetaCreate):
    supabase = get_supabase()
    try:
        # Guardamos la carpeta en Supabase
        data = supabase.table("carpetas").insert({
            "usuario_id": carpeta.usuario_id,
            "nombre": carpeta.nombre,
            "descripcion": carpeta.descripcion
        }).execute()
        
        return {"mensaje": "Carpeta creada exitosamente", "carpeta": data.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear carpeta: {str(e)}")

@router.get("/{usuario_id}")
async def listar_carpetas(usuario_id: int):
    supabase = get_supabase()
    try:
        # Traemos todas las carpetas de este usuario ordenadas por las más nuevas
        data = supabase.table("carpetas").select("*").eq("usuario_id", usuario_id).order("created_at", desc=True).execute()
        return {"carpetas": data.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener carpetas: {str(e)}")

@router.get("/{carpeta_id}/documentos")
async def listar_documentos(carpeta_id: str):
    supabase = get_supabase()
    try:
        # Traemos todos los archivos guardados adentro de esta carpeta
        data = supabase.table("documentos_carpeta").select("*").eq("carpeta_id", carpeta_id).order("created_at", desc=False).execute()
        return {"documentos": data.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener documentos: {str(e)}")
