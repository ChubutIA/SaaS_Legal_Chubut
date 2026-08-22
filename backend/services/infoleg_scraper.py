"""
================================================================
CHUBUT.IA — SCRAPER INFOLEG (LEGISLACIÓN NACIONAL)
================================================================
Replica la arquitectura de `comodoro_scraper.py`: recibe tipo + número
de norma (o, en su defecto, una frase conceptual), busca en el sitio
oficial y devuelve una lista de diccionarios con la norma y su texto
ya limpio.

✅ CÓMO FUNCIONA REALMENTE EL FORMULARIO (confirmado con ingeniería
inversa manual en el sitio, no solo con el cURL):

  1) El campo `texto` NO acepta comillas ni puntos — el sitio valida
     esos caracteres y tira "No puede contener carácteres especiales"
     en el propio formulario. Por eso la estrategia de frase exacta
     entre comillas (que usábamos antes) daba 0 resultados: ni
     siquiera llegaba a ejecutar la búsqueda, el validador la
     rechazaba antes.
  2) `texto` SIN comillas hace un match libre por cada palabra suelta.
     Con frases largas esto devuelve decenas o cientos de miles de
     normas (ej. "contrato de trabajo" ≈ 170.000), inutilizable.
  3) La ÚNICA combinación que trae la norma exacta es `tipoNorma`
     (código interno del <select>, ej. "1" para Ley) + `numero` (SIN
     puntos, ej. "24240"). Con eso el buscador filtra por norma puntual
     en vez de por texto libre.

Por eso este scraper ya NO arma una sola "palabra_clave" de texto: pide
tipo_norma + numero por separado (ai_engine.py se encarga de que el
LLM se los pase estructurados), y solo cae a búsqueda libre por
`texto` (sin comillas) como último recurso, para consultas puramente
conceptuales sin número identificable — con la advertencia de que ese
modo puede devolver un volumen alto de resultados.

✅ MAPEO DE tipoNorma CONFIRMADO POR DUMP DEL HTML (no leído en vivo):
Antes intentábamos leer el `<select name="tipoNorma">` en cada corrida
para sacar el `value` real sin adivinarlo. Roman hizo un dump directo
del HTML del formulario y confirmó que esos values son fijos y
numéricos (1=Ley, 2=Decreto, 3=Resolución, 4=Disposición, 8=Decisión
Administrativa). Como son códigos estáticos del sitio (no cambian por
sesión ni por request), hardcodearlos en `MAPEO_TIPOS_NORMA` es más
simple y más confiable que seguir parseando el `<select>` — la lectura
en vivo agregaba una petición HTTP extra y un punto de falla (mal
matching de texto de opción) sin ninguna ventaja real, ya que estos
valores no son el tipo de dato que el sitio vaya a randomizar.

GET  mostrarBusquedaNormas.do  → muestra el formulario y crea la
                                  sesión; de ahí leemos el `action`
                                  real del <form> (Struts le mete el
                                  jsessionid ahí:
                                  buscarNormas.do;jsessionid=X).
POST buscarNormas.do (URL dinámica con jsessionid) → procesa la
                                  búsqueda real.

La URL de ficha de norma (`verNorma.do?id=...`) sigue confirmada y es
la que se usa para extraer el texto completo de cada resultado.
"""

import requests
from bs4 import BeautifulSoup
import re
import unicodedata
import urllib.parse

BASE_URL = "https://servicios.infoleg.gob.ar/infolegInternet/"
FORM_URL = BASE_URL + "mostrarBusquedaNormas.do"   # GET: muestra el formulario y crea la sesión
SEARCH_ACTION_URL = BASE_URL + "buscarNormas.do"   # fallback si no se puede leer el <form>
ENCODING = "iso-8859-1"  # InfoLEG todavía sirve HTML en Latin-1, no UTF-8

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Values reales del <select name="tipoNorma">, confirmados por dump
# directo del HTML (no se leen en vivo). Claves ya normalizadas
# (minúsculas, sin tildes) para matchear con _normalizar_tipo_norma().
MAPEO_TIPOS_NORMA = {
    "ley": "1",
    "decreto": "2",
    "resolucion": "3",
    "disposicion": "4",
    "decision administrativa": "8",
}


