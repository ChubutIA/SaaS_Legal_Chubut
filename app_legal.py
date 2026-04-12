import os
import streamlit as st
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN PREMIUM
st.set_page_config(page_title="Chubut.IA - Legal", page_icon="⚖️", layout="wide")

# --- INYECCIÓN DE CSS PARA DISEÑO AZUL MARINO Y REMARCOS ---
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        
        /* Barra lateral Azul Marino */
        [data-testid="stSidebar"] {
            background-color: #1E3A8A;
        }
        /* Letras blancas en la barra lateral para que resalten */
        [data-testid="stSidebar"] * {
            color: #FFFFFF !important;
        }
        /* Remarco para los mensajes de la IA */
        .stChatMessage:nth-child(even) {
            border-left: 4px solid #1E3A8A;
            background-color: rgba(30, 58, 138, 0.05);
            padding-left: 1rem;
            border-radius: 5px;
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

# 3. CONTROL DE SEGURIDAD Y MEMORIA MULTI-CHAT
if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = False

# Nuevo sistema de memoria estilo ChatGPT
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
        
        # Botón actualizado
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
    with st.sidebar:
        st.title("⚙️ Panel de Control")
        st.caption("Base de datos: Jurisprudencia Provincial")
        st.divider()
        
        # --- PANEL DE HISTORIAL DE CHATS ---
        st.markdown("### 💬 Tus Conversaciones")
        
        if st.button("➕ Nueva Consulta", use_container_width=True):
            nuevo_id = len(st.session_state.sesiones_chat) + 1
            nuevo_nombre = f"Consulta {nuevo_id}"
            st.session_state.sesiones_chat[nuevo_nombre] = []
            st.session_state.sesion_actual = nuevo_nombre
            st.rerun()
            
        opciones_chat = list(st.session_state.sesiones_chat.keys())
        chat_seleccionado = st.radio("Historial:", opciones_chat, index=opciones_chat.index(st.session_state.sesion_actual), label_visibility="collapsed")
        
        if chat_seleccionado != st.session_state.sesion_actual:
            st.session_state.sesion_actual = chat_seleccionado
            st.rerun()
            
        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.usuario_autenticado = False
            # Opcional: Podés borrar el historial al salir si querés más privacidad
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

    st.title("⚖️ Asistente Legal Inteligente")
    st.markdown(f"**Chat Actual: {st.session_state.sesion_actual}**")
    st.divider()

    try:
        vectordb, llm = conectar_boveda()
    except Exception as e:
        st.error(f"Error al conectar con la bóveda: {e}")
        st.stop()

    # Cargamos el historial DEL CHAT SELECCIONADO
    historial_activo = st.session_state.sesiones_chat[st.session_state.sesion_actual]

    for mensaje in historial_activo:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    if pregunta := st.chat_input("Consultá la jurisprudencia acá..."):
        historial_activo.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)

        with st.chat_message("assistant"):
            with st.spinner("Analizando expedientes en Chubut.IA..."):
                documentos_relevantes = vectordb.similarity_search(pregunta, k=5)
                contexto_legal = "\n\n".join([doc.page_content for doc in documentos_relevantes])

                instruccion_sistema = f"""Sos Chubut.IA, un asistente legal brillante y experto en la jurisprudencia de la provincia de Chubut.
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
                for msg in historial_activo:
                    role = "user" if msg["role"] == "user" else "assistant"
                    content = msg["content"]
                    mensajes_llm.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
                
                try:
                    def extraer_texto(stream):
                        for pedacito in stream:
                            yield pedacito.content
                    
                    respuesta_generada = st.write_stream(extraer_texto(llm.stream(mensajes_llm)))
                    historial_activo.append({"role": "assistant", "content": respuesta_generada})
                    
                    st.divider()
                    st.download_button(
                        label="📄 Descargar Dictamen para Word (.txt)",
                        data=respuesta_generada,
                        file_name=f"Dictamen_{st.session_state.sesion_actual}.txt",
                        mime="text/plain",
                        type="primary",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Ocurrió un error: {e}")
