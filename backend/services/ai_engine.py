"""
================================================================
CHUBUT.IA — MOTOR DE IA v3.0 — ARQUITECTURA DE CEREBRO DUAL
================================================================
Dos bases vectoriales independientes con cortafuegos de contexto:

  VDB_FALLOS  →  MI_BASE_VECTORIAL   (jurisprudencia / sentencias)
  VDB_LEYES   →  MI_BASE_LEYES       (Digesto Provincial en PDF)

Flujo de una consulta:
  1. Reformulación con memoria conversacional
  2. Clasificación de intención (fallos / leyes / ambos / conversacion)
  3. Súper Búsqueda Dual sobre la(s) base(s) relevante(s)
  4. Construcción del prompt con cortafuegos de contexto
  5. Generación de respuesta con GPT-4o-mini
================================================================
"""

try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import os
import re
import zipfile
import asyncio
import gdown

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ══════════════════════════════════════════════════════════════════
# 1. SINGLETONS Y CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════

_vdb_fallos: Chroma | None = None   # Jurisprudencia
_vdb_leyes:  Chroma | None = None   # Digesto Provincial
_llm:        ChatOpenAI | None = None
_emb:        OpenAIEmbeddings | None = None  # Instancia compartida

# ── Rutas y URLs ──────────────────────────────────────────────────
FALLOS_PATH      = "MI_BASE_VECTORIAL"
LEYES_PATH       = "MI_BASE_LEYES"
LEYES_COLLECTION = "leyes_chubut"

GDRIVE_FALLOS_URL = "https://drive.google.com/uc?id=1J0O52QmGKZnx_gazbuZ7-Mq6R48pxz9E"
GDRIVE_LEYES_URL  = os.getenv("GDRIVE_LEYES_URL", "")  # Configurar en Railway

# ── Intenciones del clasificador ──────────────────────────────────
INTENT_FALLOS        = "fallos"
INTENT_LEYES         = "leyes"
INTENT_AMBOS         = "ambos"
INTENT_CONVERSACION  = "conversacion"
INTENTS_VALIDOS      = {INTENT_FALLOS, INTENT_LEYES, INTENT_AMBOS, INTENT_CONVERSACION}


# ══════════════════════════════════════════════════════════════════
# 2. INICIALIZACIÓN (llamada en el lifespan de FastAPI)
# ══════════════════════════════════════════════════════════════════

async def initialize_ai():
    """Inicializa ambas bases vectoriales y el LLM de forma asíncrona."""
    global _vdb_fallos, _vdb_leyes, _llm, _emb
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _load_ai_sync)


def _load_ai_sync():
    """Carga sincrónica: descarga ZIPs si faltan, inicializa Chroma y LLM."""
    global _vdb_fallos, _vdb_leyes, _llm, _emb

    # ── Embeddings compartidos (un solo modelo para las dos bases) ───
    _emb = OpenAIEmbeddings(model="text-embedding-3-small")

    # ── Base de Fallos ───────────────────────────────────────────────
    _vdb_fallos = _cargar_o_descargar(
        path=FALLOS_PATH,
        gdrive_url=GDRIVE_FALLOS_URL,
        nombre="Base de Jurisprudencia",
        collection=None,         # colección default
    )

    # ── Base de Leyes ────────────────────────────────────────────────
    if GDRIVE_LEYES_URL:
        _vdb_leyes = _cargar_o_descargar(
            path=LEYES_PATH,
            gdrive_url=GDRIVE_LEYES_URL,
            nombre="Base del Digesto Provincial",
            collection=LEYES_COLLECTION,
        )
    elif os.path.exists(LEYES_PATH):
        # Ya existe localmente (desarrollo / primer deploy manual)
        _vdb_leyes = Chroma(
            persist_directory=LEYES_PATH,
            embedding_function=_emb,
            collection_name=LEYES_COLLECTION,
        )
        print("✅ Base del Digesto Provincial cargada (local).")
    else:
        # Sin base de leyes: el sistema funciona solo con fallos
        print("⚠️  GDRIVE_LEYES_URL no configurada y MI_BASE_LEYES no existe.")
        print("   Las consultas sobre leyes responderán con contexto vacío.")
        _vdb_leyes = None

    # ── LLM ──────────────────────────────────────────────────────────
    _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    print("✅ Motor de IA Dual inicializado correctamente.")


