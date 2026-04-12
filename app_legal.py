import os
import streamlit as st
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN PREMIUM
st.set_page_config(page_title="SaaS Legal Chubut", page_icon="⚖️", layout="wide")
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        .stChatMessage {background-color: transparent;}
    </style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN DIRECTA A LA CAJA FUERTE
try:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("🚨 La llave de OpenAI no se encontró en la configuración de Streamlit Secrets.")
    st.stop()

# BASE DE DATOS DE CLIENTES
CLIENTES_AUTORIZADOS = {
    "roman_admin": "ceo2026",
    "estudio_perez": "abogado123",
    "juzgado_trelew": "ley456"
}

# 3. CONTROL DE SEGURIDAD
if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = False
if "historial_chat" not in st.session_state:
    st.session_state.historial_chat = []

# ==========================================
# PANTALLA DE LOGIN
# ==========================================
if not st.session_state.usuario_autenticado:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.write("")
        st.write("")
        st.image("https://cdn-icons-png.flaticon.com/512/6062/6062646.png", width=100)
        st.title("Acceso Exclusivo")
        st.markdown("**SaaS Jurisprudencia - Chubut**")
        st.divider()
        
        usuario_input = st.text_input("Usuario")
        password_input = st.text_input("Contraseña", type="password") 
        
        if st.button("Ingresar a la Bóveda", type="primary", use_container_width=True):
            if usuario_input in CLIENTES_AUTORIZADOS and CLIENTES_AUTORIZADOS[usuario_input] == password_input:
                st.session_state.usuario_autenticado = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas o suscripción vencida.")

# ==========================================
# APLICACIÓN PRINCIPAL
# ==========================================
else:
    with st.sidebar:
        st.title("⚙️ Panel de Control")
        st.success("Suscripción Activa")
        st.divider()
        st.caption("Base de datos actual:")
        st.caption("Jurisprudencia Provincial")
        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.usuario_autenticado = False
            st.session_state.historial_chat = []
            st.rerun()

    @st.cache_resource
    def conectar_boveda():
        # Buscamos la carpeta directamente en la nube
        directorio_db = "MI_BASE_VECTORIAL"
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        if not os.path.exists(directorio_db) or not os.listdir(directorio_db):
            st.error("🚨 No se encontró la base de datos vectorial en los archivos.")
            st.stop()
        else:
            vectordb = Chroma(persist_directory=directorio_db, embedding_function=embeddings)
            
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        return vectordb, llm

    st.title("⚖️ Asistente Legal Inteligente")
    st.markdown("**Motor de Jurisprudencia Provincial - Chubut**")
    st.divider()

    try:
        vectordb, llm = conectar_boveda()
    except Exception as e:
        st.error(f"Error al conectar con la bóveda: {e}")
        st.stop()

    for mensaje in st.session_state.historial_chat:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    if pregunta := st.chat_input("Consultá la jurisprudencia acá..."):
        st.session_state.historial_chat.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)

        with st.chat_message("assistant"):
            with st.spinner("Analizando expedientes completos en la bóveda..."):
                documentos_relevantes = vectordb.similarity_search(pregunta, k=5)
                contexto_legal = "\n\n".join([doc.page_content for doc in documentos_relevantes])

                instruccion_sistema = f"""Sos un asistente legal brillante y experto en la jurisprudencia de Chubut.
                Basate ÚNICAMENTE en el siguiente contexto extraído de fallos reales.
                
                Por cada caso relevante que encuentres, DEBÉS usar EXACTAMENTE este formato visual:

                ### 📌 [Carátula del Caso]
                * 📅 **Fecha del Fallo:** (Buscá la fecha en el texto).
                * 📝 **Cita Textual:** "(Extraé un PÁRRAFO COMPLETO o frase extensa. Respetá las comillas)".
                * 📄 **Resumen de los Hechos:** (Detallá qué pasó y qué se pedía).
                * ⚖️ **Resolución:** (Explicá cómo falló el juez o la cámara).
                * 🔗 **Enlace Oficial:** [Ver Fallo Completo en Eureka](LINK_AQUÍ)

                CONTEXTO:
                {contexto_legal}
                """
                
                mensajes_llm = [SystemMessage(content=instruccion_sistema)]
                for msg in st.session_state.historial_chat:
                    role = "user" if msg["role"] == "user" else "assistant"
                    content = msg["content"]
                    mensajes_llm.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
                
                try:
                    def extraer_texto(stream):
                        for pedacito in stream:
                            yield pedacito.content
                    
                    # Generamos y mostramos la respuesta en pantalla
                    respuesta_generada = st.write_stream(extraer_texto(llm.stream(mensajes_llm)))
                    st.session_state.historial_chat.append({"role": "assistant", "content": respuesta_generada})
                    
                    # --- BOTÓN DE DESCARGA ---
                    st.divider()
                    st.download_button(
                        label="📄 Descargar Dictamen para Word (.txt)",
                        data=respuesta_generada,
                        file_name="Jurisprudencia_Chubut.txt",
                        mime="text/plain",
                        type="primary",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Ocurrió un error: {e}")
