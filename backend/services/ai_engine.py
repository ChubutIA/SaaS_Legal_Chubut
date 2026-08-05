"""
================================================================
CHUBUT.IA — MOTOR DE IA v4.0 — API EN VIVO + BASE VECTORIAL
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
import httpx
import urllib.parse
import urllib.parse

from services.comodoro_scraper import buscar_ordenanzas_comodoro
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# ══════════════════════════════════════════════════════════════════
# 1. SINGLETONS Y CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════
_vdb_fallos: Chroma | None = None
_vdb_leyes:  Chroma | None = None # Lo mantenemos por compatibilidad con chat.py
_llm:        ChatOpenAI | None = None
_emb:        OpenAIEmbeddings | None = None

FALLOS_PATH      = "MI_BASE_VECTORIAL"
GDRIVE_FALLOS_URL = "https://drive.google.com/uc?id=1J0O52QmGKZnx_gazbuZ7-Mq6R48pxz9E"

INTENT_FALLOS        = "fallos"
INTENT_LEYES         = "leyes"
INTENT_AMBOS         = "ambos"
INTENT_CONVERSACION  = "conversacion"
INTENTS_VALIDOS      = {INTENT_FALLOS, INTENT_LEYES, INTENT_AMBOS, INTENT_CONVERSACION}

# ══════════════════════════════════════════════════════════════════
# 2. INICIALIZACIÓN
# ══════════════════════════════════════════════════════════════════
async def initialize_ai():
    global _vdb_fallos, _llm, _emb
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _load_ai_sync)

def _load_ai_sync():
    global _vdb_fallos, _llm, _emb
    _emb = OpenAIEmbeddings(model="text-embedding-3-small")
    _vdb_fallos = _cargar_o_descargar(FALLOS_PATH, GDRIVE_FALLOS_URL, "Base de Jurisprudencia", None)
    _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    print("✅ Motor de IA v4.0 inicializado. (Jurisprudencia local + Leyes API en vivo)")

def _cargar_o_descargar(path: str, gdrive_url: str, nombre: str, collection: str | None) -> Chroma:
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
    return vdb

def get_vdb_fallos() -> Chroma:
    if _vdb_fallos is None: raise RuntimeError("Motor IA no inicializado.")
    return _vdb_fallos

def get_vdb_leyes() -> Chroma | None:
    return None # Ya no usamos base local de leyes, usamos API

def get_llm() -> ChatOpenAI:
    if _llm is None: raise RuntimeError("LLM no inicializado.")
    return _llm

# ══════════════════════════════════════════════════════════════════
# 3. CLASIFICADOR DE INTENCIÓN
# ══════════════════════════════════════════════════════════════════
_PATRONES_LEYES = re.compile(r"\b(ley|leyes|decreto|resoluc|ordenanza|norma|artículo|art\.|código|estatuto|digesto|legislac|promulgad|sancionad|modificac|vigente|derogad|n[°º]\s*\d|n[uú]mero\s+\d)\b", re.IGNORECASE)
_PATRONES_FALLOS = re.compile(r"\b(fallo|sentencia|jurisprudencia|juzgado|tribunal|caratula|expediente|demanda|actor|demandado|apelación|recurso|amparo|resolvió|rechaz|hizo lugar|condena|absuelv|absuel)\b", re.IGNORECASE)

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
    query_lower = query.lower()
    tiene_leyes  = bool(_PATRONES_LEYES.search(query_lower))
    tiene_fallos = bool(_PATRONES_FALLOS.search(query_lower))

    if tiene_leyes and not tiene_fallos: return INTENT_LEYES
    if tiene_fallos and not tiene_leyes: return INTENT_FALLOS
    if tiene_leyes and tiene_fallos: return INTENT_AMBOS

    llm_clasificador = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    loop = asyncio.get_event_loop()
    prompt = _PROMPT_CLASIFICADOR.format(query=query[:800])
    try:
        resultado = await loop.run_in_executor(None, lambda: llm_clasificador.invoke([HumanMessage(content=prompt)]).content)
        intent = resultado.strip().lower().split()[0]
        return intent if intent in INTENTS_VALIDOS else INTENT_FALLOS
    except Exception:
        return INTENT_FALLOS

# ══════════════════════════════════════════════════════════════════
# 4. BÚSQUEDA VECTORIAL (FALLOS) Y API (LEYES)
# ══════════════════════════════════════════════════════════════════
async def _busqueda_dual_en_vdb(query_original: str, query_tecnica: str, vdb: Chroma, k: int = 6, max_docs: int = 10) -> list:
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
    if not docs: return "(Sin resultados de jurisprudencia para esta consulta)"
    return "\n\n".join([f"📅 FECHA: {d.metadata.get('fecha_completa', 'N/D')}\n🔗 URL: {d.metadata.get('link_pdf', 'N/D')}\n📄 CONTENIDO:\n{d.page_content}" for d in docs])

async def buscar_leyes_api_chubut(query_usuario: str, llm: ChatOpenAI) -> str:
    """Extrae palabras clave y busca directo en la API secreta de la Legislatura."""
    loop = asyncio.get_event_loop()
    
    prompt_limpieza = f"Extraé solo 2 o 3 palabras clave legales de esta consulta para buscar en una base de datos. Ignorá saludos o verbos. Consulta: '{query_usuario}'. Palabras clave:"
    try:
        keywords = await loop.run_in_executor(None, lambda: llm.invoke([HumanMessage(content=prompt_limpieza)]).content.replace('"', '').strip())
    except:
        keywords = query_usuario

    url = f"https://digesto.legislaturadelchubut.gob.ar/api/public/search/documentos?query={urllib.parse.quote(keywords)}&page=0&size=3"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15.0)
            if response.status_code == 200:
                datos = response.json()
                if not datos:
                    return "(No se encontraron resultados en el Digesto Oficial para esta consulta. Podés usar tu conocimiento general.)"
                
                textos_leyes = []
                for doc in datos:
                    norma = doc.get("numeroCompleto", "Norma sin número")
                    resumen = doc.get("resumen", "Sin resumen oficial.")
                    texto_completo = doc.get("textoCompleto", "")
                    estado = doc.get("estadoConsolidacion", "Estado desconocido")
                    
                    # Extraer datos exactos para armar la URL directa
                    rama_data = doc.get("rama") or {}
                    rama_desc = rama_data.get("descripcion", "General") if isinstance(rama_data, dict) else "General"
                    rama_id = rama_data.get("id", "") if isinstance(rama_data, dict) else ""
                    numero_ley = doc.get("numero", "")
                    
                    # Armar la URL mágica directa a la vista de la ley
                    if rama_id and numero_ley:
                        link_oficial = f"https://digesto.legislaturadelchubut.gob.ar/public/rama/{rama_id}/ley/{numero_ley}"
                    else:
                        # Fallback por si la ley es muy vieja y no tiene rama
                        link_oficial = f"https://digesto.legislaturadelchubut.gob.ar/public/result?filter%5Bquery%5D={urllib.parse.quote(norma)}"
                    
                    if texto_completo and len(texto_completo) > 2000:
                        texto_completo = texto_completo[:2000] + "... [TEXTO TRUNCADO]"
                        
                    textos_leyes.append(
                        f"📜 NORMA: {norma}\n"
                        f"🏛️ RAMA: {rama_desc}\n"
                        f"✅ ESTADO: {estado}\n"
                        f"🔗 LINK_OFICIAL: {link_oficial}\n"
                        f"📝 RESUMEN: {resumen}\n"
                        f"📄 TEXTO:\n{texto_completo}"
                    )
                return "\n\n".join(textos_leyes)
            else:
                return "(La API del Digesto Oficial no respondió correctamente. Podés usar tu conocimiento general.)"
    except Exception as e:
        print(f"Error API Digesto: {e}")
        return "(Error de conexión con la API del Digesto Oficial. Podés usar tu conocimiento general.)"
async def buscar_ordenanzas_municipal(query_usuario: str, llm: ChatOpenAI) -> str:
    """Extrae 1 sola palabra clave y busca en el scraper de Comodoro"""
    loop = asyncio.get_event_loop()
    
    prompt = f"Extraé UNA (1) sola palabra clave principal de esta consulta legal para buscar en un digesto municipal. Ignorá verbos o saludos. Solo devolvé esa palabra. Consulta: '{query_usuario}'. Palabra clave:"
    try:
        keyword = await loop.run_in_executor(None, lambda: llm.invoke([HumanMessage(content=prompt)]).content.replace('"', '').strip())
        keyword = keyword.split()[0] # Por si la IA devuelve más de una palabra
    except:
        keyword = query_usuario.split()[0]
        
    try:
        # Llamamos a tu archivo comodoro_scraper.py
        resultados = await loop.run_in_executor(None, buscar_ordenanzas_comodoro, keyword)
        if not resultados:
            return "(No se encontraron ordenanzas municipales para esta consulta.)"
            
        textos = []
        for item in resultados:
            textos.append(
                f"🏛️ ORDENANZA: {item['norma']}\n"
                f"📅 FECHA: {item['fecha']}\n"
                f"📝 TEMA: {item['tema']}\n"
                f"🔗 LINK: {item['link']}\n"
                f"📄 CONTENIDO EXTRAÍDO DEL DOCUMENTO:\n{item['contenido_pdf']}"
            )
        return "\n\n".join(textos)
    except Exception as e:
        return "(Error al consultar el digesto municipal de Comodoro.)"
# ══════════════════════════════════════════════════════════════════
# 5. SÚPER BÚSQUEDA DUAL
# ══════════════════════════════════════════════════════════════════
async def super_search(query_usuario: str, historial_previo: list[dict], llm: ChatOpenAI, vdb_fallos: Chroma, vdb_leyes: Chroma | None) -> tuple[str, str, str]:
    loop = asyncio.get_event_loop()

    if historial_previo:
        hist_texto = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in historial_previo[-3:]])
        prompt_ref = f"Basado en esta charla previa:\n{hist_texto}\n\nReescribí la siguiente pregunta para que sea una consulta de búsqueda completa e independiente en una base de datos jurídica. Si el usuario menciona 'esa ley', 'ese fallo', 'resúmelo' o algo similar, incluí obligatoriamente el tema legal del que venían hablando. Pregunta del usuario: '{query_usuario[:1500]}'. Solo devolvé la pregunta reescrita, sin comillas."
        query_busqueda = await loop.run_in_executor(None, lambda: llm.invoke([HumanMessage(content=prompt_ref)]).content.replace('"', "").strip())
    else:
        query_busqueda = query_usuario

    query_segura = query_busqueda[:3000]

    prompt_tecnico = f"Traducí esta consulta al lenguaje hiper-formal y técnico que usaría un juez o legislador argentino en un texto oficial. Enfocate en el núcleo jurídico. Solo devolvé la frase traducida, sin comillas: '{query_segura[:1000]}'"

    query_tecnica_raw, intent = await asyncio.gather(
        loop.run_in_executor(None, lambda: llm.invoke([HumanMessage(content=prompt_tecnico)]).content.replace('"', "").strip()),
        clasificar_intencion(query_segura, llm),
    )
    query_tecnica = query_tecnica_raw[:3000]

    contexto_fallos = "(No se consultó la base de jurisprudencia)"
    contexto_leyes  = "(No se consultó el Digesto Provincial)"

    if intent == INTENT_CONVERSACION:
        return contexto_fallos, contexto_leyes, intent

    if intent in (INTENT_FALLOS, INTENT_AMBOS):
        docs_f = await _busqueda_dual_en_vdb(query_segura, query_tecnica, vdb_fallos)
        contexto_fallos = _formatear_docs_fallos(docs_f)

    if intent in (INTENT_LEYES, INTENT_AMBOS):
        # LLAMAMOS A LAS APIs PROVINCIAL Y MUNICIPAL EN PARALELO
        task_provincial = buscar_leyes_api_chubut(query_segura, llm)
        task_municipal = buscar_ordenanzas_municipal(query_segura, llm)
        
        res_provincial, res_municipal = await asyncio.gather(task_provincial, task_municipal)
        
        contexto_leyes = (
            "=== LEYES PROVINCIALES (CHUBUT) ===\n" + res_provincial + "\n\n" +
            "=== ORDENANZAS MUNICIPALES (COMODORO RIVADAVIA) ===\n" + res_municipal
        )

    return contexto_fallos, contexto_leyes, intent

# ══════════════════════════════════════════════════════════════════
# 6. SYSTEM PROMPT CON CORTAFUEGOS DE CONTEXTO
# ══════════════════════════════════════════════════════════════════
def build_system_prompt(contexto_fallos: str, contexto_leyes: str, intent: str) -> str:
    if intent == INTENT_CONVERSACION:
        bloque_contexto = "El usuario está haciendo una pregunta de seguimiento o conversacional. Respondé de forma fluida y natural usando tu memoria de la conversación."
    elif intent == INTENT_FALLOS:
        bloque_contexto = f"══ BLOQUE A — JURISPRUDENCIA (fallos y sentencias judiciales) ══\n{contexto_fallos}\n══════════════════════════════════════════════════════════════"
    elif intent == INTENT_LEYES:
        bloque_contexto = f"══ BLOQUE B — DIGESTO PROVINCIAL API EN VIVO (leyes, decretos) ══\n{contexto_leyes}\n══════════════════════════════════════════════════════════════"
    else:
        bloque_contexto = f"══ BLOQUE A — JURISPRUDENCIA (fallos y sentencias judiciales) ══\n{contexto_fallos}\n══════════════════════════════════════════════════════════════\n\n══ BLOQUE B — DIGESTO PROVINCIAL API EN VIVO (leyes, decretos) ══\n{contexto_leyes}\n══════════════════════════════════════════════════════════════"

    return f"""Sos Chubut.IA, el asistente jurídico experto de la Provincia del Chubut.

