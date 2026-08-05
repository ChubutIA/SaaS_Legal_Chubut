import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF para leer PDFs desde la web

def buscar_ordenanzas_comodoro(palabra_clave):
    """
    Busca ordenanzas en el Digesto Municipal de Comodoro Rivadavia
    y extrae un resumen del texto completo del PDF vinculado.
    """
    url = "https://digestocomodoro.gob.ar/"
    
    session = requests.Session()
    headers_get = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response_get = session.get(url, headers=headers_get, timeout=10)
        soup_get = BeautifulSoup(response_get.text, 'html.parser')
        
        viewstate = soup_get.find('input', {'id': '__VIEWSTATE'})['value'] if soup_get.find('input', {'id': '__VIEWSTATE'}) else ""
        viewstategenerator = soup_get.find('input', {'id': '__VIEWSTATEGENERATOR'})['value'] if soup_get.find('input', {'id': '__VIEWSTATEGENERATOR'}) else ""
        eventvalidation = soup_get.find('input', {'id': '__EVENTVALIDATION'})['value'] if soup_get.find('input', {'id': '__EVENTVALIDATION'}) else ""
        
        payload = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "ctl00$body$ddlID_TIPO_NORMA": "1", 
            "ctl00$body$ddlAnio": "-1",        
            "ctl00$body$txtCampoBuscar": palabra_clave, 
            "ctl00$body$hidID_NORMA": "",
            "ctl00$body$btnBuscar": "Buscar",
            "ctl00$body$ddlTIPOS_NORMAS_A": "-1",
            "ctl00$body$ddlANIOS_A": "-1",
            "ctl00$body$ddlCATEGORIAS": "-1",
            "ctl00$body$ddlSECTORES": "-1",
            "ctl00$body$txtCampoBuscarA": ""
        }
        
        headers_post = headers_get.copy()
        headers_post["Content-Type"] = "application/x-www-form-urlencoded"
        
        response_post = session.post(url, data=payload, headers=headers_post, timeout=15)
        soup_post = BeautifulSoup(response_post.text, 'html.parser')
        
        resultados = []
        tabla_resultados = soup_post.find('table', {'class': 'table'})
        
        if tabla_resultados:
            filas = tabla_resultados.find_all('tr')[1:] # Saltamos el encabezado
            
            for fila in filas[:3]:
                columnas = fila.find_all('td')
                if len(columnas) >= 4:
                    norma = columnas[1].text.strip()
                    fecha = columnas[2].text.strip()
                    tema = columnas[3].text.strip()
                    
                    # Buscar el link de descarga o visualización de forma segura
                    link_etiqueta = columnas[0].find('a')
                    link = ""
                    if link_etiqueta and 'href' in link_etiqueta.attrs:
                        link = link_etiqueta['href']
                        # Si es un link relativo de ASP.NET, lo completamos
                        if not link.startswith("http"):
                            # Limpiamos puntos o barras extra si las hubiera
                            link = link.lstrip("./")
                            link = f"https://digestocomodoro.gob.ar/{link}"
                    
                    # --- LECTURA DEL PDF ---
                    texto_pdf = "(No se pudo extraer el texto del documento)"
                    if link and "verNorma" in link:
                        try:
                            res_pdf = session.get(link, timeout=10)
                            if res_pdf.status_code == 200:
                                doc_pdf = fitz.open(stream=res_pdf.content, filetype="pdf")
                                texto_acumulado = ""
                                for pagina in doc_pdf:
                                    texto_acumulado += pagina.get_text()
                                
                                if texto_acumulado.strip():
                                    texto_pdf = texto_acumulado.strip()[:2500] + "..."
                        except Exception as pdf_err:
                            texto_pdf = f"(Error al leer el PDF: {pdf_err})"
                    
                    resultados.append({
                        "norma": norma,
                        "fecha": fecha,
                        "tema": tema,
                        "link": link,
                        "contenido_pdf": texto_pdf
                    })
        
        return resultados

    except Exception as e:
        print(f"Error al buscar en el digesto: {e}")
        return []
if __name__ == "__main__":
    print("Buscando 'violencia' y leyendo PDFs...")
    datos = buscar_ordenanzas_comodoro("violencia")
    for item in datos:
        print(f"\n- Norma: {item['norma']} ({item['fecha']})")
        print(f"  Tema: {item['tema']}")
        print(f"  Extracto del PDF: {item['contenido_pdf'][:200]}...")