def _cargar_o_descargar(
    path: str,
    gdrive_url: str,
    nombre: str,
    collection: str | None,
) -> Chroma:
    """Descarga el ZIP desde Google Drive si la carpeta no existe, luego carga Chroma."""
    if not os.path.exists(path):
        print(f"📥 Descargando {nombre} desde Google Drive...")
        zip_name = f"{path.replace('/', '_')}.zip"
        gdown.download(gdrive_url, zip_name, quiet=False)
        with zipfile.ZipFile(zip_name, "r") as zr:
            zr.extractall()
        os.remove(zip_name)
        print(f"✅ {nombre} descomprimida en '{path}/'")

    kwargs = dict(persist_directory=path, embedding_function=_emb)
    if collection:
        kwargs["collection_name"] = collection

    vdb = Chroma(**kwargs)
    print(f"✅ {nombre} lista ({vdb._collection.count():,} fragmentos).")
    return vdb


# ── Getters públicos ──────────────────────────────────────────────
def get_vdb_fallos() -> Chroma:
    if _vdb_fallos is None:
        raise RuntimeError("Motor IA no inicializado.")
    return _vdb_fallos


def get_vdb_leyes() -> Chroma | None:
    """Puede ser None si la base de leyes no está disponible."""
    return _vdb_leyes


def get_llm() -> ChatOpenAI:
    if _llm is None:
        raise RuntimeError("LLM no inicializado.")
    return _llm


# ══════════════════════════════════════════════════════════════════
# 3. CLASIFICADOR DE INTENCIÓN
# ══════════════════════════════════════════════════════════════════

# Heurísticas rápidas para evitar un LLM call en casos obvios.
# Si no matchean, se usa el clasificador LLM.
_PATRONES_LEYES = re.compile(
    r"\b(ley|leyes|decreto|resoluc|ordenanza|norma|artículo|art\.|código|estatuto"
    r"|digesto|legislac|promulgad|sancionad|modificac|vigente|derogad"
    r"|n[°º]\s*\d|n[uú]mero\s+\d)\b",
    re.IGNORECASE,
)
_PATRONES_FALLOS = re.compile(
    r"\b(fallo|sentencia|jurisprudencia|juzgado|tribunal|caratula|expediente"
    r"|demanda|actor|demandado|apelación|recurso|amparo|resolvió|rechaz|hizo lugar"
    r"|condena|absuelv|absuel)\b",
    re.IGNORECASE,
)

_PROMPT_CLASIFICADOR = """\
Clasificá la siguiente consulta legal en UNA SOLA de estas cuatro categorías.
Respondé ÚNICAMENTE con la palabra clave, sin explicación ni puntuación:

  fallos       → el usuario busca sentencias, jurisprudencia o fallos judiciales
  leyes        → el usuario pregunta por leyes, decretos, resoluciones, artículos legales o normas
  ambos        → la consulta requiere TANTO jurisprudencia COMO legislación
  conversacion → es una pregunta de seguimiento, saludo, o no requiere búsqueda en base de datos

Consulta: "{query}"

Categoría:"""


async def clasificar_intencion(query: str, llm: ChatOpenAI) -> str:
    """
    Clasifica la intención de la consulta.
    Prioridad:
      1. Heurísticas locales (sin costo de API, ~0ms)
      2. Clasificador LLM (si las heurísticas empatan o no matchean)
    """
    query_lower = query.lower()

    tiene_leyes  = bool(_PATRONES_LEYES.search(query_lower))
    tiene_fallos = bool(_PATRONES_FALLOS.search(query_lower))

    # Caso claro por heurística → retorno inmediato sin llamar a la API
    if tiene_leyes and not tiene_fallos:
        return INTENT_LEYES
    if tiene_fallos and not tiene_leyes:
        return INTENT_FALLOS
    if tiene_leyes and tiene_fallos:
        return INTENT_AMBOS

    # Ambiguo → usar el LLM clasificador (temperatura 0 para respuesta fija)
    llm_clasificador = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    loop = asyncio.get_event_loop()
    prompt = _PROMPT_CLASIFICADOR.format(query=query[:800])

    try:
        resultado = await loop.run_in_executor(
            None,
            lambda: llm_clasificador.invoke([HumanMessage(content=prompt)]).content
        )
        intent = resultado.strip().lower().split()[0]  # primera palabra
        return intent if intent in INTENTS_VALIDOS else INTENT_FALLOS
    except Exception:
        # Fallback seguro: buscar en fallos
        return INTENT_FALLOS