{bloque_contexto}

════════════════════ REGLAS ABSOLUTAS ════════════════════════

REGLA 1 — CORTAFUEGOS DE CONTEXTO (crítica):
Las fuentes BLOQUE A (jurisprudencia) y BLOQUE B (legislación) son independientes.
NUNCA mezcles un fallo con una ley en la misma cita.
NUNCA uses un link de jurisprudencia (juschubut.gov.ar / Eureka) para citar una ley.

REGLA 2 — CONOCIMIENTO GENERAL Y ADVERTENCIA OBLIGATORIA:
Si el BLOQUE B indica que no se encontraron resultados, TENÉS PERMITIDO responder utilizando tu conocimiento general.
⚠️ ATENCIÓN: Si usás tu conocimiento general porque la API no trajo resultados, estás ESTRICTAMENTE OBLIGADO a agregar este texto exacto al final de tu respuesta:
"⚠️ *Nota: Esta respuesta se basa en mi conocimiento general.*"

REGLA 3 — CONVERSACIÓN FLUIDA EN SEGUIMIENTOS:
Si el usuario pide resumir, explicar mejor, o hace una pregunta sobre algo que ya mencionaste en el mensaje anterior, respondé de forma natural y conversacional.

════════════════════ FORMATOS DE RESPUESTA ═══════════════════

