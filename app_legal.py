# 0. PARCHE PARA CHROMADB EN LINUX (RAILWAY)
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
import zipfile
import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client, Client
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO PROFESIONAL
st.set_page_config(page_title="Chubut.IA - Jurisprudencia Inteligente", page_icon="logo.png", layout="wide")

st.markdown("""
    <style>
        footer {visibility: hidden;}
        [data-testid="stSidebar"] .stButton>button { 
            width: 100%; border-radius: 8px; text-align: left; padding-left: 10px; 
            background-color: transparent; border: 1px solid rgba(128, 128, 128, 0.3); 
            color: inherit; transition: all 0.2s ease-in-out;
        }
        [data-testid="stSidebar"] .stButton>button:hover {
            border-color: rgba(128, 128, 128, 0.8); background-color: rgba(128, 128, 128, 0.1);
        }
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

# 2. CONEXIÓN A SERVICIOS (Configuradas en Railway)
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not OPENAI_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    st.error("🚨 Error crítico: Faltan variables de configuración en Railway.")
    st.stop()
else:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. ESTADO DE SESIÓN
if "user_data" not in st.session_state: st.session_state.user_data = None

# ==========================================
# AUTOMATIZACIÓN DE PAGO (Webhook / Redirect)
# ==========================================
def verificar_pago_entrante(user_email):
    # Si el usuario vuelve de Mercado Pago, la URL tendrá parámetros de éxito
    params = st.query_params
    if params.get("status") == "approved" and st.session_state.user_data:
        # Activamos el Plan Pro por 30 días automáticamente
        venc_pro = (datetime.now() + timedelta(days=30)).date()
        supabase.table("usuarios").update({
            "plan": "pro",
            "vencimiento_pro": str(venc_pro)
        }).eq("email", user_email).execute()
        st.success("¡Pago procesado con éxito! Tu Plan Pro está activo por 30 días.")
        # Limpiamos los parámetros para que no se ejecute dos veces
        st.query_params.clear()

# ==========================================
# PANTALLA DE ACCESO
# ==========================================
def pantalla_acceso():
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.markdown("<h3 style='text-align: center;'>Chubut.IA - Jurisprudencia</h3>", unsafe_allow_html=True)
        tab_in, tab_reg = st.tabs(["🔑 Entrar", "📝 Registrarse"])
        
        with tab_in:
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            if st.button("Iniciar Sesión", type="primary", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user_data = res.user
                    st.rerun()
                except: st.error("Email o contraseña incorrectos.")

        with tab_reg:
            new_user = st.text_input("Nombre y Apellido")
            new_email = st.text_input("Correo Electrónico")
            new_pass = st.text_input("Crea una contraseña", type="password")
            confirm_pass = st.text_input("Confirmar contraseña", type="password")
            
            if st.button("Crear Cuenta", use_container_width=True):
                # Validaciones básicas de seguridad
                if not new_user or not new_email or not new_pass or not confirm_pass:
                    st.warning("⚠️ Por favor, completá todos los campos.")
                elif new_pass != confirm_pass:
                    st.error("❌ Las contraseñas no coinciden. Intentá de nuevo.")
                elif len(new_pass) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres.")
                else:
                    # Verificar que el usuario y el correo sean únicos
                    with st.spinner("Verificando datos..."):
                        check_user = supabase.table("usuarios").select("usuario").eq("usuario", new_user).execute()
                        check_email = supabase.table("usuarios").select("email").eq("email", new_email).execute()
                        
                        if len(check_user.data) > 0:
                            st.error("⚠️ Ese Nombre ya está en uso. Por favor, elegí otro.")
                        elif len(check_email.data) > 0:
                            st.error("⚠️ Este correo electrónico ya está registrado. Iniciá sesión o usá otro.")
                        else:
                            # Si todo está perfecto, creamos la cuenta
                            try:
                                # Cálculo automático de la semana de prueba
                                venc_trial = (datetime.now() + timedelta(days=7)).date()
                                
                                supabase.auth.sign_up({
                                    "email": new_email, 
                                    "password": new_pass, 
                                    "options": {"data": {"display_name": new_user}}
                                })
                                
                                supabase.table("usuarios").insert({
                                    "usuario": new_user, 
                                    "email": new_email, 
                                    "plan": "gratis",
                                    "vencimiento_trial": str(venc_trial), 
                                    "historial": {"Nueva Consulta": []}
                                }).execute()
                                
                                st.success("✅ ¡Cuenta creada con éxito! Ya podés iniciar sesión en la pestaña 'Entrar'.")
                            except Exception as e: 
                                st.error(f"Error técnico al crear la cuenta: {e}")

# ==========================================
# PANTALLA DE CHAT (ACCESO CONTROLADO)
# ==========================================
def pantalla_chat():
    user = st.session_state.user_data
    verificar_pago_entrante(user.email) # Automatización de pago al volver
    
    db_res = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    if not db_res.data:
        st.error("No se encontró el perfil de usuario.")
        st.stop()

    datos = db_res.data[0]
    hoy = datetime.now().date()
    
    # LÓGICA DE TIEMPO AUTOMATIZADA
    es_pro = False
    if datos.get("plan") == "pro" and datos.get("vencimiento_pro"):
        venc_pro = datetime.strptime(datos["vencimiento_pro"], "%Y-%m-%d").date()
        if hoy <= venc_pro: es_pro = True

    esta_en_trial = False
    if not es_pro and datos.get("vencimiento_trial"):
        venc_trial = datetime.strptime(datos["vencimiento_trial"], "%Y-%m-%d").date()
        if hoy <= venc_trial: esta_en_trial = True

    # BLOQUEO POR VENCIMIENTO
    if not es_pro and not esta_en_trial:
        st.markdown(f"""
            <div style="text-align: center; padding: 40px; border: 2px solid #ef4444; border-radius: 15px; background-color: rgba(239, 68, 68, 0.1);">
                <h2 style="color: #ef4444;">Tu tiempo de acceso ha expirado</h2>
                <p>Tu semana de prueba gratuita terminó. Activá el Plan Pro para seguir consultando fallos y leyes de Chubut.</p>
            </div>
        """, unsafe_allow_html=True)
        st.link_button("🚀 Activar Acceso Profesional", "https://mpago.la/1f481Uj", use_container_width=True)
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            st.rerun()
        st.stop()

    # SIDEBAR Y GESTIÓN DE CHATS
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown(f"👤 **{datos['usuario']}**")
        if es_pro: st.warning(f"💎 PRO ACTIVO hasta {datos['vencimiento_pro']}")
        else: st.info(f"🎁 TRIAL ACTIVO hasta {datos['vencimiento_trial']}")
        
        st.divider()
        if st.button("➕ Nueva Consulta", type="primary", use_container_width=True):
            nueva_id = f"Consulta {len(datos['historial']) + 1}"
            datos['historial'][nueva_id] = []
            st.session_state.sesion_actual = nueva_id
            supabase.table("usuarios").update({"historial": datos['historial']}).eq("email", user.email).execute()
            st.rerun()

        # Historial de chats (Funcionalidad Completa)
        historial = datos.get("historial") or {"Nueva Consulta": []}
        if "sesion_actual" not in st.session_state: st.session_state.sesion_actual = list(historial.keys())[-1]
        
        for chat_id in reversed(list(historial.keys())):
            if st.button(f"📄 {chat_id}", key=f"btn_{chat_id}", use_container_width=True):
                st.session_state.sesion_actual = chat_id
                st.rerun()
        
        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            st.rerun()

    # MOTOR DE IA Y BASE DE DATOS
    @st.cache_resource(show_spinner="Conectando con la jurisprudencia de Chubut...")
    def load_ia():
        if not os.path.exists("MI_BASE_VECTORIAL"):
            import gdown
            file_id = "188KmlAHVcg4bbomeXG7Z6mP6dUm0Fqju"
            gdown.download(f"https://drive.google.com/uc?id={file_id}", "base.zip", quiet=False)
            with zipfile.ZipFile("base.zip", 'r') as zr: zr.extractall()
        emb = OpenAIEmbeddings(model="text-embedding-3-small")
        vdb = Chroma(persist_directory="MI_BASE_VECTORIAL", embedding_function=emb)
        return vdb, ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    vdb, llm = load_ia()
    chat_actual = historial.get(st.session_state.sesion_actual, [])

    # INTERFAZ DE CHAT
    if not chat_actual:
        st.markdown(f'<div style="text-align: center; margin-top: 20vh; color: #6B7280;"><h1>¿En qué puedo asistirlo hoy, Dr.?</h1></div>', unsafe_allow_html=True)
    else:
        for m in chat_actual:
            with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Consulte sobre fallos, leyes o jurisprudencia..."):
        chat_actual.append({"role": "user", "content": prompt})
        st.rerun()

    if chat_actual and chat_actual[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Buscando en la base de datos legal..."):
                docs = vdb.similarity_search(chat_actual[-1]["content"], k=4)
                contexto = "\n\n".join([d.page_content for d in docs])
                instruccion = f"Sos Chubut.IA. Usá este contexto de fallos de Chubut: {contexto}. Respondé con rigor legal, usando emojis y citando fuentes."
                
                mensajes = [SystemMessage(content=instruccion)]
                for m in chat_actual:
                    mensajes.append(HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"]))
                
                respuesta = llm.invoke(mensajes)
                st.markdown(respuesta.content)
                chat_actual.append({"role": "assistant", "content": respuesta.content})
                
                # Actualización automática del historial en Supabase
                historial[st.session_state.sesion_actual] = chat_actual
                supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
                st.rerun()

# --- EJECUCIÓN ---
if st.session_state.user_data is None:
    pantalla_acceso()
else:
    pantalla_chat()
