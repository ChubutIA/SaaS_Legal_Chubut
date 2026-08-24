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
import json

from services.infoleg_scraper import buscar_normas_infoleg
from services.comodoro_scraper import buscar_ordenanzas_comodoro
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

MODELO_DEMANDA_ALIMENTOS = """
PROMUEVE DEMANDA DE ALIMENTOS. SOLICITA ALIMENTOS PROVISORIOS. RETROACTIVIDAD. OFRECE PRUEBA
Señor/a Juez/a de Familia:
Teresa Pérez, DNI N° __________, por derecho propio y en representación de sus hijos menores de edad [NOMBRE DEL HIJO 1], de 3 años de edad, DNI N° __________, y [NOMBRE DEL HIJO 2], de 6 años de edad, DNI N° __________, con domicilio real en __________, constituyendo domicilio procesal en __________ y domicilio electrónico en __________, con el patrocinio letrado de la Dra. __________, T° ___ F° ___, a V.S. respetuosamente me presento y digo:

I. OBJETO
Que vengo a promover demanda de alimentos contra el Sr. [NOMBRE COMPLETO DEL PROGENITOR], DNI N° __________, con domicilio real en __________ y/o laboral en , a fin de que se lo condene a abonar en favor de sus hijos menores de edad una cuota alimentaria mensual equivalente a $__________, o la suma que V.S. estime adecuada conforme las necesidades de los alimentados y las posibilidades económicas del alimentante.
Asimismo, solicito que la cuota sea fijada en un porcentaje de los ingresos del demandado, incluyendo salario, sueldo anual complementario, premios, bonificaciones, comisiones, horas extras, adicionales, viáticos remunerativos y cualquier otro concepto que integre su remuneración, con un piso mínimo de $__________ mensuales.
Para el supuesto de que el demandado no registre ingresos formales suficientes o resulte trabajador independiente, solicito que la cuota sea fijada prudencialmente conforme su capacidad económica real y las necesidades de los niños.
Asimismo, solicito:
a) se fijen alimentos provisorios desde el inicio del proceso;
b) se reconozca la retroactividad de la obligación alimentaria desde la interpelación fehaciente efectuada al demandado, en los términos del art. 669 del Código Civil y Comercial, siempre que se encuentren cumplidos sus presupuestos;
c) se tengan presentes y se liquiden las cuotas alimentarias devengadas e impagas;
d) se ordenen las medidas necesarias para asegurar el efectivo cumplimiento de la cuota alimentaria;
e) oportunamente, se haga lugar a la demanda, con costas al demandado.

II. HECHOS
La suscripta es madre de los niños [NOMBRE HIJO 1], actualmente de 3 años de edad, y [NOMBRE HIJO 2], actualmente de 6 años de edad, conforme surge de las partidas de nacimiento que se acompañan.
Ambos niños son hijos del demandado, Sr. [NOMBRE DEL PROGENITOR], encontrándose debidamente acreditado el vínculo filial.
Los niños conviven con su madre, quien tiene a su cargo de manera cotidiana y permanente su cuidado personal, atendiendo sus necesidades de alimentación, vivienda, vestimenta, higiene, educación, salud, recreación y demás requerimientos propios de su edad.
La totalidad de dichas tareas implican una considerable dedicación personal y económica por parte de esta progenitora, constituyendo asimismo un aporte a la manutención de los hijos, conforme lo establecido por el art. 660 del Código Civil y Comercial.
El progenitor demandado, pese a encontrarse obligado legalmente a contribuir a la manutención de sus hijos, ha incumplido con su obligación alimentaria durante aproximadamente seis meses, sin efectuar los aportes necesarios y suficientes para atender las necesidades de los niños.
Esta situación ha obligado a la progenitora conviviente a afrontar prácticamente en soledad los gastos ordinarios y extraordinarios derivados de la crianza de ambos hijos.
Debe destacarse que las necesidades de los niños son actuales, permanentes y propias de su edad, comprendiendo alimentación, vivienda, servicios, vestimenta, calzado, educación, útiles, transporte, atención médica, medicamentos, actividades recreativas y demás gastos indispensables para su desarrollo integral.

III. ETAPA PREJUDICIAL
Con carácter previo a la promoción de la presente acción se llevó adelante la correspondiente etapa prejudicial, conforme surge de las constancias que se acompañan.
En dicha instancia se procuró alcanzar un acuerdo respecto de la contribución alimentaria que corresponde al progenitor demandado.
Sin embargo, no fue posible arribar a un acuerdo, razón por la cual resulta necesario acudir a la vía judicial a fin de obtener la determinación de una cuota alimentaria adecuada y suficiente para los niños.
[INDICAR AQUÍ: fecha de audiencia, organismo interviniente, número de expediente/acta y resultado de la audiencia.]
Asimismo, para el supuesto de corresponder, se deja expresamente planteado que el demandado fue interpelado en forma fehaciente con fecha __/__/____, mediante __________, sin que haya regularizado su obligación alimentaria.

IV. NECESIDADES DE LOS ALIMENTADOS
Los niños cuentan actualmente con 3 y 6 años de edad, encontrándose en plena etapa de crecimiento y desarrollo, circunstancia que determina necesidades alimentarias, educativas, sanitarias y recreativas que deben ser atendidas de manera continua.
A título meramente enunciativo, los gastos comprenden:
- alimentación diaria;
- vivienda y servicios correspondientes al hogar;
- vestimenta y calzado;
- gastos escolares, cuotas, materiales y útiles;
- transporte;
- atención médica;
- medicamentos y tratamientos;
- obra social/prepaga, en caso de corresponder;
- actividades recreativas y deportivas;
- higiene y cuidado personal;
- gastos extraordinarios propios de la crianza.
La enumeración precedente no resulta taxativa, toda vez que el concepto de alimentos comprende las necesidades materiales y aquellas vinculadas con el desarrollo integral de los niños.

V. CAPACIDAD ECONÓMICA DEL DEMANDADO
El demandado se desempeña como [empleado/trabajador independiente/comerciante/profesional/otro], desarrollando su actividad en __________.
Según conocimiento de esta parte, percibiría aproximadamente la suma de $__________ mensuales, sin perjuicio de los restantes ingresos y/o beneficios económicos que pudiera obtener.
Asimismo, [indicar, si se conoce: posee vehículo / desarrolla actividad comercial / es titular de inmueble / trabaja para determinada empresa / percibe ingresos por actividad independiente / posee otros recursos económicos].
La información relativa a sus ingresos se denuncia de manera aproximada, toda vez que la progenitora carece de acceso a la totalidad de la información patrimonial y laboral del demandado.
Por ello, resulta indispensable la producción de la prueba informativa ofrecida en autos, a efectos de determinar su verdadera capacidad económica.

VI. DERECHO
Fundo la presente acción en lo dispuesto por los arts. 658, 659, 660, 661, 669 y concordantes del Código Civil y Comercial de la Nación, en cuanto establecen el deber de ambos progenitores de proveer alimentos a sus hijos, determinan el contenido de la obligación alimentaria, reconocen valor económico a las tareas de cuidado y regulan la obligación respecto de los alimentos impagos.
El art. 658 establece que ambos progenitores tienen la obligación de criar, alimentar y educar a sus hijos conforme a su condición y fortuna.
A su vez, el art. 659 dispone que los alimentos comprenden las necesidades de manutención, educación, esparcimiento, vestimenta, habitación, asistencia, gastos por enfermedad y demás gastos necesarios, y que deben ser proporcionales a las posibilidades económicas de los obligados y a las necesidades de los alimentados.
Por su parte, el art. 660 reconoce expresamente el valor económico de las tareas cotidianas realizadas por el progenitor que tiene a su cargo el cuidado personal de los hijos.
Finalmente, el art. 669 establece que los alimentos se deben desde el día de la demanda o desde la interpelación fehaciente del obligado, cuando la demanda se interpone dentro de los seis meses de aquella.
La obligación alimentaria constituye, además, una manifestación concreta de los deberes derivados de la responsabilidad parental y debe ser interpretada conforme al principio del interés superior de los niños.

VII. ALIMENTOS PROVISORIOS
Atento a la edad de los niños, la naturaleza de las necesidades involucradas y el incumplimiento denunciado, solicito que V.S. fije alimentos provisorios desde el inicio de las presentes actuaciones, sin necesidad de aguardar el dictado de la sentencia definitiva.
La urgencia surge de la propia naturaleza de la prestación reclamada, destinada a cubrir necesidades cotidianas que no admiten demora.
Solicito que dicha cuota provisoria sea fijada en la suma de $__________ mensuales, o en el porcentaje de los ingresos del demandado que V.S. estime corresponder.
Para el caso de que el demandado se encuentre registrado como trabajador en relación de dependencia, solicito se ordene a su empleador la retención directa de la cuota fijada y su depósito en la cuenta judicial que se habilite al efecto.

VIII. RETROACTIVIDAD. ALIMENTOS DEVENGADOS
Solicito que la sentencia determine la retroactividad de la obligación alimentaria conforme al art. 669 del Código Civil y Comercial.
En particular, habiendo mediado interpelación fehaciente con fecha __/__/____, solicito que la obligación sea establecida desde dicha fecha, en tanto la presente acción se interpone dentro del plazo legal.
Asimismo, dejo planteado el derecho de esta parte a reclamar los gastos afrontados por la progenitora conviviente correspondientes al período anterior, en la medida y con el alcance que legalmente corresponda.

IX. PRUEBA
A. DOCUMENTAL
Se acompaña:
- Partida de nacimiento de [NOMBRE HIJO 1].
- Partida de nacimiento de [NOMBRE HIJO 2].
- Constancia de DNI de los niños.
- Constancia de DNI de la progenitora.
- Constancia de la etapa prejudicial realizada.
- Acta de cierre/falta de acuerdo.
- Intimación/interpelación fehaciente al demandado, en caso de corresponder.
- Comprobantes de gastos de los niños.
- Constancias escolares.
- Comprobantes de gastos médicos, medicamentos y/o cobertura de salud.
- Toda otra documentación que acredite las necesidades de los alimentados.

B. INFORMATIVA
Solicito se libren oficios a:
1. AFIP/ARCA: a fin de que informe si el demandado se encuentra inscripto, actividad declarada, categoría, empleadores registrados, remuneraciones declaradas y demás información que resulte pertinente.
2. ANSES: a fin de que informe si el demandado registra beneficios, prestaciones, jubilaciones, pensiones, asignaciones o cualquier otro ingreso registrado.
3. [EMPLEADOR]: para que informe remuneración mensual, conceptos que integran la misma, adicionales, premios, horas extras, bonificaciones, antigüedad, SAC y demás conceptos percibidos por el demandado.
4. Entidades bancarias correspondientes: para que informen, en caso de resultar procedente y conforme las facultades judiciales, la información patrimonial que corresponda.
5. Registro de la Propiedad Inmueble: a fin de que informe bienes inmuebles registrados a nombre del demandado.
6. Registro de la Propiedad Automotor: a fin de que informe vehículos registrados a nombre del demandado.
Todo ello a fin de determinar la real capacidad económica del alimentante.

C. TESTIMONIAL
Se ofrece la declaración testimonial de:
- ____________________, DNI __________, domicilio __________.
- ____________________, DNI __________, domicilio __________.
- ____________________, DNI __________, domicilio __________.
Los testigos declararán acerca de la convivencia de los niños con su madre, las tareas de cuidado asumidas por ésta, las necesidades de los alimentados, los gastos afrontados y las circunstancias económicas conocidas del demandado.

X. INFORME SOCIOAMBIENTAL
Para el supuesto de estimarlo necesario, solicito se disponga la realización de informe socioambiental en el domicilio donde viven los niños, a fin de acreditar sus condiciones de vida, necesidades y circunstancias familiares.

XI. INTERÉS SUPERIOR DE LOS NIÑOS
La pretensión debe ser analizada teniendo especialmente en consideración el interés superior de los niños involucrados, quienes cuentan con 3 y 6 años de edad y requieren una tutela judicial efectiva y oportuna.
La falta de cumplimiento de la obligación alimentaria no puede traducirse en que la totalidad de las cargas derivadas de la crianza recaigan sobre la progenitora conviviente.
La obligación corresponde a ambos progenitores y debe distribuirse de acuerdo con las necesidades de los niños y las posibilidades económicas de cada obligado.

XII. PETITORIO
Por todo lo expuesto, a V.S. solicito:
1. Me tenga por presentada, parte y con el domicilio constituido.
2. Tenga por promovida demanda de alimentos contra el Sr. [NOMBRE COMPLETO DEL PROGENITOR], DNI N° __________.
3. Tenga por acreditada la legitimación de la progenitora para reclamar alimentos en representación de sus hijos menores.
4. Se tengan por acompañadas las constancias de la etapa prejudicial y se tenga por cumplida dicha instancia.
5. Se fijen alimentos provisorios en favor de los niños por la suma de $__________ mensuales o el porcentaje de los ingresos que V.S. estime corresponder.
6. Se ordene, de corresponder, la retención directa de la cuota alimentaria sobre los haberes del demandado.
7. Se tenga presente la interpelación fehaciente efectuada con fecha __/__/____ y se establezca la retroactividad de la obligación conforme el art. 669 del Código Civil y Comercial.
8. Se ordene la producción de la prueba ofrecida.
9. Oportunamente, se haga lugar a la demanda y se fije una cuota alimentaria definitiva de $__________ mensuales, o el porcentaje de los ingresos del demandado que resulte adecuado, con los ajustes que correspondan.
10. Se establezca la forma y fecha de pago de las cuotas.
11. Se condene al demandado al pago de las cuotas alimentarias devengadas e impagas que correspondan.
12. Se impongan las costas al demandado.
Proveer de conformidad,
SERÁ JUSTICIA.
"""
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
# 3b. CLASIFICADOR DE JURISDICCIÓN (provincial/municipal vs nacional)
# ══════════════════════════════════════════════════════════════════
_PATRONES_NACIONAL = re.compile(
    r"\b(naci[oó]n(al)?|argentin[oa]|c[oó]digo civil|c[oó]digo penal|c[oó]digo de comercio|"
    r"c[oó]digo civil y comercial|contrato de trabajo|\blct\b|constituci[oó]n nacional|"
    r"defensa del consumidor|24\.?240|infoleg|boletín oficial(?! de chubut)|congreso de la naci[oó]n)\b",
    re.IGNORECASE
)
_PATRONES_PROVINCIAL = re.compile(
    r"\b(chubut|comodoro( rivadavia)?|provincial|municipal|ordenanza|digesto|legislatura del chubut)\b",
    re.IGNORECASE
)

