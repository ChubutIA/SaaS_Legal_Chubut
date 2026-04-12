import os
import streamlit as st
from supabase import create_client, Client
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Chubut.IA - Legal", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")

# --- CSS PROFESIONAL ---
st.markdown("""
    <style>
        footer {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 5rem;}
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
            border: 1px solid rgba(128, 128, 128, 0.2) !important; border-radius: 20px 20px 20px 2px !important;
            padding: 1.5rem !important; margin-bottom: 1.5rem !important; box-shadow: 0 4px 12px rgba(0,0,0,0.05); max-width: 85%;
        }
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
            background-color: #1E3A8A !important; border-radius: 20px 20px 2px 20px !important;
            padding: 1.2rem !important; margin-bottom: 1.5rem !important; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 80%; margin-left: auto;
        }
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) * { color: #FFFFFF !important; }
    </style>
""", unsafe_allow_html=True)

# 2. CONEXIONES A LOS SECRETOS (OPENAI + SUPABASE)
try:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("🚨 Falta alguna API Key en Streamlit Secrets.")
    st.stop()

# 3. CONTROL DE SESIÓN MULTI-CHAT
if "usuario_autenticado" not in st.session_state: st.session_state.usuario_autenticado = False
if "user_data" not in st.session_state: st.session_state.user_data = None
if "sesiones_chat" not in st.session_state: st.session_state.sesiones_chat = {"Nueva Consulta": []}
if "sesion_actual" not in st.session_state: st.session_state.sesion_actual = "Nueva Consulta"

# ==========================================
# PANTALLA DE LOGIN / REGISTRO
# ==========================================
if st.session_state.user_data is None:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("<br>", unsafe_allow_html=True)
        col_img1, col_img2, col_img3 = st.columns([1, 3, 1])
        with col_img2:
            if os.path.exists("logo.png"):
                st.image("logo.png", use_container_width=True)
            else:
                st.markdown("<h1 style='text-align: center;'>Chubut.IA</h1>", unsafe_allow_html=True)
                
        st.markdown("<div style='text-align: center; font-size: 1.1rem; margin-top: 10px;'>🔒 <b>Sistema de Jurisprudencia</b></div>", unsafe_allow_html=True)
        st.divider()
        
        tab_login, tab_registro = st.tabs(["Iniciar Sesión", "Crear Cuenta"])
        
        with tab_login:
            u_login = st.text_input("Usuario", key="u_log")
            p_login = st.text_input("Contraseña", type="password", key="p_log")
            if st.button("Ingresar", type="primary", use_container_width=True):
                res = supabase.table("usuarios").select("*").eq("usuario", u_login).eq("password", p_login).execute()
                if len(res.data) > 0:
                    st.session_state.user_data = res.data[0]
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
                    
        with tab_registro:
            u_reg = st.text_input("Elegí un Usuario", key="u_reg")
            p_reg = st.text_input("Elegí una Contraseña", type="password", key="p_reg")
            if st.button("Registrarme y empezar prueba", use_container_width=True):
                existe = supabase.table("usuarios").select("*").eq("usuario", u_reg).execute()
                if len(existe.data) > 0:
                    st.warning("Ese nombre de usuario ya está ocupado.")
                else:
                    nuevo = {"usuario": u_reg, "password": p_reg, "consultas": 3}
                    supabase.table("usuarios").insert(nuevo).execute()
                    st.success("¡Cuenta creada! Ya podés iniciar sesión en la pestaña de al lado.")

# ==========================================
# APLICACIÓN PRINCIPAL (EL CHAT)
# ==========================================
else:
    # 1. Leer Créditos Actualizados
    user = st.session_state.user_data
    db_user = supabase.table("usuarios").select("*").eq("id", user["id"]).execute().data[0]
    creditos = db_user["consultas"]

    # 2. Conectar la Bóveda de Fallos (Chroma)
    @st.cache_resource
    def conectar_boveda():
        directorio_db = "MI_BASE_VECTORIAL"
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        if not os.path.exists(directorio_db):
            st.error("🚨 Base de datos vectorial no encontrada.")
            st.stop()
        vectordb = Chroma(persist_directory=directorio_db, embedding_function=embeddings)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        return vectordb, llm

    try:
        vectordb, llm = conectar_boveda()
    except Exception as e:
        st.error(f"Error de conexión con la bóveda: {e}")
        st.stop()

    # --- BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.header("Chubut.IA")
        
        st.divider()
        st.markdown(f"👤 **Usuario:** {user['usuario']}")
        
        # EL PAYWALL
        if creditos > 0:
            st.success(f"🎁 Te quedan **{creditos}** consultas gratis")
        else:
            st.error("🚫 Sin consultas disponibles")
            st.markdown("### 💎 Pasate a Pro")
            st.write("Seguí usando Chubut.IA de forma ilimitada por solo **6,99 USD/mes**.")
            st.button("Pagar Suscripción (Stripe)", type="primary", use_container_width=True)
            
        st.divider()
        
        if st.button("➕ Nueva Consulta", use_container_width=True):
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
            st.session_state.user_data = None
            st.rerun()

    # --- LÓGICA DEL CHAT Y LA IA ---
    historial_activo = st.session_state.sesiones_chat[st.session_state.sesion_actual]

    if len(historial_activo) == 0:
        st.write("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 3rem;'>¿En qué puedo ayudarte hoy?</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #808080; font-size: 1.2rem;'>Consultá la jurisprudencia de Chubut con inteligencia artificial.</p>", unsafe_allow_html=True)
    else:
        for mensaje in historial_activo:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])

    # INPUT DEL USUARIO
    if pregunta := st.chat_input("Escribe tu consulta aquí..."):
        
        # 1. VERIFICAR CRÉDITOS ANTES DE DEJARLO PREGUNTAR
        if creditos <= 0:
            st.warning("Has agotado tus consultas gratuitas. Por favor, adquiere el plan Pro en la barra lateral para continuar.")
            st.stop()
            
        # 2. SISTEMA DE AUTOTÍTULO
        if len(historial_activo) == 0:
            nuevo_titulo = pregunta[:25].capitalize() + "..."
            st.session_state.sesiones_chat[nuevo_titulo] = st.session_state.sesiones_chat.pop(st.session_state.sesion_actual)
            st.session_state.sesion_actual = nuevo_titulo

        # 3. GUARDAR Y RECARGAR
        st.session_state.sesiones_chat[st.session_state.sesion_actual].append({"role": "user", "content": pregunta})
        st.rerun() 

    # RESPUESTA DE LA IA
    historial_actualizado = st.session_state.sesiones_chat[st.session_state.sesion_actual]
    if len(historial_actualizado) > 0 and historial_actualizado[-1]["role"] == "user":
        pregunta_actual = historial_actualizado[-1]["content"]
        
        with st.chat_message("assistant"):
            with st.spinner("Buscando fallos en Chubut.IA..."):
                
                # --- MAGIA DE LA IA ---
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
                    
                    # --- MAGIA DE COBRO (DESCONTAR 1 CRÉDITO) ---
                    nueva_cantidad = creditos - 1
                    supabase.table("usuarios").update({"consultas": nueva_cantidad}).eq("id", user["id"]).execute()
                    
                    st.divider()
                    st.download_button(label="📄 Descargar Dictamen", data=respuesta_generada, file_name=f"Dictamen_ChubutIA.txt", mime="text/plain", type="secondary", use_container_width=True)
                
                except Exception as e:
                    st.error(f"Error: {e}")
