import os
import zipfile
import asyncio
import gdown
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from duckduckgo_search import DDGS

# ── Singletons globales ──────────────────────────────────────────────────────
_vdb: Chroma | None = None
_llm: ChatOpenAI | None = None

VECTORSTORE_PATH = "MI_BASE_VECTORIAL"
GDRIVE_URL = "https://drive.google.com/uc?id=1J0O52QmGKZnx_gazbuZ7-Mq6R48pxz9E"


# ── Inicialización (llamada en el lifespan de FastAPI) ───────────────────────
async def initialize_ai():
    global _vdb, _llm
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _load_ai_sync)


def _load_ai_sync():
    global _vdb, _llm

    if not os.path.exists(VECTORSTORE_PATH):
        print("📥 Descargando base vectorial desde Google Drive...")
        gdown.download(GDRIVE_URL, "base.zip", quiet=False)
        with zipfile.ZipFile("base.zip", "r") as zr:
            zr.extractall()
        os.remove("base.zip")
        print("✅ Base vectorial descomprimida.")

    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    _vdb = Chroma(persist_directory=VECTORSTORE_PATH, embedding_function=emb)
    _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    print("✅ ChromaDB y LLM inicializados.")


def get_vdb() -> Chroma:
    if _vdb is None:
        raise RuntimeError("Motor IA no inicializado. Esperá al arranque del servidor.")
    return _vdb


def get_llm() -> ChatOpenAI:
    if _llm is None:
        raise RuntimeError("LLM no inicializado.")
    return _llm


# ── System Prompt ────────────────────────────────────────────────────────────
def build_system_prompt(contexto: str) -> str:
    return f"""Sos Chubut.IA, el motor jurídico experto de la Provincia de Chubut.

A continuación te paso los fallos recuperados:
{contexto}

REGLAS ESTRICTAS:
1. Muestra SIEMPRE los fallos relevantes y reales del contexto.
2. NUNCA inventes jurisprudencia.
3. TIENES ESTRICTAMENTE PROHIBIDO usar la palabra 'undefined' en tus respuestas.
4. Si el usuario pregunta algo que NO está en el contexto o es de conocimiento general, podés responder usando tu conocimiento previo, pero DEBES agregar obligatoriamente al final de tu respuesta EXACTAMENTE esta frase: "⚠️ *Nota: Esta respuesta se basa en conocimiento general. Mi base de datos oficial y mi especialidad es la jurisprudencia de la Provincia del Chubut.*"

FORMATO OBLIGATORIO:
📌 **[Título Descriptivo del Caso]**
* 📅 **Fecha del fallo:** [Fecha]
* 📖 **Cita Textual:** "[Extracto]"
* 📝 **Resumen de los Hechos:** [Resumen breve]
* ⚖️ **Resolución:** [Decisión]
* 🔗 **Ver fallo oficial:** [Acceder al documento oficial](URL_DEL_FALLO)
(IMPORTANTE: En la última viñeta, debes reemplazar "URL_DEL_FALLO" EXCLUSIVAMENTE con la dirección web que aparece como 'ENLACE_OFICIAL' en el contexto. Si no hay enlace, omite esa viñeta).
"""
# ── Súper Búsqueda Dual ──────────────────────────────────────────────────────
async def super_search(
    query_usuario: str,
    historial_previo: list[dict],
    llm: ChatOpenAI,
    vdb: Chroma,
) -> tuple[str, str]:
    loop = asyncio.get_event_loop()

    if historial_previo:
        hist_texto = "\n".join(
            [f"{m['role']}: {m['content'][:200]}" for m in historial_previo[-3:]]
        )
        prompt_ref = (
            f"Basado en esta charla previa:\n{hist_texto}\n\n"
            f"Reescribe la siguiente pregunta para que sea una consulta de búsqueda completa e independiente. "
            f"Pregunta del usuario: '{query_usuario[:1500]}'. Solo devuelve la pregunta reescrita sin comillas."
        )
        query_busqueda = await loop.run_in_executor(
            None,
            lambda: llm.invoke([HumanMessage(content=prompt_ref)]).content.replace('"', "").strip(),
        )
    else:
        query_busqueda = query_usuario

    query_segura = query_busqueda[:3000]

    prompt_opt = (
        f"Traduce esta consulta coloquial al lenguaje formal y técnico que usaría un juez. "
        f"Solo devuelve la frase traducida, sin comillas: '{query_segura[:1000]}'"
    )

    query_traducida, docs_original = await asyncio.gather(
        loop.run_in_executor(
            None,
            lambda: llm.invoke([HumanMessage(content=prompt_opt)]).content.replace('"', "").strip(),
        ),
        loop.run_in_executor(None, lambda: vdb.similarity_search(query_segura, k=6)),
    )

    docs_traducidos = await loop.run_in_executor(
        None, lambda: vdb.similarity_search(query_traducida, k=6)
    )

    docs_unicos = []
    textos_vistos: set[str] = set()
    for d in docs_original + docs_traducidos:
        if d.page_content not in textos_vistos:
            textos_vistos.add(d.page_content)
            docs_unicos.append(d)

    docs = docs_unicos[:10]

    # FILTRO ABSOLUTO PARA LINKS
    contexto_lista = []
    for d in docs:
        fecha = d.metadata.get('fecha_completa', 'Sin fecha')
        raw_url = str(d.metadata.get('link_pdf') or d.metadata.get('url') or "").strip()
        
        # Si la URL viene rota o vacía desde la base de datos, la pisamos
        if not raw_url or raw_url.lower() in ["undefined", "none", "null"]:
            raw_url = "https://www.juschubut.gov.ar/jurisprudencia/"
            
        contexto_lista.append(f"📅 FECHA: {fecha}\n🔗 ENLACE_OFICIAL: {raw_url}\n📄 CONTENIDO:\n{d.page_content}")

    contexto_final = "\n\n".join(contexto_lista)

    return contexto_final, query_segura

