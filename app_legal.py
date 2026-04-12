import os
import streamlit as st
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN PREMIUM CON TU LOGO
st.set_page_config(
    page_title="Chubut.IA - Legal", 
    page_icon="logo.png", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS PROFESIONAL ---
st.markdown("""
    <style>
        footer {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 5rem;}

        /* Estilo para las burbujas */
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
            border: 1px solid rgba(128, 128, 128, 0.2) !important;
            border-radius: 20px 20px 20px 2px !important;
            padding: 1.5rem !important;
            margin-bottom: 1.5rem !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            max-width: 85%;
        }
        
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
            background-color: #1E3A8A !important;
            border-radius: 20px 20px 2px 20px !important;
            padding: 1.2rem !important;
            margin-bottom: 1.5rem !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            max-width: 80%;
            margin-left: auto;
        }
        
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) * {
            color: #FFFFFF !important;
        }
    </style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN A LOS SECRETOS
try:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("🚨 Falta la API Key en Streamlit Secrets.")
    st.stop()

CLIENTES_AUTORIZADOS = {
    "roman_admin": "ceo2026",
    "estudio_perez": "abogado123"
}

# 3. CONTROL DE SESIÓN
if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = False

if "sesiones_chat" not in st.session_state:
    st.session_state.sesiones_chat = {"Nueva Consulta": []}
if "sesion_actual" not in st.session_state:
    st.session_state.sesion_actual = "Nueva Consulta"

# ==========================================
# PANTALLA DE LOGIN BALANCEADA
# ==========================================
if not st.session_state.usuario_autenticado:
    # Volvemos a las columnas equilibradas
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.write("<br>", unsafe_allow_html=True)
        
        # Truco de sub-columnas para centrar y achicar el logo
        col_img1, col_img2, col_img3 = st.columns([1, 3, 1])
        with col_img2:
            if os.path.exists("logo.png"):
                st.image("logo.png", use_container_width=True)
            else:
                st.markdown("<h1 style='text-align: center;'>Chubut.IA</h1>", unsafe_allow_html=True)
                
        st.markdown("<div style='text-align: center; font-size: 1.1rem; margin-top: 10px;'>🔒 <b>Sistema de Jurisprudencia</b></div>", unsafe_allow_html=True)
        st.divider()
        
        usuario_input = st.text_input("Usuario")
        password_input = st.text_input("Contraseña", type="password") 
        
        st.write("") 
        if st.button("Ingresar", type="primary", use_container_width=True):
            if usuario_input in CLIENTES_AUTORIZADOS and CLIENTES_AUTORIZADOS[usuario_input] == password_input:
                st.session_state.usuario_autenticado = True
                st.rerun()
            else:
                st.error("Acceso denegado.")

# ==========================================
# APLICACIÓN PRINCIPAL
# ==========================================
else:
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.header("Chubut.IA")
            
        st.divider()
        
        if st.button("➕ Nueva Consulta", use_container_width=True, type="primary"):
            nuevo_id = len(st.session_state.sesiones_chat) + 1
            nuevo_nombre = f"Nueva Consulta {nuevo_id}"
            st.session_state.sesiones_chat[nuevo_nombre] = []
            st.session_state.sesion_actual = nuevo_nombre
            st.rerun()
            
        st.subheader("Historial")
        opciones_chat = list(st.session_state.sesiones_chat.keys())
        chat_seleccionado = st.radio(" ", reversed(opciones_chat), index=list(reversed(opciones_chat)).index(st.session_state.sesion_actual), label_visibility="collapsed")
        
        if chat_seleccionado != st.session_state.sesion_actual:
            st.session_state.sesion_actual = chat_seleccionado
            st.rerun()
            
        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.usuario_autenticado = False
            st.rerun()

    @st.cache_resource
    def conectar_boveda():
        directorio_db = "MI_BASE_VECTORIAL"
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        if not os.path.exists(directorio_db):
            st.error("🚨 Base de datos no encontrada.")
            st.stop()
        vectordb = Chroma(persist_directory=directorio_db, embedding_function=embeddings)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        return vectordb, llm

    try:
        vectordb, llm = conectar_boveda()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        st.stop()

    historial_activo = st.session_state.sesiones_chat[st.session_state.sesion_actual]

    if len(historial_activo) == 0:
        st.write("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 3rem;'>¿En qué puedo ayudarte hoy?</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #808080; font-size: 1.2rem;'>Consultá la jurisprudencia de Chubut con inteligencia artificial.</p>", unsafe_allow_html=True)
    else:
        for mensaje in historial_activo:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])

    if pregunta := st.chat_input("Escribe tu consulta aquí..."):
        if len(historial_activo) == 0:
            nuevo_titulo = pregunta[:25].capitalize() + "..."
            st.session_state.sesiones_chat[nuevo_titulo] = st.session_state.sesiones_chat.pop(st.session_state.sesion_actual)
            st.session_state.sesion_actual = nuevo_titulo

        st.session_state.sesiones_chat[st.session_state.sesion_actual].append({"role": "user", "content": pregunta})
        st.rerun() 

    historial_actualizado = st.session_state.sesiones_chat[st.session_state.sesion_actual]
    if len(historial_actualizado) > 0 and historial_actualizado[-1]["role"] == "user":
        pregunta_actual = historial_actualizado[-1]["content"]
        
        with st.chat_message("assistant"):
            with st.spinner("Buscando en Chubut.IA..."):
                documentos_relevantes = vectordb.similarity_search(pregunta_actual, k=5)
                contexto_legal = "\n\n".join([doc.page_content for doc in documentos_relevantes])
                instruccion_sistema = f"Sos Chubut.IA. Contexto: {contexto_legal}. Formato: 📌 Carátula, 📅 Fecha, 📝 Cita, ⚖️ Resolución, 🔗 Link."
                mensajes_llm = [SystemMessage(content=instruccion_sistema)]
                for msg in historial_actualizado:
                    role = "user" if msg["role"] == "user" else "assistant"
                    mensajes_llm.append(HumanMessage(content=msg["content"]) if role == "user" else AIMessage(content=msg["content"]))
                
                try:
                    def extraer_texto(stream):
                        for pedacito in stream:
                            yield pedacito.content
                    respuesta_generada = st.write_stream(extraer_texto(llm.stream(mensajes_llm)))
                    st.session_state.sesiones_chat[st.session_state.sesion_actual].append({"role": "assistant", "content": respuesta_generada})
                    st.download_button(label="📄 Descargar Dictamen", data=respuesta_generada, file_name=f"Dictamen_ChubutIA.txt", mime="text/plain", type="secondary", use_container_width=True)
                except Exception as e:
                    st.error(f"Error: {e}")