def _headers_navegador_completos(referer: str) -> dict:
    """Réplica de los headers vistos en el cURL capturado con DevTools."""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://servicios.infoleg.gob.ar",
        "Pragma": "no-cache",
        "Referer": referer,
        "Sec-Fetch-Dest": "iframe",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": USER_AGENT,
    }


def _normalizar_tipo_norma(tipo_norma_deseado: str) -> str:
    """
    Normaliza el string que viene del LLM (minúsculas, sin tildes, sin
    espacios extra) para poder buscarlo en MAPEO_TIPOS_NORMA sin
    depender de que el LLM devuelva el texto exactamente igual a como
    está escrito en el <select>.
    """
    if not tipo_norma_deseado:
        return ""
    sin_tildes = unicodedata.normalize("NFKD", tipo_norma_deseado).encode("ascii", "ignore").decode("ascii")
    return sin_tildes.strip().lower()


def _mapear_tipo_norma(tipo_norma_deseado: str) -> str:
    """
    Devuelve el `value` numérico fijo de MAPEO_TIPOS_NORMA para el tipo
    de norma pedido. Si no matchea ninguna clave (tipo desconocido o
    vacío), asume "Ley" (value "1") por ser el tipo más común en
    consultas legales, en vez de mandar el campo vacío (que en algunos
    casos del formulario de InfoLEG puede comportarse distinto a
    "cualquier tipo").
    """
    clave = _normalizar_tipo_norma(tipo_norma_deseado)
    if clave in MAPEO_TIPOS_NORMA:
        return MAPEO_TIPOS_NORMA[clave]

    # Match parcial por si el LLM manda variantes (ej. "decreto del
    # poder ejecutivo" en vez de "decreto")
    for clave_conocida, value in MAPEO_TIPOS_NORMA.items():
        if clave_conocida in clave or clave in clave_conocida:
            return value

    return MAPEO_TIPOS_NORMA["ley"]  # fallback: asumimos Ley


def _payload_por_numero(tipo_norma_value: str, numero: str) -> dict:
    """
    Payload para búsqueda puntual por tipo + número (la ÚNICA
    combinación que InfoLEG realmente resuelve a una norma exacta).
    El número va SIN puntos ni barras de año.
    """
    numero_limpio = re.sub(r"\D", "", numero or "")
    return {
        "tipoNorma": tipo_norma_value,
        "numero": numero_limpio,
        "anioSancion": "",
        "texto": "",
        "dependencia": "",
        "diaPubDesde": "",
        "mesPubDesde": "0",
        "anioPubDesde": "",
        "diaPubHasta": "",
        "mesPubHasta": "0",
        "anioPubHasta": "",
    }


def _payload_por_texto_libre(texto_libre: str) -> dict:
    """
    Último recurso para consultas puramente conceptuales sin número
    identificable (ej. "código civil y comercial" a secas). SIN
    comillas (el campo las rechaza) y SIN garantía de resultados
    acotados — puede devolver muchísimas normas, es un fallback, no la
    vía principal.
    """
    return {
        "tipoNorma": "",
        "numero": "",
        "anioSancion": "",
        "texto": (texto_libre or "").strip(),
        "dependencia": "",
        "diaPubDesde": "",
        "mesPubDesde": "0",
        "anioPubDesde": "",
        "diaPubHasta": "",
        "mesPubHasta": "0",
        "anioPubHasta": "",
    }