# ══════════════════════════════════════════════════════════════════
# 4. BÚSQUEDA VECTORIAL (componente reutilizable)
# ══════════════════════════════════════════════════════════════════

async def _busqueda_dual_en_vdb(
    query_original: str,
    query_tecnica: str,
    vdb: Chroma,
    k: int = 6,
    max_docs: int = 10,
) -> list:
    """
    Ejecuta dos búsquedas de similitud sobre un único VDB
    (con la query original y con la traducción técnica),
    fusiona y deduplica los resultados.
    """
    loop = asyncio.get_event_loop()

    docs_a, docs_b = await asyncio.gather(
        loop.run_in_executor(None, lambda: vdb.similarity_search(query_original, k=k)),
        loop.run_in_executor(None, lambda: vdb.similarity_search(query_tecnica, k=k)),
    )

    vistos: set[str] = set()
    resultado: list = []
    for doc in docs_a + docs_b:
        if doc.page_content not in vistos:
            vistos.add(doc.page_content)
            resultado.append(doc)

    return resultado[:max_docs]


def _formatear_docs_fallos(docs: list) -> str:
    """Formatea los documentos de jurisprudencia para el prompt."""
    if not docs:
        return "(Sin resultados de jurisprudencia para esta consulta)"
    return "\n\n".join([
        f"📅 FECHA: {d.metadata.get('fecha_completa', 'N/D')}\n"
        f"🔗 URL: {d.metadata.get('link_pdf', 'N/D')}\n"
        f"📄 CONTENIDO:\n{d.page_content}"
        for d in docs
    ])


def _formatear_docs_leyes(docs: list) -> str:
    """Formatea los documentos del Digesto para el prompt."""
    if not docs:
        return "(Sin resultados en el Digesto Provincial para esta consulta)"
    return "\n\n".join([
        f"📜 NORMA: {d.metadata.get('cita', d.metadata.get('nombre_archivo', 'N/D'))}\n"
        f"📄 FUENTE: {d.metadata.get('fuente', 'N/D')}\n"
        f"📝 TEXTO:\n{d.page_content}"
        for d in docs
    ])


# ══════════════════════════════════════════════════════════════════
# 5. SÚPER BÚSQUEDA DUAL (función principal de recuperación)
# ══════════════════════════════════════════════════════════════════

