from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from middleware.auth_guard import get_current_user
from services.pdf_generator import generar_pdf

router = APIRouter()


class ExportPayload(BaseModel):
    historial: list[dict]
    titulo: str


@router.post("/pdf")
async def export_pdf(
    payload: ExportPayload,
    auth: dict = Depends(get_current_user),
):
    """Genera y devuelve un PDF del historial de la conversación."""
    if not payload.historial:
        raise HTTPException(status_code=400, detail="El historial está vacío.")

    try:
        pdf_bytes = generar_pdf(payload.historial, payload.titulo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar el PDF: {str(e)}")

    nombre_archivo = f"Reporte_{payload.titulo[:40].replace(' ', '_')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.post("/pdf/guest")
async def export_pdf_guest(payload: ExportPayload):
    """Exportación de PDF para usuarios invitados (sin autenticación requerida)."""
    if not payload.historial:
        raise HTTPException(status_code=400, detail="El historial está vacío.")

    pdf_bytes = generar_pdf(payload.historial, payload.titulo)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="Reporte_ChubutIA.pdf"'},
    )