async def clasificar_jurisdiccion(query: str, llm: ChatOpenAI) -> str:
    """Devuelve 'nacional', 'provincial' o 'ambas'."""
    q = query.lower()
    tiene_nacional = bool(_PATRONES_NACIONAL.search(q))
    tiene_provincial = bool(_PATRONES_PROVINCIAL.search(q))

    if tiene_nacional and not tiene_provincial:
        return "nacional"
    if tiene_provincial and not tiene_nacional:
        return "provincial"
    if tiene_nacional and tiene_provincial:
        return "ambas"

    # Ninguna palabra clave disparó: le preguntamos a la IA
    prompt = (
        f"Clasificá si esta consulta legal es sobre normativa NACIONAL argentina "
        f"(leyes del Congreso, códigos, Constitución Nacional) o PROVINCIAL/MUNICIPAL "
        f"(Chubut, Comodoro Rivadavia, ordenanzas). Respondé solo: nacional, provincial o ambas.\n"
        f"Consulta: '{query[:500]}'"
    )
    loop = asyncio.get_event_loop()
    try:
        resultado = await loop.run_in_executor(None, lambda: llm.invoke([HumanMessage(content=prompt)]).content)
        r = resultado.strip().lower()
        if "nacional" in r and "provincial" not in r:
            return "nacional"
        if "provincial" in r and "nacional" not in r:
            return "provincial"
        return "ambas"
    except Exception:
        return "provincial"  # fallback: mantiene el comportamiento actual del sistema


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

