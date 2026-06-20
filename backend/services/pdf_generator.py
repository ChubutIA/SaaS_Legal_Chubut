from datetime import datetime, timedelta
from fpdf import FPDF


def generar_pdf(historial: list[dict], titulo_chat: str) -> bytes:
    """
    Genera un PDF limpio (sin emojis) del historial de chat.
    Filtra el bloque oculto '--- DOCUMENTO ADJUNTO PARA ANALIZAR ---'.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Encabezado ──────────────────────────────────────────────────────────
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Reporte de Jurisprudencia - Chubut.IA", ln=True, align="C")

    pdf.set_font("helvetica", "", 10)
    fecha_local = (datetime.now() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 8, f"Generado el: {fecha_local}", ln=True, align="C")
    pdf.ln(6)

    # ── Título del chat ──────────────────────────────────────────────────────
    pdf.set_font("helvetica", "B", 12)
    titulo_limpio = _limpiar(titulo_chat)
    pdf.multi_cell(0, 8, f"Consulta: {titulo_limpio}")
    pdf.ln(4)

    # ── Mensajes ─────────────────────────────────────────────────────────────
    for msg in historial:
        rol = "Usuario" if msg["role"] == "user" else "Chubut.IA"

        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 8, f"{rol}:", ln=True)

        pdf.set_font("helvetica", "", 9)
        contenido = msg["content"]

        # Ocultar bloque de documento adjunto en el PDF
        if "--- DOCUMENTO ADJUNTO PARA ANALIZAR ---" in contenido:
            contenido = contenido.split("--- DOCUMENTO ADJUNTO PARA ANALIZAR ---")[0].strip()
            contenido += "\n\n[Documento adjunto procesado por la IA]"

        # Eliminar Markdown básico y emojis
        contenido = contenido.replace("**", "").replace("__", "")
        texto_limpio = _limpiar(contenido)

        pdf.multi_cell(0, 5, texto_limpio)
        pdf.ln(3)

    return bytes(pdf.output())


def _limpiar(texto: str) -> str:
    """Convierte a latin-1 ignorando caracteres incompatibles (emojis, unicode especial)."""
    return texto.encode("latin-1", "ignore").decode("latin-1")