FORMATO PARA FALLOS (usá este cuando presentes jurisprudencia):
📌 **[Título Descriptivo del Caso]**
* 📅 **Fecha del Fallo:** [AAAA] (Atención: Extraé y devolvé ÚNICAMENTE el año, ej: 2009. Bajo ninguna circunstancia incluyas días o meses)
* 📖 **Cita Textual:** "[fragmento con sustancia jurídica del BLOQUE A]"
* 📝 **Resumen:** [qué trataba el caso]
* ⚖️ **Resolución:** [decisión del juez, si figura]
* 🔗 **Ver fallo oficial:** [Link al PDF oficial](URL_EXACTA_DEL_BLOQUE_A)

FORMATO PARA LEYES (usá este cuando presentes normativa del BLOQUE B):
📜 **[Número Completo de la Norma]**
* 🏛️ **Rama:** [rama del BLOQUE B]
* ✅ **Estado:** [estado del BLOQUE B]
* 📋 **Artículo relevante o Resumen:** "[texto literal o explicación clara]"
* 🔗 **Ver documento:** <a href="[Insertá exactamente el LINK_OFICIAL provisto en el BLOQUE B]" target="_blank" rel="noopener noreferrer">Abrir Ley en el Digesto Oficial (Nueva Pestaña)</a>

