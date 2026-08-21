"""
================================================================
CHUBUT.IA — SCRAPER INFOLEG (LEGISLACIÓN NACIONAL)
================================================================
Replica la arquitectura de `comodoro_scraper.py`: recibe una palabra
clave, simula la búsqueda en el sitio oficial y devuelve una lista de
diccionarios con la norma y su texto ya limpio, en un formato análogo
al que usa el scraper municipal (norma / fecha / tema / link / texto).

✅ CAMPO DE BÚSQUEDA CONFIRMADO (via DevTools / Network → Payload):
El input de texto libre del formulario de InfoLEG se llama `texto`.
Ese es el valor que se usa como CAMPO_TEXTO_CONFIRMADO más abajo y es
el que se manda en el payload de la búsqueda.

El resto de los campos del formulario (tipo de norma, número, año,
dependencia, fechas) se siguen leyendo dinámicamente del HTML real
(igual que se hace con el VIEWSTATE de ASP.NET en comodoro_scraper.py),
para no romper la búsqueda si el sitio agrega algún token oculto
(CSRF, sessionid, etc). Solo se sobreescribe el campo `texto` con la
palabra clave de la consulta; el resto de los campos queda con su
valor por defecto del formulario.

La URL de ficha de norma (`verNorma.do?id=...`) también está
confirmada y es la que se usa para extraer el texto completo.
"""

import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

BASE_URL = "https://servicios.infoleg.gob.ar/infolegInternet/"
SEARCH_URL = BASE_URL + "buscarNormas.do"
ENCODING = "iso-8859-1"  # InfoLEG todavía sirve HTML en Latin-1, no UTF-8

# Confirmado interceptando la petición real (Network → Payload).
CAMPO_TEXTO_CONFIRMADO = "texto"


def _extraer_campos_formulario(soup: BeautifulSoup, form_id_o_name: str = None) -> dict:
    """
    Igual que hacemos con __VIEWSTATE en comodoro_scraper.py: en vez de
    adivinar los inputs, los leemos todos del HTML real para no romper
    la búsqueda si el sitio tiene tokens ocultos (CSRF, sessionid, etc).
    """
    form = soup.find("form")
    campos = {}
    if not form:
        return campos

    for input_tag in form.find_all(["input", "select"]):
        name = input_tag.get("name")
        if not name:
            continue
        if input_tag.name == "select":
            # Tomamos la primera opción como valor por defecto
            option = input_tag.find("option")
            campos[name] = option.get("value", "") if option else ""
        else:
            campos[name] = input_tag.get("value", "")

    return campos


def buscar_normas_infoleg(palabra_clave: str, max_resultados: int = 3) -> list:
    """
    Busca normativa nacional en InfoLEG por palabra clave y devuelve
    una lista de diccionarios con la misma forma que usa el resto del
    proyecto para pasarle contexto a la IA:
        {
            "norma": "Ley 24.240",
            "fecha": "1993-09-22",
            "tema": "Defensa del Consumidor",
            "link": "https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=638",
            "contenido_texto": "...texto limpio de la norma..."
        }
    """
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # 1) GET a la página de búsqueda para levantar el formulario real
        resp_get = session.get(SEARCH_URL, headers=headers, timeout=10)
        resp_get.encoding = ENCODING
        soup_get = BeautifulSoup(resp_get.text, "html.parser")

        payload = _extraer_campos_formulario(soup_get)
        payload[CAMPO_TEXTO_CONFIRMADO] = palabra_clave

        form = soup_get.find("form")
        method = (form.get("method") if form else "get").lower()
        action = (form.get("action") if form else SEARCH_URL)
        action_url = action if action.startswith("http") else urllib.parse.urljoin(SEARCH_URL, action)

        # 2) Enviamos la búsqueda (GET o POST según lo que declare el form)
        if method == "post":
            resp_post = session.post(action_url, data=payload, headers=headers, timeout=15)
        else:
            resp_post = session.get(action_url, params=payload, headers=headers, timeout=15)
        resp_post.encoding = ENCODING
        soup_post = BeautifulSoup(resp_post.text, "html.parser")

        # 3) Extraemos los links a normas individuales (verNorma.do?id=...)
        #    Esta parte SÍ está confirmada: es el patrón real de InfoLEG.
        links_norma = []
        for a in soup_post.find_all("a", href=True):
            href = a["href"]
            if "verNorma.do" in href and "id=" in href:
                url_completa = href if href.startswith("http") else urllib.parse.urljoin(BASE_URL, href)
                titulo = a.get_text(strip=True)
                if url_completa not in [l["link"] for l in links_norma]:
                    links_norma.append({"link": url_completa, "titulo_lista": titulo})

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

        # InfoLEG no usa <article> ni divs con clases claras: nos quedamos
        # con el body completo y limpiamos scripts/estilos/menús.
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        texto_crudo = soup.get_text(separator="\n")
        # Colapsamos líneas en blanco repetidas que deja el HTML viejo
        texto_limpio = re.sub(r"\n{2,}", "\n\n", texto_crudo).strip()

        # Heurística simple para "norma" y "fecha": suele estar en el
        # primer <b> o <h1>/<h2> de la página y cerca aparece una fecha
        # con formato dd/mm/aaaa.
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
    print("Buscando 'ley de contrato de trabajo' en InfoLEG...")
    datos = buscar_normas_infoleg("ley de contrato de trabajo")
    for item in datos:
        print(f"\n- Norma: {item['norma']} ({item['fecha']})")
        print(f"  Link: {item['link']}")
        print(f"  Extracto: {item['contenido_texto'][:200]}...")