async def super_search(
    query_usuario: str,
    historial_previo: list[dict],
    llm: ChatOpenAI,
    vdb_fallos: Chroma,
    vdb_leyes: Chroma | None,
) -> tuple[str, str, str]:
    """Pipeline completo de recuperación de contexto."""
    loop = asyncio.get_event_loop()

    # ── Paso 1: Reformulación con memoria ─────────────────────────
    if historial_previo:
        hist_texto = "\n".join([
            f"{m['role']}: {m['content'][:200]}"
            for m in historial_previo[-3:]
        ])
        prompt_ref = (
            f"Basado en esta charla previa:\n{hist_texto}\n\n"
            f"Reescribí la siguiente pregunta para que sea una consulta de búsqueda "
            f"completa e independiente en una base de datos jurídica. "
            f"Si el usuario menciona 'esa ley', 'ese fallo', 'resúmelo' o algo similar, "
            f"incluí obligatoriamente el tema legal del que venían hablando. "
            f"Pregunta del usuario: '{query_usuario[:1500]}'. "
            f"Solo devolvé la pregunta reescrita, sin comillas."
        )
        query_busqueda = await loop.run_in_executor(
            None,
            lambda: llm.invoke([HumanMessage(content=prompt_ref)]).content
                       .replace('"', "").strip()
        )
    else:
        query_busqueda = query_usuario

    query_segura = query_busqueda[:3000]

    # ── Paso 2: Traducción técnica + Clasificación (en paralelo) ──
    prompt_tecnico = (
        f"Traducí esta consulta al lenguaje hiper-formal y técnico que usaría "
        f"un juez o legislador argentino en un texto oficial. "
        f"Enfocate en el núcleo jurídico. "
        f"Solo devolvé la frase traducida, sin comillas: '{query_segura[:1000]}'"
    )

    query_tecnica_raw, intent = await asyncio.gather(
        loop.run_in_executor(
            None,
            lambda: llm.invoke([HumanMessage(content=prompt_tecnico)]).content
                       .replace('"', "").strip()
        ),
        clasificar_intencion(query_segura, llm),
    )
    query_tecnica = query_tecnica_raw[:3000]

    # ── Paso 3: Búsqueda según intención ──────────────────────────
    contexto_fallos = "(No se consultó la base de jurisprudencia)"
    contexto_leyes  = "(No se consultó el Digesto Provincial)"

    if intent == INTENT_CONVERSACION:
        return contexto_fallos, contexto_leyes, intent

    if intent in (INTENT_FALLOS, INTENT_AMBOS):
        docs_f = await _busqueda_dual_en_vdb(query_segura, query_tecnica, vdb_fallos)
        contexto_fallos = _formatear_docs_fallos(docs_f)

    if intent in (INTENT_LEYES, INTENT_AMBOS):
        if vdb_leyes is not None:
            docs_l = await _busqueda_dual_en_vdb(query_segura, query_tecnica, vdb_leyes)
            contexto_leyes = _formatear_docs_leyes(docs_l)
        else:
            # ACÁ LE DAMOS PERMISO PARA USAR SU CONOCIMIENTO GENERAL
            contexto_leyes = (
                "(La base oficial del Digesto Provincial no está conectada en este momento. "
                "Utiliza tu conocimiento general para responder sobre la ley solicitada y "
                "agrega OBLIGATORIAMENTE la advertencia al final de tu respuesta.)"
            )

    return contexto_fallos, contexto_leyes, intent


# ══════════════════════════════════════════════════════════════════
# 6. SYSTEM PROMPT CON CORTAFUEGOS DE CONTEXTO
# ══════════════════════════════════════════════════════════════════

