"""
ingest_fallos_v2.py
================================================================
Reemplaza a crear_base_nueva.py + actualizar_base.py + reparador_base.py.

Lee los .txt que generan robot_chubut.py / Robot_actualizador.py
(carátula + separador "TEXTO COMPLETO DEL FALLO" + cuerpo + línea
"ENLACE OFICIAL PARA VER EL FALLO ORIGINAL: ..."), extrae metadata
de forma consistente (una sola lógica, no dos como antes), clasifica
la materia con un LLM, chunkea, embebe y sube todo a Supabase.

Es IDEMPOTENTE: podés correrlo cada vez que el scraper junte fallos
nuevos — hace upsert por (fallo_id, chunk_index), así que no duplica
ni necesita un paso de "reparación" posterior.

INSTALAR
--------
    pip install openai supabase langchain-text-splitters python-dotenv

VARIABLES DE ENTORNO (poné esto en un .env, NUNCA en el código)
-----------------------------------------------------------------
    OPENAI_API_KEY=...
    SUPABASE_URL=...
    SUPABASE_KEY=...   (service_role key, para poder hacer upsert)

USO
---
    python ingest_fallos_v2.py ./mi_base_legal
"""

import sys
import os
import re
import json
import hashlib

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"   # debe coincidir con ai_engine.py
CLASIFICADOR_MODEL = "gpt-4o-mini"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
BATCH_EMBEDDING = 96
BATCH_UPSERT = 50

SEPARADOR_CUERPO = re.compile(r"={10,}\s*\nTEXTO COMPLETO DEL FALLO\s*\n={10,}\s*\n*", re.IGNORECASE)
PATRON_LINK = re.compile(r"ENLACE OFICIAL PARA VER EL FALLO ORIGINAL:\s*(\S+)", re.IGNORECASE)
PATRON_FECHA_FIRMA = re.compile(r"Fecha de firma:\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})", re.IGNORECASE)

MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "setiembre": "09", "octubre": "10",
    "noviembre": "11", "diciembre": "12",
}

MATERIAS_VALIDAS = [
    "laboral", "contencioso_administrativo", "civil", "penal",
    "familia", "comercial", "previsional", "otros",
]

PROMPT_MATERIA = """\
Clasificá este fallo judicial de Chubut en UNA sola de estas materias:
laboral, contencioso_administrativo, civil, penal, familia, comercial, previsional, otros

Respondé ÚNICAMENTE la palabra clave, sin explicación ni puntuación.

Carátula: {caratula}

Primeras líneas del fallo:
{extracto}"""


def get_openai() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def get_supabase():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


# ── 1. Parseo del .txt del scraper ───────────────────────────────────────────
def parsear_archivo(ruta: str) -> dict | None:
    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
        texto = f.read()

    partes = SEPARADOR_CUERPO.split(texto, maxsplit=1)
    if len(partes) != 2:
        print(f"  ⚠️  {os.path.basename(ruta)}: no encontré el separador 'TEXTO COMPLETO DEL FALLO', lo salteo.")
        return None

    caratula = partes[0].strip()
    cuerpo_y_footer = partes[1]

    match_link = PATRON_LINK.search(cuerpo_y_footer)
    link_pdf = match_link.group(1).strip() if match_link else None
    if not link_pdf or link_pdf.lower() == "link no disponible":
        link_pdf = "https://apps1cloud.juschubut.gov.ar/Eureka/"

    # El cuerpo real es todo lo que está antes de la línea del enlace/separador final
    cuerpo = PATRON_LINK.split(cuerpo_y_footer)[0]
    cuerpo = re.sub(r"={10,}\s*$", "", cuerpo).strip()

    fecha = _extraer_fecha(cuerpo, ruta)

    if not caratula or len(cuerpo) < 50:
        print(f"  ⚠️  {os.path.basename(ruta)}: carátula o cuerpo vacíos/demasiado cortos, lo salteo.")
        return None

    fallo_id = os.path.splitext(os.path.basename(ruta))[0]

    return {
        "fallo_id": fallo_id,
        "caratula": caratula,
        "fecha": fecha,
        "link_pdf": link_pdf,
        "texto_completo": cuerpo,
    }


def _extraer_fecha(cuerpo: str, ruta: str) -> str | None:
    """
    Prioriza 'Fecha de firma:' (inequívoca). Si no está, busca fechas SOLO
    en el último tramo del texto (donde suele estar la firma/cierre), para
    no agarrar una fecha de un fallo citado dentro del cuerpo. Si nada de
    eso aparece, cae al año detectado en el nombre de archivo.
    """
    m = PATRON_FECHA_FIRMA.search(cuerpo)
    if m:
        dia, mes, anio = m.groups()
        return f"{anio}-{int(mes):02d}-{int(dia):02d}"

    cola = cuerpo[-1200:]  # últimos ~1200 caracteres: zona típica de firma/cierre

    fechas_num = re.findall(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2})\b", cola)
    if fechas_num:
        dia, mes, anio = fechas_num[-1]
        try:
            return f"{anio}-{int(mes):02d}-{int(dia):02d}"
        except ValueError:
            pass

    patron_texto = r"\b(\d{1,2})\s+(?:días\s+del\s+mes\s+de\s+|de\s+)?([a-zA-Z]+)\s+(?:del\s+año\s+|de\s+año\s+|del\s+|de\s+)?(20\d{2})\b"
    for dia, mes_texto, anio in reversed(re.findall(patron_texto, cola, re.IGNORECASE)):
        mes_num = MESES.get(mes_texto.lower())
        if mes_num:
            try:
                return f"{anio}-{mes_num}-{int(dia):02d}"
            except ValueError:
                continue

    match_anio = re.search(r"(20\d{2})", os.path.basename(ruta))
    if match_anio:
        return f"{match_anio.group(1)}-01-01"  # fecha aproximada; mejor que nada para ordenar/filtrar

    return None


