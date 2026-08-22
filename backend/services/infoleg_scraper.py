"""
================================================================
CHUBUT.IA — SCRAPER INFOLEG (LEGISLACIÓN NACIONAL)
================================================================
Replica la arquitectura de `comodoro_scraper.py`: recibe una palabra
clave, simula la búsqueda en el sitio oficial y devuelve una lista de
diccionarios con la norma y su texto ya limpio.

✅ PAYLOAD Y ENDPOINTS CONFIRMADOS (via DevTools → Copy as cURL):
El bug de "siempre devuelve la portada" tuvo dos causas encadenadas:

  1) La URL de PROCESAMIENTO no es la misma que la del FORMULARIO:
     GET  mostrarBusquedaNormas.do  → muestra el formulario vacío y
          crea la sesión.
     POST buscarNormas.do           → procesa la búsqueda real.

  2) Struts incrusta el jsessionid directamente en el atributo
     `action` del <form> devuelto por mostrarBusquedaNormas.do (ej:
     `action="/infolegInternet/buscarNormas.do;jsessionid=XYZ..."`).
     Si se postea a una URL "limpia" como
     `https://.../buscarNormas.do` (sin ese `;jsessionid=...`), el
     servidor no logra asociar el POST con la sesión recién creada y
     devuelve la portada por defecto en vez de ejecutar la búsqueda.

Por eso el código ahora SIEMPRE parsea el `action` real del `<form>`
devuelto por el GET a mostrarBusquedaNormas.do y postea a esa URL
exacta (con `urllib.parse.urljoin`, que conserva el jsessionid si
está presente), en vez de asumir una URL fija.

El payload en sí (sin ningún token ni botón oculto) es exactamente
este, con `texto` como único campo que varía:
    tipoNorma= numero= anioSancion= texto=<palabra_clave> dependencia=
    diaPubDesde= mesPubDesde=0 anioPubDesde= diaPubHasta= mesPubHasta=0
    anioPubHasta=

La URL de ficha de norma (`verNorma.do?id=...`) sigue confirmada y es
la que se usa para extraer el texto completo de cada resultado.
"""

import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

BASE_URL = "https://servicios.infoleg.gob.ar/infolegInternet/"
FORM_URL = BASE_URL + "mostrarBusquedaNormas.do"   # GET: muestra el formulario y crea la sesión
SEARCH_ACTION_URL = BASE_URL + "buscarNormas.do"   # POST: procesa la búsqueda real
ENCODING = "iso-8859-1"  # InfoLEG todavía sirve HTML en Latin-1, no UTF-8

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _payload_busqueda(palabra_clave: str) -> dict:
    """
    Payload hardcodeado 1:1 con el capturado en DevTools (Copy as cURL).
    Todos los campos van vacíos salvo `texto` (la palabra clave) y los
    dos selects de mes, que el propio sitio manda en "0" por defecto.

    El motor de búsqueda de InfoLEG matchea cada palabra del campo
    `texto` por separado si no van entre comillas. Con una frase como
    "contrato de trabajo" sin comillas, la palabra "de" sola matchea
    casi toda la base de datos (~410 mil normas) y el resultado queda
    ordenado por fecha de publicación, por eso siempre aparecían los
    últimos DNU en vez de resultados relevantes. Envolver la frase en
    comillas dobles fuerza la búsqueda de frase exacta.
    """
    frase_exacta = f'"{palabra_clave}"'
    return {
        "tipoNorma": "",
        "numero": "",
        "anioSancion": "",
        "texto": frase_exacta,
        "dependencia": "",
        "diaPubDesde": "",
        "mesPubDesde": "0",
        "anioPubDesde": "",
        "diaPubHasta": "",
        "mesPubHasta": "0",
        "anioPubHasta": "",
    }