async def buscar_leyes_nacionales_infoleg(query_usuario: str, llm: ChatOpenAI) -> str:
    """
    Extrae tipo_norma + numero estructurados (el ÚNICO combo que
    InfoLEG resuelve a una norma exacta) y, si no hay número
    identificable, cae a texto_libre como último recurso.
    """
    loop = asyncio.get_event_loop()

    prompt = (
        "Analizá esta consulta legal y respondé ÚNICAMENTE un JSON (sin "
        "markdown, sin backticks, sin texto adicional) con esta forma:\n"
        '{"tipo_norma": "...", "numero": "...", "texto_libre": "..."}\n\n'
        "Reglas:\n"
        "1) Si la consulta menciona un número de norma (ley, decreto, resolución, etc.): "
        "completá 'tipo_norma' con el tipo genérico (Ley, Decreto, Resolución, Decreto-Ley, etc.) "
        "y 'numero' con el número COMPLETO incluyendo la barra y el año si lo tiene, pero SIN puntos "
        "(ej: 'Ley 24.240' → numero=\"24240\". 'Decreto 274/2019' → numero=\"274/2019\"). "
        "Dejá 'texto_libre' en null.\n"
        "2) Si NO hay número identificable (consulta conceptual, ej. "
        "'código civil y comercial' o 'contrato de trabajo' sin número): "
        'dejá "tipo_norma" y "numero" en null, y completá "texto_libre" '
        "con 2 a 4 palabras clave (sin comillas, sin puntuación).\n"
        "3) Nunca agregues explicaciones fuera del JSON.\n\n"
        f"Consulta: '{query_usuario}'"
    )

    try:
        respuesta_llm = await loop.run_in_executor(
            None, lambda: llm.invoke([HumanMessage(content=prompt)]).content
        )
        # Extracción a prueba de balas: buscamos el bloque JSON usando Regex
        match = re.search(r'\{.*\}', respuesta_llm, re.DOTALL)
        if match:
            datos = json.loads(match.group(0))
        else:
            datos = {}
            
        tipo_norma = datos.get("tipo_norma")
        numero = datos.get("numero")
        texto_libre = datos.get("texto_libre")
    except Exception:
        # Si el JSON viene roto, probamos como texto libre
        tipo_norma, numero, texto_libre = None, None, query_usuario

    try:
        resultados = await loop.run_in_executor(
            None,
            lambda: buscar_normas_infoleg(tipo_norma=tipo_norma, numero=numero, texto_libre=texto_libre),
        )
        if not resultados:
            return f"(No se encontraron normas nacionales en InfoLEG para tipo='{tipo_norma}' numero='{numero}' texto='{texto_libre}'.)"

        textos = []
        for item in resultados:
            textos.append(
                f"📜 NORMA: {item['norma']}\n"
                f"📅 FECHA: {item['fecha']}\n"
                f"📝 TEMA: {item['tema']}\n"
                f"🔗 LINK_OFICIAL: {item['link']}\n"
                f"📄 TEXTO:\n{item['contenido_texto']}"
            )
        return "\n\n".join(textos)
    except Exception:
        return "(Error al consultar InfoLEG.)"
