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
    "circular": "5",
    "comunicacion": "6",
    "decreto/ley": "7",
    "decreto ley": "7",
    "decreto-ley": "7", # <-- ¡Agregamos la versión con guion!
    "decision administrativa": "8",
    "acordada": "12",
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

# LA CLAVE DEL ÉXITO: Strings crudos en vez de diccionarios y a prueba de años
def _payload_por_numero_string(tipo_norma_value: str, numero: str) -> str:
    # Si la IA manda "50/2019", esto lo corta en la barra y se queda solo con el "50"
    numero_base = str(numero or "").split('/')[0]
    numero_limpio = re.sub(r"\D", "", numero_base)
    return f"tipoNorma={tipo_norma_value}&numero={numero_limpio}&anioSancion=&texto=&dependencia=&diaPubDesde=&mesPubDesde=0&anioPubDesde=&diaPubHasta=&mesPubHasta=0&anioPubHasta="

def _payload_por_texto_libre_string(texto_libre: str) -> str:
    texto_encoded = urllib.parse.quote_plus((texto_libre or "").strip())
    return f"tipoNorma=&numero=&anioSancion=&texto={texto_encoded}&dependencia=&diaPubDesde=&mesPubDesde=0&anioPubDesde=&diaPubHasta=&mesPubHasta=0&anioPubHasta="

def _leer_norma_infoleg(session: requests.Session, headers: dict, url: str) -> dict:
    try:
        resp = session.get(url, headers=headers, timeout=15)
        resp.encoding = ENCODING
        soup = BeautifulSoup(resp.text, "html.parser")

        link_actualizado = None
        for a in soup.find_all("a", href=True):
            texto_enlace = a.get_text(strip=True).lower()
            if "texto actualizado" in texto_enlace or "texact" in a["href"].lower():
                link_actualizado = a["href"]
                if not link_actualizado.startswith("http"):
                    link_actualizado = urllib.parse.urljoin(BASE_URL, link_actualizado)
                break
                
        if link_actualizado:
            resp_act = session.get(link_actualizado, headers=headers, timeout=15)
            resp_act.encoding = ENCODING
            soup_texto = BeautifulSoup(resp_act.text, "html.parser")
        else:
            soup_texto = soup

        titulo_tag = soup.find(["h1", "h2", "b"])
        norma = titulo_tag.get_text(strip=True) if titulo_tag else None

        for tag in soup_texto(["script", "style", "nav", "header", "footer"]): 
            tag.decompose()

        texto_crudo = soup_texto.get_text(separator=" ")
        texto_limpio = re.sub(r"\s+", " ", texto_crudo).strip()

        fecha_match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", texto_limpio)
        fecha = fecha_match.group(0) if fecha_match else "N/D"

        # Memoria gigante para leer cualquier ley
        if len(texto_limpio) > 150000: 
            texto_limpio = texto_limpio[:150000] + "..."

        return {
            "norma": norma,
            "fecha": fecha,
            "tema": "N/D",
            "link": url, 
            "contenido_texto": texto_limpio
        }
    except Exception as e:
        return {"contenido_texto": f"(Error al leer la norma: {e})"}

def buscar_normas_infoleg(tipo_norma: str = None, numero: str = None, texto_libre: str = None, max_resultados: int = 3) -> list:
    session = requests.Session()
    headers = _headers_navegador_completos(referer=FORM_URL)
    
    try:
        resp_form = session.get(FORM_URL, headers=headers, timeout=10)
        resp_form.encoding = ENCODING
        soup_form = BeautifulSoup(resp_form.text, "html.parser")
        
        form_tag = soup_form.find("form")
        action = form_tag.get("action") if form_tag else None
        post_url = urllib.parse.urljoin(FORM_URL, action) if action else SEARCH_ACTION_URL
        
        if numero:
            tipo_norma_value = _mapear_tipo_norma(tipo_norma)
            payload = _payload_por_numero_string(tipo_norma_value, numero)
        elif texto_libre:
            payload = _payload_por_texto_libre_string(texto_libre)
        else:
            return []
            
        headers_post = _headers_navegador_completos(referer=FORM_URL)
        resp_post = session.post(post_url, data=payload, headers=headers_post, timeout=15)
        resp_post.encoding = ENCODING
        soup_post = BeautifulSoup(resp_post.text, "html.parser")
        
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
                "contenido_texto": detalle.get("contenido_texto", "")
            })
        return resultados
    except Exception as e:
        print(f"Error al buscar en InfoLEG: {e}")
        return []