FORMATO OBLIGATORIO PARA ORDENANZAS MUNICIPALES (CADA ORDENANZA DEBE LLEVAR SU LINK):
🏛️ **[Número de Ordenanza]**
* 📅 **Fecha:** [Fecha]
* 📋 **Tema:** [Tema]
* 🔗 **Ver documento:** <a href="[Insertá exactamente el LINK provisto en la base]" target="_blank" rel="noopener noreferrer">Abrir Ordenanza Municipal (Nueva Pestaña)</a>
* 📝 **Resumen Detallado:** [Explicación del contenido extraído del PDF]

FORMATO MIXTO (cuando la respuesta combina ambas fuentes):
Presentá primero la legislación aplicable (BLOQUE B) y luego la jurisprudencia que la interpreta o aplica (BLOQUE A).
════════════════════════════════════════════════════════════════"""

# ══════════════════════════════════════════════════════════════════
# 7. GENERACIÓN DE RESPUESTA
# ══════════════════════════════════════════════════════════════════
async def generate_response(contexto_fallos: str, contexto_leyes: str, intent: str, historial_completo: list[dict]) -> str:
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
    llm = get_llm()
    loop = asyncio.get_event_loop()
    prompt = f"Resumí esta consulta legal en 3 o 4 palabras: '{primer_mensaje[:500]}'"
    titulo = await loop.run_in_executor(None, lambda: llm.invoke([HumanMessage(content=prompt)]).content.replace('"', "").strip())
    return titulo