# ══════════════════════════════════════════════════════════════════
# 5. SÚPER BÚSQUEDA DUAL
# ══════════════════════════════════════════════════════════════════
async def super_search(query_usuario: str, historial_previo: list[dict], llm: ChatOpenAI, vdb_fallos: Chroma, vdb_leyes: Chroma | None) -> tuple[str, str, str]:
    loop = asyncio.get_event_loop()

    if historial_previo:
        hist_texto = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in historial_previo[-3:]])
        prompt_ref = (
            f"Basado en esta charla previa:\n{hist_texto}\n\n"
            f"Reescribí la siguiente pregunta del usuario para que sea una consulta de búsqueda independiente. "
            f"REGLA VITAL: Si el usuario introduce un tema NUEVO (ej. menciona una ley, decreto o número nuevo), dejá la pregunta EXACTAMENTE como está, NO le agregues contexto viejo. "
            f"Solo usá la charla previa si el usuario dice 'esa ley', 'ese artículo', o hace referencia directa a lo anterior.\n"
            f"Pregunta del usuario: '{query_usuario[:1500]}'. Solo devolvé la pregunta final, sin comillas."
        )
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
        jurisdiccion = await clasificar_jurisdiccion(query_segura, llm)
        if jurisdiccion not in ("nacional", "provincial", "ambas"):
            jurisdiccion = "ambas" # Fallback de seguridad extrema

        tareas: list = []
        etiquetas: list[str] = []

        if jurisdiccion in ("provincial", "ambas"):
            tareas.append(buscar_leyes_api_chubut(query_segura, llm))
            etiquetas.append("LEYES PROVINCIALES (CHUBUT)")
            tareas.append(buscar_ordenanzas_municipal(query_segura, llm))
            etiquetas.append("ORDENANZAS MUNICIPALES (COMODORO RIVADAVIA)")

        if jurisdiccion in ("nacional", "ambas"):
            tareas.append(buscar_leyes_nacionales_infoleg(query_segura, llm))
            etiquetas.append("LEGISLACIÓN NACIONAL (INFOLEG)")

        resultados_busqueda = await asyncio.gather(*tareas)

        contexto_leyes = "\n\n".join(
            f"=== {etiqueta} ===\n{resultado}"
            for etiqueta, resultado in zip(etiquetas, resultados_busqueda)
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
Las fuentes de Jurisprudencia (BLOQUE A) y Legislación (BLOQUE B) son totalmente independientes.
- NUNCA mezcles links entre bloques. Usa el link provisto en cada sección.

REGLA 2 — USO DE INFORMACIÓN Y ADVERTENCIAS:
- Si el BLOQUE B contiene el texto de una ley, DEBES usar esa información para responder. Usa tu capacidad analítica para interpretar el texto legal provisto y responder la duda del usuario (ej: interpretar el Artículo 34 para compras por internet). No agregues advertencias si estás interpretando el texto provisto.
- ⚠️ SOLO si el BLOQUE B dice explícitamente "(No se encontraron normas...)", entonces usa tu conocimiento general y estás OBLIGADO a agregar este texto exacto al principio de tu respuesta: "⚠️ *Nota: Esta respuesta se basa en mi conocimiento general.*"

REGLA 3 — CONVERSACIÓN FLUIDA EN SEGUIMIENTOS:
Si el usuario pide resumir o hace una pregunta de seguimiento, responde de forma natural.

REGLA 4 — GENERACIÓN DE DEMANDAS DE ALIMENTOS (ESTRICTA):
Si el usuario te pide redactar, armar o escribir una demanda de alimentos, DEBES utilizar obligatoria y estrictamente la siguiente plantilla de modelo. 
Reemplazá los datos faltantes con la información específica que te provea el usuario en su consulta (nombres, DNI, montos, etc.). 
Si el usuario no te da un dato, dejá los corchetes [ ] o el espacio en blanco (____) para que lo complete luego en su estudio. 
NO inventes formatos nuevos, NO alteres la numeración romana, y NO agregues secciones que no estén en la plantilla.

PLANTILLA OFICIAL A UTILIZAR:
{MODELO_DEMANDA_ALIMENTOS}

════════════════════ FORMATOS DE RESPUESTA ═══════════════════

FORMATO PARA FALLOS:
📌 **[Título Descriptivo del Caso]**
* 📅 **Fecha del Fallo:** [AAAA]
* 📖 **Cita Textual:** "[fragmento del BLOQUE A]"
* 📝 **Resumen:** [qué trataba el caso]
* 🔗 **Ver fallo oficial:** [Link al PDF oficial]

FORMATO PARA LEYES PROVINCIALES (Digesto Chubut):
📜 **[Número Completo de la Norma]**
* 🏛️ **Rama:** [rama del BLOQUE B]
* ✅ **Estado:** [estado del BLOQUE B]
* 📋 **Análisis:** [tu explicación basada en el texto]
* 🔗 **Ver documento oficial:** <a href="[LINK_OFICIAL del BLOQUE B]" target="_blank" rel="noopener noreferrer">Abrir Norma en el Digesto Oficial (Nueva Pestaña)</a>

FORMATO PARA LEGISLACIÓN NACIONAL (InfoLEG):
📜 **[Número Completo de la Norma] - [Nombre de la Norma]**
* 🏛️ **Rama:** Nacional
* ✅ **Estado:** Vigente (salvo indicación contraria)
* 📋 **Análisis:** [tu explicación basada en el texto]
* 🔗 **Ver normativa:** [Abrir Ley en InfoLEG](PONER_AQUÍ_EL_LINK_OFICIAL_DEL_BLOQUE_B)

FORMATO PARA ORDENANZAS MUNICIPALES:
🏛️ **[Número de Ordenanza]**
* 📅 **Fecha:** [Fecha]
* 📋 **Tema:** [Tema]
* 🔗 **Ver documento:** <a href="[LINK del BLOQUE B]" target="_blank" rel="noopener noreferrer">Abrir Ordenanza Municipal (Nueva Pestaña)</a>
* 📝 **Resumen:** [Explicación]

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