# ── 2. Clasificación de materia ──────────────────────────────────────────────
def clasificar_materia(fallo: dict, client: OpenAI) -> str:
    prompt = PROMPT_MATERIA.format(
        caratula=fallo["caratula"][:300],
        extracto=fallo["texto_completo"][:1500],
    )
    try:
        resp = client.chat.completions.create(
            model=CLASIFICADOR_MODEL,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        materia = resp.choices[0].message.content.strip().lower()
        return materia if materia in MATERIAS_VALIDAS else "otros"
    except Exception as e:
        print(f"  ⚠️  Error clasificando materia de {fallo['fallo_id']}: {e}")
        return "otros"


# ── 3. Chunking con contexto pegado ──────────────────────────────────────────
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\nCONSIDERANDO", "\nRESUELVE", "\nVISTOS", "\n\n", "\n", ". ", " ", ""],
)


def chunkear_fallo(fallo: dict) -> list[dict]:
    partes = _splitter.split_text(fallo["texto_completo"])
    encabezado = (
        f"Fallo: {fallo['caratula']}. Materia: {fallo['materia']}. "
        f"Fecha: {fallo.get('fecha') or 'N/D'}.\n---\n"
    )
    filas = []
    for i, parte in enumerate(partes):
        filas.append({
            "fallo_id": fallo["fallo_id"],
            "caratula": fallo["caratula"],
            "materia": fallo["materia"],
            "juzgado": None,
            "fecha": fallo.get("fecha"),
            "link_pdf": fallo["link_pdf"],
            "chunk_index": i,
            "total_chunks": len(partes),
            "content": parte,
            "content_indexado": encabezado + parte,
        })
    return filas


# ── 4. Embeddings + upsert ───────────────────────────────────────────────────
def embeber_filas(filas: list[dict], client: OpenAI) -> None:
    for inicio in range(0, len(filas), BATCH_EMBEDDING):
        lote = filas[inicio:inicio + BATCH_EMBEDDING]
        textos = [f["content_indexado"] for f in lote]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=textos)
        for fila, dato in zip(lote, resp.data):
            fila["embedding"] = dato.embedding
        print(f"    embebidos {inicio + len(lote)}/{len(filas)} chunks")


def subir_filas(filas: list[dict], supabase) -> None:
    for inicio in range(0, len(filas), BATCH_UPSERT):
        lote = filas[inicio:inicio + BATCH_UPSERT]
        supabase.table("fallos_chunks").upsert(lote, on_conflict="fallo_id,chunk_index").execute()
        print(f"    subidos {inicio + len(lote)}/{len(filas)} chunks")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) != 2:
        print("Uso: python ingest_fallos_v2.py <carpeta_con_txt>")
        sys.exit(1)

    carpeta = sys.argv[1]
    openai_client = get_openai()
    supabase = get_supabase()

    archivos = [f for f in os.listdir(carpeta) if f.endswith(".txt")]
    print(f"📄 {len(archivos)} archivos .txt encontrados en {carpeta}")

    fallos_ok = []
    for nombre in archivos:
        ruta = os.path.join(carpeta, nombre)
        fallo = parsear_archivo(ruta)
        if fallo:
            fallos_ok.append(fallo)

    print(f"✅ {len(fallos_ok)} fallos parseados correctamente ({len(archivos) - len(fallos_ok)} salteados)")

    print("⚖️  Clasificando materia de cada fallo...")
    for i, fallo in enumerate(fallos_ok, start=1):
        fallo["materia"] = clasificar_materia(fallo, openai_client)
        if i % 20 == 0:
            print(f"    clasificados {i}/{len(fallos_ok)}")

    todas_las_filas = []
    for fallo in fallos_ok:
        todas_las_filas.extend(chunkear_fallo(fallo))
    print(f"✂️  {len(todas_las_filas)} chunks generados en total")

    print("🧠 Generando embeddings...")
    embeber_filas(todas_las_filas, openai_client)

    print("⬆️  Subiendo a Supabase (fallos_chunks)...")
    subir_filas(todas_las_filas, supabase)

    print("\n✅ Listo. Corré `analyze fallos_chunks;` en Supabase si fue una carga grande.")


if __name__ == "__main__":
    main()
