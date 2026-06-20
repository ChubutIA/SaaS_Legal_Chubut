import os
import io

from fastapi import APIRouter, UploadFile, File, HTTPException
from openai import OpenAI
import PyPDF2

router = APIRouter()


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no configurada.")
    return OpenAI(api_key=api_key)


# ── Endpoint: extracción de texto de PDF/TXT ──────────────────────────────────
@router.post("/document")
async def upload_document(file: UploadFile = File(...)):
    """
    Recibe un PDF o TXT y devuelve el texto extraído.
    El frontend usará este texto para incluirlo como contexto al enviar
    el mensaje al endpoint /api/chat, ocultando el contenido masivo visualmente.
    """
    nombre = file.filename or "archivo"
    contenido = await file.read()

    texto_extraido = ""

    if nombre.lower().endswith(".pdf"):
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(contenido))
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    texto_extraido += txt + "\n"
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Error al leer el PDF: {str(e)}")

    elif nombre.lower().endswith(".txt"):
        try:
            texto_extraido = contenido.decode("utf-8", errors="ignore")
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Error al leer el TXT: {str(e)}")

    else:
        raise HTTPException(
            status_code=415,
            detail="Formato no soportado. Solo se aceptan archivos PDF y TXT.",
        )

    if not texto_extraido.strip():
        raise HTTPException(
            status_code=422,
            detail="No se pudo extraer texto del archivo. Puede ser un PDF escaneado.",
        )

    return {
        "ok": True,
        "nombre": nombre,
        "texto": texto_extraido.strip(),
        "longitud": len(texto_extraido),
    }


# ── Endpoint: transcripción de audio con Whisper ──────────────────────────────
@router.post("/audio")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Recibe un archivo de audio y lo transcribe usando OpenAI Whisper-1.
    """
    client = _get_openai_client()
    contenido = await file.read()
    nombre = file.filename or "audio.wav"

    try:
        audio_buffer = io.BytesIO(contenido)
        audio_buffer.name = nombre

        transcripcion = client.audio.transcriptions.create(
            model="whisper-1",
            file=(nombre, audio_buffer, file.content_type or "audio/wav"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en transcripción: {str(e)}")

    return {"ok": True, "transcripcion": transcripcion.text}