def _payload_busqueda_string(palabra_clave: str) -> str:
    """
    Igual que _payload_busqueda pero como STRING crudo pre-codificado,
    replicando carácter por carácter el --data-raw del cURL capturado
    (espacios como '+', igual que hace el navegador en
    application/x-www-form-urlencoded). Se usa como alternativa por si
    el urlencode automático de `requests` con un dict difiere en algo
    sutil (orden de campos, codificación de vacíos, etc.) de lo que
    espera este backend Struts tan viejo.

    También envuelve la frase en comillas dobles (ver docstring de
    _payload_busqueda) para forzar búsqueda de frase exacta; quote_plus
    codifica las comillas como %22 automáticamente.
    """
    texto_encoded = urllib.parse.quote_plus(f'"{palabra_clave}"')
    return (
        f"tipoNorma=&numero=&anioSancion=&texto={texto_encoded}&dependencia="
        f"&diaPubDesde=&mesPubDesde=0&anioPubDesde="
        f"&diaPubHasta=&mesPubHasta=0&anioPubHasta="
    )


def _headers_navegador_completos(referer: str) -> dict:
    """
    Réplica 1:1 de TODOS los headers vistos en el cURL capturado con
    DevTools (Copy as cURL), incluidos los Sec-Fetch-* y sec-ch-ua-*.
    Es poco probable que un backend Struts de esta antigüedad valide
    estos headers (son mecanismos de Chrome bastante más nuevos que el
    sitio), pero los mandamos igual para descartar esa hipótesis.
    """
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
        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="120", "Opera GX";v="106"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }


def _guardar_debug_html(nombre: str, contenido: str) -> None:
    """Guarda la respuesta cruda para poder inspeccionarla a ojo."""
    try:
        with open(f"debug_infoleg_{nombre}.html", "w", encoding="utf-8") as f:
            f.write(contenido)
    except Exception:
        pass


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
    headers = _headers_navegador_completos(referer=FORM_URL)

    try:
        # 1) GET al formulario real. Esto crea la sesión y, en Struts,
        #    suele venir con el jsessionid incrustado en el `action`.
        resp_form = session.get(FORM_URL, headers=headers, timeout=10)
        resp_form.encoding = ENCODING
        soup_form = BeautifulSoup(resp_form.text, "html.parser")
        _guardar_debug_html("01_formulario", resp_form.text)

        form_tag = soup_form.find("form")
        action = form_tag.get("action") if form_tag else None
        post_url = urllib.parse.urljoin(FORM_URL, action) if action else SEARCH_ACTION_URL

        # 2) POST a la URL dinámica, con TODOS los headers del navegador
        #    y el payload como string crudo pre-codificado (en vez de
        #    dict, para eliminar cualquier diferencia sutil de
        #    urlencode entre requests y lo que manda Chrome).
        headers_post = _headers_navegador_completos(referer=FORM_URL)
        resp_post = session.post(
            post_url,
            data=_payload_busqueda_string(palabra_clave),
            headers=headers_post,
            timeout=15,
        )
        resp_post.encoding = ENCODING
        soup_post = BeautifulSoup(resp_post.text, "html.parser")
        _guardar_debug_html("02_resultado_busqueda", resp_post.text)

        print(f"[debug] POST a: {post_url}")
        print(f"[debug] Status: {resp_post.status_code}")
        print(f"[debug] HTML de respuesta guardado en debug_infoleg_02_resultado_busqueda.html ({len(resp_post.text)} caracteres)")

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
            print(
                "⚠️  InfoLEG no devolvió resultados de búsqueda para "
                f"'{palabra_clave}'. Puede ser que esa búsqueda realmente no "
                "tenga resultados, o que el sitio haya cambiado el formulario "
                "de nuevo (repetir el Copy as cURL para confirmar)."
            )

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
    print("Buscando 'contrato de trabajo' en InfoLEG...")
    datos = buscar_normas_infoleg("contrato de trabajo")
    for item in datos:
        print(f"\n- Norma: {item['norma']} ({item['fecha']})")
        print(f"  Link: {item['link']}")
        print(f"  Extracto: {item['contenido_texto'][:200]}...")
