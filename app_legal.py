import os
import streamlit as st
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN PREMIUM
st.set_page_config(page_title="Chubut.IA - Legal", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

# --- ESTILOS DE CHAT ESTILO GEMINI ---
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Estilo de la burbuja del Asistente (Gris oscuro) */
        [data-testid="chatAvatarIcon-assistant"] {
            background-color: #3B82F6;
        }
        .stChatMessage:nth-child(even) {
            background-color: #1E293B;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        /* Estilo de la burbuja del Usuario (Transparente) */
        .stChatMessage:nth-child(odd) {
            background-color: transparent;
            padding: 1rem;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN DIRECTA A LA CAJA FUERTE
try:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("🚨 La llave de OpenAI no se encontró en la configuración de Streamlit Secrets.")
    st.stop()

CLIENTES_AUTORIZADOS = {
    "roman_admin": "ceo2026",
    "estudio_perez": "abogado123"
}

# 3. CONTROL DE SEGURIDAD Y MEMORIA
if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = False

if "sesiones_chat" not in st.session_state:
    st.session_state.sesiones_chat = {"Consulta 1": []}
if "sesion_actual" not in st.session_state:
    st.session_state.sesion_actual = "Consulta 1"

# ==========================================
# PANTALLA DE LOGIN
# ==========================================
if not st.session_state.usuario_autenticado:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.write("")
        st.write("")
        st.image("https://cdn-icons-png.flaticon.com/512/6062/6062646.png", width=100)
        st.title("Chubut.IA")
        st.markdown("**Motor de Jurisprudencia Provincial**")
        st.divider()
        
        usuario_input = st.text_input("Usuario")
        password_input = st.text_input("Contraseña", type="password") 
        
        if st.button("Ingresar", type="primary", use_container_width=True):
            if usuario_input in CLIENTES_AUTORIZADOS and CLIENTES_AUTORIZADOS[usuario_input] == password_input:
                st.session_state.usuario_autenticado = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas o suscripción vencida.")

# ==========================================
# APLICACIÓN PRINCIPAL
# ==========================================
else:
    # --- LA BARRA LATERAL (EL HISTORIAL) ---
    with st.sidebar:
        st.title("Chubut.IA")
        st.caption("Jurisprudencia: Módulo Activo")
        st.divider()
        
        if st.button("➕ Nueva Consulta", use_container_width=True, type="primary"):
            nuevo_id = len(st.session_state.sesiones_chat) + 1
            nuevo_nombre = f"Consulta {nuevo_id}"
            st.session_state.sesiones_chat[nuevo_nombre] = []
            st.session_state.sesion_actual = nuevo_nombre
            st.rerun()
            
        st.markdown("### Historial de Chats")
        opciones_chat = list(st.session_state.sesiones_chat.keys())
        chat_seleccionado = st.radio(" ", opciones_chat, index=opciones_chat.index(st.session_state.sesion_actual), label_visibility="collapsed")
        
        if chat_seleccionado != st.session_state.sesion_actual:
            st.session_state.sesion_actual = chat_seleccionado
            st.rerun()
            
        st.divider()
        if st.button("Cerrar Sesión"):
            st.session_state.usuario_autenticado = False
            st.rerun()

    @st.cache_resource
    def conectar_boveda():
        directorio_db = "MI_BASE_VECTORIAL"
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        if not os.path.exists(directorio_db) or not os.listdir(directorio_db):
            st.error("🚨 No se encontró la base de datos vectorial.")
            st.stop()
        else:
            vectordb = Chroma(persist_directory=directorio_db, embedding_function=embeddings)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        return vectordb, llm

    try:
        vectordb, llm = conectar_boveda()
    except Exception as e:
        st.error(f"Error al conectar con la bóveda: {e}")
        st.stop()

    historial_activo = st.session_state.sesiones_chat[st.session_state.sesion_actual]

    # --- EL MENSAJE DE BIENVENIDA (Solo si el chat está vacío) ---
    if len(historial_activo) == 0:
        st.write("")
        st.write("")
        st.write("")
        st.markdown("<h1 style='text-align: center; color: #F8FAFC;'>¿En qué te puedo ayudar hoy?</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94A3B8;'>Soy Chubut.IA, tu asistente especializado en jurisprudencia provincial. Consultame sobre fallos, leyes o expedientes.</p>", unsafe_allow_html=True)

    # Mostrar historial
    for mensaje in historial_activo:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    # --- INPUT DEL USUARIO ---
    if pregunta := st.chat_input("Escribe tu consulta legal aquí..."):
        historial_activo.append({"role": "user", "content": pregunta})
        st.rerun() # Recarga rápido para mostrar el mensaje y borrar la bienvenida

    # --- PROCESAMIENTO DE LA IA ---
    # Revisamos si el ÚLTIMO mensaje es del usuario para responder
    if len(historial_activo) > 0 and historial_activo[-1]["role"] == "user":
        pregunta_actual = historial_activo[-1]["content"]
        
        with st.chat_message("assistant"):
            with st.spinner("Analizando expedientes en Chubut.IA..."):
                documentos_relevantes = vectordb.similarity_search(pregunta_actual, k=5)
                contexto_legal = "\n\n".join([doc.page_content for doc in documentos_relevantes])

                instruccion_sistema = f"""Sos Chubut.IA, un asistente legal brillante y experto en la jurisprudencia de Chubut.
                Basate ÚNICAMENTE en este contexto: {contexto_legal}
                
                Usá este formato exacto por caso:
                ### 📌 [Carátula del Caso]
                * 📅 **Fecha del Fallo:** (Buscá la fecha).
                * 📝 **Cita Textual:** "(Párrafo completo)".
                * 📄 **Resumen de los Hechos:** (Qué pasó).
                * ⚖️ **Resolución:** (Cómo falló el juez).
                * 🔗 **Enlace Oficial:** [Ver Fallo en Eureka](LINK)
                """
                
                mensajes_llm = [SystemMessage(content=instruccion_sistema)]
                # Solo le pasamos el contexto de esta sesión para no confundirla
                for msg in historial_activo:
                    role = "user" if msg["role"] == "user" else "assistant"
                    mensajes_llm.append(HumanMessage(content=msg["content"]) if role == "user" else AIMessage(content=msg["content"]))
                
                try:
                    def extraer_texto(stream):
                        for pedacito in stream:
                            yield pedacito.content
                    
                    respuesta_generada = st.write_stream(extraer_texto(llm.stream(mensajes_llm)))
                    historial_activo.append({"role": "assistant", "content": respuesta_generada})
                    
                    st.download_button(
                        label="📄 Descargar Dictamen",
                        data=respuesta_generada,
                        file_name=f"Dictamen_{st.session_state.sesion_actual}.txt",
                        mime="text/plain",
                        type="secondary",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Ocurrió un error: {e}")
