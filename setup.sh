#!/bin/bash

# Encontrar el archivo base oculto de Streamlit
INDEX_PATH=$(python -c "import streamlit, os; print(os.path.join(os.path.dirname(streamlit.__file__), 'static', 'index.html'))")

# 1. Cambiar el Título principal
sed -i 's/<title>Streamlit<\/title>/<title>Chubut.IA - Jurisprudencia Oficial<\/title>/g' $INDEX_PATH

# 2. Cambiar la descripción fea de "enable JavaScript"
sed -i 's/You need to enable JavaScript to run this app./Inteligencia Artificial de jurisprudencia y fallos de la Provincia de Chubut./g' $INDEX_PATH

# 3. Inyectar SEO (Meta Description y Keywords ocultas para Google)
sed -i 's/<head>/<head><meta name="description" content="El primer buscador de fallos y jurisprudencia de la Provincia de Chubut impulsado por IA. Diseñado para acelerar el trabajo de abogados y estudios jurídicos."><meta name="keywords" content="jurisprudencia chubut, fallos legales chubut, abogados comodoro rivadavia, justicia chubut, buscador legal chubut, inteligencia artificial derecho">/g' $INDEX_PATH

# 4. Iniciar la aplicación
streamlit run app_legal.py --server.port $PORT --server.address 0.0.0.0
