import requests
from bs4 import BeautifulSoup
import re
import unicodedata
import urllib.parse

BASE_URL = "https://servicios.infoleg.gob.ar/infolegInternet/"
FORM_URL = BASE_URL + "mostrarBusquedaNormas.do"
SEARCH_ACTION_URL = BASE_URL + "buscarNormas.do"
ENCODING = "iso-8859-1"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Diccionario estático descubierto por ingeniería inversa
MAPEO_TIPOS_NORMA = {
    "ley": "1",
    "decreto": "2",
    "resolucion": "3",
    "disposicion": "4",
    "decision administrativa": "8",
}

def _headers_navegador_completos(referer: str) -> dict:
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://servicios.infoleg.gob.ar",
        "Pragma": "no-cache",
        "Referer": referer,
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": USER_AGENT,
    }

def _normalizar_tipo_norma(tipo_norma_deseado: str) -> str:
    if not tipo_norma_deseado: return ""
    sin_tildes = unicodedata.normalize("NFKD", tipo_norma_deseado).encode("ascii", "ignore").decode("ascii")
    return sin_tildes.strip().lower()

def _mapear_tipo_norma(tipo_norma_deseado: str) -> str:
    clave = _normalizar_tipo_norma(tipo_norma_deseado)
    if clave in MAPEO_TIPOS_NORMA: return MAPEO_TIPOS_NORMA[clave]
    for clave_conocida, value in MAPEO_TIPOS_NORMA.items():
        if clave_conocida in clave or clave in clave_conocida: return value
    return MAPEO_TIPOS_NORMA["ley"]

# LA CLAVE DEL ÉXITO: Strings crudos en vez de diccionarios
def _payload_por_numero_string(tipo_norma_value: str, numero: str) -> str:
    numero_limpio = re.sub(r"\D", "", numero or "")
    return f"tipoNorma={tipo_norma_value}&numero={numero_limpio}&anioSancion=&texto=&dependencia=&diaPubDesde=&mesPubDesde=0&anioPubDesde=&diaPubHasta=&mesPubHasta=0&anioPubHasta="

def _payload_por_texto_libre_string(texto_libre: str) -> str:
    texto_encoded = urllib.parse.quote_plus((texto_libre or "").strip())
    return f"tipoNorma=&numero=&anioSancion=&texto={texto_encoded}&dependencia=&diaPubDesde=&mesPubDesde=0&anioPubDesde=&diaPubHasta=&mesPubHasta=0&anioPubHasta="

def _leer_norma_infoleg(session: requests.Session, headers: dict, url: str) -> dict:
    """
    Entra a la ficha de una norma, busca el "Texto Actualizado" y extrae el texto limpio.
    """
    try:
        resp = session.get(url, headers=headers, timeout=15)
        resp.encoding = ENCODING
        soup = BeautifulSoup(resp.text, "html.parser")

        # ¡LA MAGIA PARA LEYES VIEJAS! Buscar el botón de Texto Actualizado
        link_actualizado = None
        for a in soup.find_all("a", href=True):
            texto_enlace = a.get_text(strip=True).lower()
            if "texto actualizado" in texto_enlace or "texact" in a["href"].lower():
                link_actualizado = a["href"]
                if not link_actualizado.startswith("http"):
                    link_actualizado = urllib.parse.urljoin(BASE_URL, link_actualizado)
                break
                
        # Si existe la versión moderna, la descargamos para leer esa
        if link_actualizado:
            resp_act = session.get(link_actualizado, headers=headers, timeout=15)
            resp_act.encoding = ENCODING
            soup_texto = BeautifulSoup(resp_act.text, "html.parser")
        else:
            soup_texto = soup

        # Extraer el título original de la primera página
        titulo_tag = soup.find(["h1", "h2", "b"])
        norma = titulo_tag.get_text(strip=True) if titulo_tag else None

        # Limpiamos basura del HTML
        for tag in soup_texto(["script", "style", "nav", "header", "footer"]): 
            tag.decompose()

        texto_crudo = soup_texto.get_text(separator=" ")
        texto_limpio = re.sub(r"\s+", " ", texto_crudo).strip()

        fecha_match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", texto_limpio)
        fecha = fecha_match.group(0) if fecha_match else "N/D"

        # Límite bestial de 150.000 caracteres (aprox 40 páginas de texto puro)
        if len(texto_limpio) > 150000: 
            texto_limpio = texto_limpio[:150000] + "..."

        return {
            "norma": norma,
            "fecha": fecha,
            "tema": "N/D",
            "link": url, # Mantenemos el link oficial de la ficha para el usuario
            "contenido_texto": texto_limpio
        }
    except Exception as e:
        return {"contenido_texto": f"(Error al leer la norma: {e})"}