# ── Búsqueda Web en la Legislatura ───────────────────────────────────────────
def buscar_legislatura(query: str) -> str:
    print(f"🔍 Buscando en Legislatura: {query}")
    try:
        with DDGS() as ddgs:
            # Forzamos la búsqueda solo en el dominio oficial
            resultados = list(ddgs.text(f"{query} site:legislaturadelchubut.gob.ar", max_results=3))
            
            if not resultados:
                return "No se encontraron resultados en la web oficial de la Legislatura para esta consulta."
            
            textos = []
            for r in resultados:
                textos.append(f"- {r['title']}: {r['body']}\n  (Link: {r['href']})")
            return "\n\n".join(textos)
    except Exception as e:
        return f"Error técnico al consultar la web de la Legislatura: {e}"

# ── Generación de respuesta ──────────────────────────────────────────────────
async def generate_response(
    contexto: str,
    historial_completo: list[dict],
) -> str:
    llm = get_llm()
    loop = asyncio.get_event_loop()

    # 1. Extraer la última pregunta del usuario
    ultima_pregunta = historial_completo[-1]["content"]

    # 2. Hacer la búsqueda en la Legislatura en segundo plano
    resultados_web = await loop.run_in_executor(None, lambda: buscar_legislatura(ultima_pregunta))

    # 3. Mezclar la jurisprudencia local con las leyes de internet
    contexto_enriquecido = f"""
=== JURISPRUDENCIA OFICIAL (Base de datos local) ===
{contexto}

=== LEGISLACIÓN OFICIAL (Búsqueda web en tiempo real en legislaturadelchubut.gob.ar) ===
{resultados_web}
    """

    # 4. Armar los mensajes
    mensajes = [SystemMessage(content=build_system_prompt(contexto_enriquecido))]
    for m in historial_completo[:-1]:
        if m["role"] == "user":
            mensajes.append(HumanMessage(content=m["content"]))
        else:
            mensajes.append(AIMessage(content=m["content"]))
    mensajes.append(HumanMessage(content=ultima_pregunta))

    # 5. Generar la respuesta final
    respuesta = await loop.run_in_executor(None, lambda: llm.invoke(mensajes))
    return respuesta.content


# ── Renombrado automático de conversación ────────────────────────────────────
async def generate_chat_title(primer_mensaje: str) -> str:
    llm = get_llm()
    loop = asyncio.get_event_loop()
    prompt = f"Resume esta consulta en 3 o 4 palabras: '{primer_mensaje[:500]}'"
    titulo = await loop.run_in_executor(
        None,
        lambda: llm.invoke([HumanMessage(content=prompt)]).content.replace('"', "").strip(),
    )
    return titulo
