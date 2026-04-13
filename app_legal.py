import os
import streamlit as st
from supabase import create_client, Client
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Chubut.IA - Legal", page_icon="logo.png", layout="wide")

# --- CSS PARA DISEÑO PROFESIONAL ---
st.markdown("""
    <style>
        footer {visibility: hidden;}
        .stButton>button { width: 100%; border-radius: 10px; }
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
            border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 20px 20px 20px 2px;
            padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
            background-color: #1E3A8A !important; border-radius: 20px 20px 2px 20px;
            padding: 1.2rem; margin-bottom: 1rem; margin-left: auto;
        }
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) * { color: white !important; }
    </style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN A SERVICIOS (API KEYS)
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("🚨 Error de configuración: Revisá los Secrets en Streamlit.")
    st.stop()

# 3. MANEJO DE ESTADO DE SESIÓN
if "user_data" not in st.session_state: st.session_state.user_data = None
if "sesiones_chat" not in st.session_state: st.session_state.sesiones_chat = {"Nueva Consulta": []}
if "sesion_actual" not in st.session_state: st.session_state.sesion_actual = "Nueva Consulta"

# ==========================================
# PANTALLA DE ACCESO (LOGIN / REGISTRO)
# ==========================================
def pantalla_acceso():
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center;'>Chubut.IA</h1>", unsafe_allow_html=True)
        
        st.markdown("<h4 style='text-align: center;'>Motor de Jurisprudencia Provincial</h4>", unsafe_allow_html=True)
        st.write("<br>", unsafe_allow_html=True)
        
        tab_login, tab_registro = st.tabs(["🔑 Iniciar Sesión", "📝 Crear Cuenta"])
        
        with tab_login:
            login_email = st.text_input("Email", key="log_email")
            login_pass = st.text_input("Contraseña", type="password", key="log_pass")
            
            if st.button("Entrar", type="primary"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                    if res.user:
                        st.session_state.user_data = res.user
                        st.success("¡Bienvenido!")
                        st.rerun()
                except Exception as e:
                    if "Email not confirmed" in str(e):
                        st.warning("⚠️ Debés confirmar tu email primero. Revisá tu casilla (y Spam).")
                    else:
                        st.error("Credenciales incorrectas o usuario no encontrado.")
            
            # Recuperación de contraseña
            if st.button("¿Olvidaste tu contraseña?", key="btn_forgot"):
                if login_email:
                    try:
                        supabase.auth.reset_password_for_email(login_email)
                        st.info(f"📩 Se envió un link para cambiar tu clave a: {login_email}")
                    except:
                        st.error("No pudimos enviar el correo. Intentá más tarde.")
                else:
                    st.warning("Escribí tu email arriba para que podamos ayudarte.")

        with tab_registro:
            reg_user = st.text_input("Nombre de Usuario / Estudio", placeholder="Ej: Roman07")
            reg_email = st.text_input("Correo Electrónico")
            reg_pass = st.text_input("Elegí una Contraseña", type="password")
            confirm_pass = st.text_input("Confirmá tu Contraseña", type="password")
            
            if st.button("Registrarme", type="primary"):
                if reg_pass != confirm_pass:
                    st.error("❌ Las contraseñas no coinciden.")
                elif len(reg_pass) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres.")
                elif not reg_user or not reg_email or "@" not in reg_email:
                    st.error("❌ Completá todos los campos correctamente.")
                else:
                    try:
                        # Registro en Supabase Auth con metadatos
                        res = supabase.auth.sign_up({
                            "email": reg_email,
                            "password": reg_pass,
                            "options": {"data": {"display_name": reg_user}}
                        })
                        st.success(f"✅ ¡Cuenta creada! Revisá tu mail **{reg_email}** para confirmarla.")
                        st.info("Nota: Si no confirmás el mail, no podrás iniciar sesión.")
                    except Exception as e:
                        st.error(f"Error al registrar: {e}")

# ==========================================
# PANTALLA DE CHAT (SISTEMA IA)
# ==========================================
def pantalla_chat():
    user = st.session_state.user_data
    # Extraemos el nombre de usuario de la metadata guardada en el registro
    nombre_mostrar = user.user_metadata.get("display_name", user.email.split("@")[0])
    
    # Sincronización de Créditos (Tabla 'usuarios')
    res_db = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    if len(res_db.data) == 0:
        # Si es la primera vez, le creamos sus 3 consultas gratis
        supabase.table("usuarios").insert({
            "usuario": nombre_mostrar,
            "email": user.email,
            "consultas": 3,
            "password": "AUTH_USER"
        }).execute()
        creditos = 3
    else:
        creditos = res_db.data[0]["consultas"]

    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown(f"👤 **{nombre_mostrar}**")
        st.caption(f"📧 {user.email}")
        
        if creditos > 0:
            st.success(f"🎁 Te quedan **{creditos}** consultas gratis")
        else:
            st.error("🚫 Consultas agotadas")
            st.markdown("### 💎 Pasate a Pro")
            st.write("Seguí consultando de forma ilimitada.")
            # AQUÍ PEGARÁS TU LINK DE MERCADO PAGO LUEGO
            st.link_button("Suscribirme (6,99 USD)", "https://mercadopago.com.ar", type="primary")
        
        st.divider()
        if st.button("➕ Nueva Consulta"):
            nueva_id = len(st.session_state.sesiones_chat) + 1
            nombre_chat = f"Consulta {nueva_id}"
            st.session_state.sesiones_chat[nombre_chat] = []
            st.session_state.sesion_actual = nombre_chat
            st.rerun()
            
        st.divider()
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            st.rerun()

    # --- LÓGICA DE IA (RAG) ---
    @st.cache_resource
    def conectar_ia():
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Asegurate de que la carpeta MI_BASE_VECTORIAL esté en tu GitHub
        vectordb = Chroma(persist_directory="MI_BASE_VECTORIAL", embedding_function=embeddings)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        return vectordb, llm

    try:
        vectordb, llm = conectar_ia()
    except:
        st.warning("⚠️ Cargando base de datos legal...")
        st.stop()

    historial = st.session_state.sesiones_chat[st.session_state.sesion_actual]
    
    # Mostrar mensajes previos
    for msg in historial:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # Entrada del Usuario
    if prompt := st.chat_input("¿Qué duda legal tenés sobre Chubut?"):
        if creditos <= 0:
            st.warning("Has agotado tus consultas gratuitas. Suscribite al plan Pro para continuar.")
            st.stop()
            
        historial.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analizando fallos en Chubut..."):
                # Buscar jurisprudencia
                docs = vectordb.similarity_search(prompt, k=4)
                contexto_fallos = "\n\n".join([d.page_content for d in docs])
                
                instruccion = f"Sos Chubut.IA. Contexto legal: {contexto_fallos}. Formato: 📌 Carátula, 📅 Fecha, 📝 Cita, ⚖️ Resolución."
                mensajes = [SystemMessage(content=instruccion)]
                for m in historial:
                    role = HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"])
                    mensajes.append(role)
                
                # Respuesta de la IA
                respuesta = llm.invoke(mensajes)
                st.markdown(respuesta.content)
                historial.append({"role": "assistant", "content": respuesta.content})
                
                # Descontar crédito
                supabase.table("usuarios").update({"consultas": creditos - 1}).eq("email", user.email).execute()
                st.rerun()

# --- EJECUCIÓN PRINCIPAL ---
if st.session_state.user_data is None:
    pantalla_acceso()
else:
    pantalla_chat()