def build_system_prompt(
    contexto_fallos: str,
    contexto_leyes: str,
    intent: str,
) -> str:
    """Construye el system prompt con un CORTAFUEGOS DE CONTEXTO estricto."""

    # ── Sección de contexto según intención ───────────────────────
    if intent == INTENT_CONVERSACION:
        bloque_contexto = (
            "El usuario está haciendo una pregunta de seguimiento o conversacional. "
            "Respondé de forma fluida y natural usando tu memoria de la conversación."
        )
    elif intent == INTENT_FALLOS:
        bloque_contexto = f"""══ BLOQUE A — JURISPRUDENCIA (fallos y sentencias judiciales) ══
{contexto_fallos}
══════════════════════════════════════════════════════════════"""
    elif intent == INTENT_LEYES:
        bloque_contexto = f"""══ BLOQUE B — DIGESTO PROVINCIAL (leyes, decretos y resoluciones) ══
{contexto_leyes}
══════════════════════════════════════════════════════════════"""
    else:  # AMBOS
        bloque_contexto = f"""══ BLOQUE A — JURISPRUDENCIA (fallos y sentencias judiciales) ══
{contexto_fallos}
══════════════════════════════════════════════════════════════

══ BLOQUE B — DIGESTO PROVINCIAL (leyes, decretos y resoluciones) ══
{contexto_leyes}
══════════════════════════════════════════════════════════════"""

    return f"""Sos Chubut.IA, el asistente jurídico experto de la Provincia del Chubut.

{bloque_contexto}

════════════════════ REGLAS ABSOLUTAS ════════════════════════

REGLA 1 — CORTAFUEGOS DE CONTEXTO (crítica):
Las fuentes BLOQUE A (jurisprudencia) y BLOQUE B (legislación) son independientes.
NUNCA mezcles un fallo con una ley en la misma cita.
NUNCA uses un link de jurisprudencia (juschubut.gov.ar / Eureka) para citar una ley.

REGLA 2 — CONOCIMIENTO GENERAL Y ADVERTENCIA OBLIGATORIA:
Si la información de una LEY no se encuentra en el BLOQUE B (ya sea porque está vacío o porque la norma no figura), TENÉS PERMITIDO responder utilizando tu conocimiento general previo sobre leyes argentinas y provinciales.
⚠️ ATENCIÓN: Si usás tu conocimiento general, estás ESTRICTAMENTE OBLIGADO a agregar este texto exacto al final de tu respuesta:
"⚠️ *Nota: Esta respuesta se basa en mi conocimiento general, ya que la base oficial de leyes no se encuentra conectada actualmente y la información no está verificada en tiempo real. Mi especialidad principal y base de datos oficial es la jurisprudencia de la Provincia del Chubut.*"
NUNCA inventes URLs. Si usas conocimiento general, en el apartado de Fuente poné "Enlace no disponible en la base actual".

REGLA 3 — CONVERSACIÓN FLUIDA EN SEGUIMIENTOS:
Si el usuario pide resumir, explicar mejor, o hace una pregunta sobre algo
que ya mencionaste en el mensaje anterior, respondé de forma natural y conversacional.

════════════════════ FORMATOS DE RESPUESTA ═══════════════════

FORMATO PARA FALLOS (usá este cuando presentes jurisprudencia):
📌 **[Título Descriptivo del Caso]**
* 📅 **Fecha del Fallo:** [DD/MM/AAAA]
* 📖 **Cita Textual:** "[fragmento con sustancia jurídica del BLOQUE A]"
* 📝 **Resumen:** [qué trataba el caso]
* ⚖️ **Resolución:** [decisión del juez, si figura]
* 🔗 **Ver fallo oficial:** [Link al PDF oficial](URL_EXACTA_DEL_BLOQUE_A)

FORMATO PARA LEYES (usá este cuando presentes normativa):
📜 **[Tipo y Número de la Norma]**
* 🗓️ **Sancionada/Promulgada:** [año o fecha, si figura o lo sabés]
* 📋 **Artículo relevante:** "[texto literal o resumen del artículo]"
* 💡 **Interpretación:** [explicación en lenguaje claro de qué implica este artículo]
* 📁 **Fuente:** [nombre del archivo del BLOQUE B o "Enlace no disponible en la base actual"]

FORMATO MIXTO (cuando la respuesta combina ambas fuentes):
Presentá primero la legislación aplicable (BLOQUE B) y luego la jurisprudencia
que la interpreta o aplica (BLOQUE A).
════════════════════════════════════════════════════════════════"""



# ══════════════════════════════════════════════════════════════════
# 7. GENERACIÓN DE RESPUESTA
# ══════════════════════════════════════════════════════════════════

async def generate_response(
    contexto_fallos: str,
    contexto_leyes: str,
    intent: str,
    historial_completo: list[dict],
) -> str:
    """Construye los mensajes y llama al LLM."""
    llm = get_llm()
    loop = asyncio.get_event_loop()

    system_prompt = build_system_prompt(contexto_fallos, contexto_leyes, intent)
    mensajes = [SystemMessage(content=system_prompt)]

    for m in historial_completo[:-1]:
        if m["role"] == "user":
            mensajes.append(HumanMessage(content=m["content"]))
        else:
            mensajes.append(AIMessage(content=m["content"]))

    mensajes.append(HumanMessage(content=historial_completo[-1]["content"]))

    respuesta = await loop.run_in_executor(None, lambda: llm.invoke(mensajes))
    return respuesta.content


# ══════════════════════════════════════════════════════════════════
# 8. UTILIDADES
# ══════════════════════════════════════════════════════════════════

async def generate_chat_title(primer_mensaje: str) -> str:
    """Genera un título corto para la conversación (3-4 palabras)."""
    llm = get_llm()
    loop = asyncio.get_event_loop()
    prompt = f"Resumí esta consulta legal en 3 o 4 palabras: '{primer_mensaje[:500]}'"
    titulo = await loop.run_in_executor(
        None,
        lambda: llm.invoke([HumanMessage(content=prompt)]).content
                   .replace('"', "").strip()
    )
    return titulo
