import requests
from bs4 import BeautifulSoup

def buscar_ordenanzas_comodoro(palabra_clave):
    """
    Busca ordenanzas en el Digesto Municipal de Comodoro Rivadavia
    """
    url = "https://digestocomodoro.gob.ar/"
    
    # Iniciamos una sesión para que recuerde las cookies y el contexto
    session = requests.Session()
    
    # 1. Hacemos un GET primero para obtener la página y sus tokens de seguridad (VIEWSTATE)
    headers_get = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response_get = session.get(url, headers=headers_get, timeout=10)
        soup_get = BeautifulSoup(response_get.text, 'html.parser')
        
        # Extraemos los tokens de seguridad obligatorios de ASP.NET
        viewstate = soup_get.find('input', {'id': '__VIEWSTATE'})['value'] if soup_get.find('input', {'id': '__VIEWSTATE'}) else ""
        viewstategenerator = soup_get.find('input', {'id': '__VIEWSTATEGENERATOR'})['value'] if soup_get.find('input', {'id': '__VIEWSTATEGENERATOR'}) else ""
        eventvalidation = soup_get.find('input', {'id': '__EVENTVALIDATION'})['value'] if soup_get.find('input', {'id': '__EVENTVALIDATION'}) else ""
        
        # 2. Preparamos el payload (Form Data) EXACTO que nos mostraste en la captura
        payload = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            
            # Estos son los campos de la captura
            "ctl00$body$ddlID_TIPO_NORMA": "1", # "1" asumo que es el ID de "Ordenanza" según la captura
            "ctl00$body$ddlAnio": "-1",         # -1 es "Todos los años"
            "ctl00$body$txtCampoBuscar": palabra_clave, # La palabra que buscamos (ej: "violencia")
            "ctl00$body$hidID_NORMA": "",
            "ctl00$body$btnBuscar": "Buscar",
            "ctl00$body$ddlTIPOS_NORMAS_A": "-1",
            "ctl00$body$ddlANIOS_A": "-1",
            "ctl00$body$ddlCATEGORIAS": "-1",
            "ctl00$body$ddlSECTORES": "-1",
            "ctl00$body$txtCampoBuscarA": ""
        }
        
        # 3. Hacemos el POST (enviamos el formulario simulando el click en "Buscar")
        headers_post = headers_get.copy()
        headers_post["Content-Type"] = "application/x-www-form-urlencoded"
        
        response_post = session.post(url, data=payload, headers=headers_post, timeout=15)
        soup_post = BeautifulSoup(response_post.text, 'html.parser')
        
        # 4. Analizamos la tabla de resultados (Acá hay que ajustar según el HTML de la web)
        resultados = []
        
        # IMPORTANTE: El selector de la tabla puede variar. 
        # Inspeccioná una fila de resultados en la web para ver si usan <tr>, una clase específica, etc.
        # Esto es un ejemplo genérico:
        tabla_resultados = soup_post.find('table', {'class': 'table'})
        
        if tabla_resultados:
            filas = tabla_resultados.find_all('tr')[1:] # Saltamos el encabezado
            
            for fila in filas:
                columnas = fila.find_all('td')
                if len(columnas) >= 4:
                    norma = columnas[1].text.strip()
                    fecha = columnas[2].text.strip()
                    tema = columnas[3].text.strip()
                    
                    # Buscar el link de descarga en la primera columna (la del ojito)
                    link_etiqueta = columnas[0].find('a')
                    link = link_etiqueta['href'] if link_etiqueta else ""
                    if link and not link.startswith("http"):
                         link = f"https://digestocomodoro.gob.ar/{link}"
                    
                    resultados.append({
                        "norma": norma,
                        "fecha": fecha,
                        "tema": tema,
                        "link": link
                    })
        
        return resultados

    except Exception as e:
        print(f"Error al buscar en el digesto: {e}")
        return []

# --- Ejemplo de uso ---
if __name__ == "__main__":
    print("Buscando 'violencia'...")
    datos = buscar_ordenanzas_comodoro("violencia")
    for item in datos:
        print(f"- {item['norma']} ({item['fecha']}): {item['tema']}")