def buscar_normas_infoleg(
    tipo_norma: str = None,
    numero: str = None,
    texto_libre: str = None,
    max_resultados: int = 3,
) -> list:
    """
    Busca normativa nacional en InfoLEG y devuelve una lista de
    diccionarios con la misma forma que usa el resto del proyecto para
    pasarle contexto a la IA:
        {
            "norma": "Ley 24.240",
            "fecha": "1993-09-22",
            "tema": "Defensa del Consumidor",
            "link": "https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=638",
            "contenido_texto": "...texto limpio de la norma..."
        }

    Modo preferido: pasar tipo_norma + numero (ej. "Ley", "24240").
    Fallback: si no hay numero, se usa texto_libre sin comillas (puede
    devolver muchos resultados; se recorta a max_resultados igual).
    """
    session = requests.Session()
    headers = _headers_navegador_completos(referer=FORM_URL)

    try:
        # 1) GET al formulario real: crea la sesión y nos da tanto el
        #    `action` dinámico (con jsessionid) como las opciones
        #    reales de tipoNorma.
        resp_form = session.get(FORM_URL, headers=headers, timeout=10)
        resp_form.encoding = ENCODING
        soup_form = BeautifulSoup(resp_form.text, "html.parser")

        form_tag = soup_form.find("form")
        action = form_tag.get("action") if form_tag else None
        post_url = urllib.parse.urljoin(FORM_URL, action) if action else SEARCH_ACTION_URL

        # 2) Armamos el payload según qué datos tengamos
        if numero:
            tipo_norma_value = _mapear_tipo_norma(tipo_norma)
            payload = _payload_por_numero(tipo_norma_value, numero)
        elif texto_libre:
            payload = _payload_por_texto_libre(texto_libre)
        else:
            print("⚠️  buscar_normas_infoleg: no se recibió numero ni texto_libre, no hay nada que buscar.")
            return []

        headers_post = _headers_navegador_completos(referer=FORM_URL)
        resp_post = session.post(post_url, data=payload, headers=headers_post, timeout=15)
        resp_post.encoding = ENCODING
        soup_post = BeautifulSoup(resp_post.text, "html.parser")

        # 3) Extraemos los links a normas individuales (verNorma.do?id=...)
        links_norma = []
        for a in soup_post.find_all("a", href=True):
            href = a["href"]
            if "verNorma.do" in href and "id=" in href:
                url_completa = href if href.startswith("http") else urllib.parse.urljoin(BASE_URL, href)
                titulo = a.get_text(strip=True)
                if url_completa not in [l["link"] for l in links_norma]:
                    links_norma.append({"link": url_completa, "titulo_lista": titulo})

        if not links_norma:
            print(f"⚠️  InfoLEG no devolvió resultados para tipo='{tipo_norma}' numero='{numero}' texto_libre='{texto_libre}'.")

        resultados = []
        for item in links_norma[:max_resultados]:
            detalle = _leer_norma_infoleg(session, headers, item["link"])
            resultados.append({
                "norma": detalle.get("norma") or item["titulo_lista"] or "Norma sin identificar",
                "fecha": detalle.get("fecha", "N/D"),
                "tema": detalle.get("tema", "N/D"),
                "link": item["link"],
                "contenido_texto": detalle.get("contenido_texto", "(No se pudo extraer el texto de la norma)"),
            })

        return resultados

    except Exception as e:
        print(f"Error al buscar en InfoLEG: {e}")
        return []


def _leer_norma_infoleg(session: requests.Session, headers: dict, url: str) -> dict:
    """
    Entra a la ficha de una norma (verNorma.do?id=...) y extrae texto
    limpio a partir del HTML viejo (tablas, <p>, <br>, <b> sin clases).
    """
    try:
        resp = session.get(url, headers=headers, timeout=15)
        resp.encoding = ENCODING
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        texto_crudo = soup.get_text(separator=" ")
        # Colapsamos TODO el whitespace (saltos de línea, tabs, espacios
        # múltiples que dejan las tablas de layout viejas) a un solo
        # espacio, para que quede un párrafo continuo y legible.
        texto_limpio = re.sub(r"\s+", " ", texto_crudo).strip()

        titulo_tag = soup.find(["h1", "h2", "b"])
        norma = titulo_tag.get_text(strip=True) if titulo_tag else None

        fecha_match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", texto_limpio)
        fecha = fecha_match.group(0) if fecha_match else "N/D"

        if len(texto_limpio) > 2500:
            texto_limpio = texto_limpio[:2500] + "..."

        return {
            "norma": norma,
            "fecha": fecha,
            "tema": "N/D",
            "contenido_texto": texto_limpio,
        }
    except Exception as e:
        return {"contenido_texto": f"(Error al leer la norma: {e})"}


if __name__ == "__main__":
    print("Buscando Ley 24.240...")
    datos = buscar_normas_infoleg(tipo_norma="Ley", numero="24240")
    for item in datos:
        print(f"\n- Norma: {item['norma']} ({item['fecha']})")
        print(f"  Link: {item['link']}")
        print(f"  Extracto: {item['contenido_texto'][:200]}...")
