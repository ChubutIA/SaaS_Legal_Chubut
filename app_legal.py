# 0. PARCHE PARA CHROMADB EN LINUX (RAILWAY)
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
import zipfile
import requests # <-- NUEVO MOTOR DE DESCARGAS
import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
from supabase import create_client, Client
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO PROFESIONAL
st.set_page_config(page_title="Chubut.IA - Jurisprudencia", page_icon="logo.png", layout="wide")

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

# 2. INICIALIZAR COOKIES Y SERVICIOS
cookie_manager = stx.CookieManager()

OPENAI_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not OPENAI_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    st.error("🚨 Error crítico: Faltan variables de configuración en Railway.")
    st.stop()
else:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. VARIABLES DE ESTADO
if "user_data" not in st.session_state: st.session_state.user_data = None
if "show_login" not in st.session_state: st.session_state.show_login = False
if "guest_history" not in st.session_state: st.session_state.guest_history = []

# LEER COOKIE DE CONSULTAS
galleta_consultas = cookie_manager.get(cookie="consultas_invitado")
consultas_gastadas = int(galleta_consultas) if galleta_consultas is not None else 0

# ==========================================
# AUTOMATIZACIÓN DE PAGO
# ==========================================
def verificar_pago_entrante(user_email):
    params = st.query_params
    if params.get("status") == "approved" and st.session_state.user_data:
        venc_pro = (datetime.now() + timedelta(days=30)).date()
        supabase.table("usuarios").update({
            "plan": "pro",
            "vencimiento_pro": str(venc_pro)
        }).eq("email", user_email).execute()
        st.success("¡Pago procesado con éxito! Tu Plan Pro está activo por 30 días.")
        st.query_params.clear()

# ==========================================
# PANTALLA DE ACCESO (LOGIN / REGISTRO)
# ==========================================
def pantalla_acceso():
    if st.button("⬅️ Volver al Chat de Prueba"):
        st.session_state.show_login = False
        st.rerun()

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.markdown("<h3 style='text-align: center;'>Acceso al Sistema</h3>", unsafe_allow_html=True)
        tab_in, tab_reg = st.tabs(["🔑 Entrar", "📝 Registrarse"])
        
        with tab_in:
            with st.form("form_login", clear_on_submit=False):
                email = st.text_input("Email")
                password = st.text_input("Contraseña", type="password")
                btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True)

            if btn_login:
                if email and password:
                    with st.spinner("Autenticando..."):
                        try:
                            res = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password})
                            st.session_state.user_data = res.user
                            st.session_state.show_login = False
                            st.rerun()
                        except:
                            st.error("❌ Credenciales incorrectas.")
                else:
                    st.warning("⚠️ Completá ambos campos.")

        with tab_reg:
            with st.form("form_registro", clear_on_submit=False):
                new_user = st.text_input("Nombre y Apellido")
                new_email = st.text_input("Correo Electrónico")
                new_pass = st.text_input("Crea una contraseña", type="password")
                confirm_pass = st.text_input("Confirmar contraseña", type="password")
                btn_reg = st.form_submit_button("Crear Cuenta", use_container_width=True)
                
            if btn_reg:
                if not new_user or not new_email or not new_pass or not confirm_pass:
                    st.warning("⚠️ Por favor, completá todos los campos.")
                elif new_pass != confirm_pass:
                    st.error("❌ Las contraseñas no coinciden.")
                elif len(new_pass) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres.")
                else:
                    with st.spinner("Creando cuenta..."):
                        check_user = supabase.table("usuarios").select("usuario").eq("usuario", new_user).execute()
                        check_email = supabase.table("usuarios").select("email").eq("email", new_email.strip()).execute()
                        
                        if len(check_user.data) > 0:
                            st.error("⚠️ Ese Nombre ya está en uso.")
                        elif len(check_email.data) > 0:
                            st.error("⚠️ Este correo electrónico ya está registrado.")
                        else:
                            try:
                                venc_trial = (datetime.now() + timedelta(days=7)).date()
                                supabase.auth.sign_up({"email": new_email.strip(), "password": new_pass, "options": {"data": {"display_name": new_user}}})
                                supabase.table("usuarios").insert({
                                    "usuario": new_user, "email": new_email.strip(), "plan": "gratis",
                                    "vencimiento_trial": str(venc_trial), "historial": {"Nueva Consulta": []}
                                }).execute()
                                st.success("✅ ¡Cuenta creada! Ya podés iniciar sesión en 'Entrar'.")
                            except Exception as e: 
                                st.error(f"Error técnico: {e}")

# ==========================================
# CEREBRO GLOBAL (DESCARGADOR NATIVO ANTI-BLOQUEOS)
# ==========================================
@st.cache_resource(show_spinner="Conectando el cerebro jurídico de Chubut (Puede demorar unos minutos)...")
def load_ia():
    if not os.path.exists("MI_BASE_VECTORIAL"):
        file_id = "1UdL0oJCkWw57t-LSLRmYUTzSrAs4ruMS" 
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # Script Nativo que engaña a Google Drive
        session = requests.Session()
        response = session.get(url, stream=True)
        token = None
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                token = value
                break
        if token:
            url = f"https://drive.google.com/uc?export=download&confirm={token}&id={file_id}"
            response = session.get(url, stream=True)
            
        with open("base.zip", "wb") as f:
            for chunk in response.iter_content(32768):
                if chunk: f.write(chunk)
                
        with zipfile.ZipFile("base.zip", 'r') as zr: 
            zr.extractall()
    
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    vdb = Chroma(persist_directory="MI_BASE_VECTORIAL", embedding_function=emb)
    return vdb, ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# LÍNEA QUE ACTIVA EL CEREBRO
vdb, llm = load_ia()

# ==========================================
# PANTALLA MODO INVITADO
# ==========================================
def pantalla_invitado():
    global consultas_gastadas
    consultas_restantes = 5 - consultas_gastadas

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown("👤 **Modo Invitado**")
        st.info(f"🎁 Consultas de prueba: {consultas_restantes} / 5")
        st.divider()
        if st.button("🔑 Iniciar Sesión / Registrarse", type="primary", use_container_width=True):
            st.session_state.show_login = True
            st.rerun()

    if not st.session_state.guest_history:
        st.markdown("""
            <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 50vh; text-align: center;">
                <h1 style="font-size: 3rem; font-weight: 600;">Probalo gratis, sin registrarte.</h1>
                <p style="font-size: 1.2rem; color: gray;">Hacé una consulta legal sobre Chubut para ver cómo funciona.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        for m in st.session_state.guest_history:
            with st.chat_message(m["role"]): st.markdown(m["content"])

    if consultas_gastadas >= 5:
        st.warning("⚠️ Alcanzaste el límite de 5 consultas gratuitas.")
        if st.button("🚀 Crear cuenta gratis para continuar", type="primary", use_container_width=True):
            st.session_state.show_login = True
            st.rerun()
    else:
        if prompt := st.chat_input("Ej: ¿Qué dice la jurisprudencia sobre alimentos?"):
            st.session_state.guest_history.append({"role": "user", "content": prompt})
            st.rerun()

    if st.session_state.guest_history and st.session_state.guest_history[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Buscando jurisprudencia..."):
                docs = vdb.similarity_search(st.session_state.guest_history[-1]["content"], k=6)
                contexto_final = "\n\n".join([f"📅 FECHA: {d.metadata.get('fecha_completa')}\n🔗 URL: {d.metadata.get('link_pdf')}\n📄 CONTENIDO:\n{d.page_content}" for d in docs])
                
                instruccion = f"Sos Chubut.IA jurídico. Basate en esto:\n{contexto_final}\n\nUsa estructura de viñetas, emojis y el link crudo al final."
                mensajes = [SystemMessage(content=instruccion)]
                for m in st.session_state.guest_history[:-1]:
                    mensajes.append(HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"]))
                mensajes.append(HumanMessage(content=st.session_state.guest_history[-1]["content"]))
                
                respuesta = llm.invoke(mensajes)
                st.markdown(respuesta.content)
                st.session_state.guest_history.append({"role": "assistant", "content": respuesta.content})
                
                nuevas_consultas = consultas_gastadas + 1
                cookie_manager.set("consultas_invitado", str(nuevas_consultas), expires_at=datetime.now() + timedelta(days=365))
                st.rerun()

# ==========================================
# PANTALLA DE CHAT (LOGUEADOS)
# ==========================================
def pantalla_chat():
    user = st.session_state.user_data
    verificar_pago_entrante(user.email)
    db_res = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    datos = db_res.data[0]
    hoy = datetime.now().date()
    
    es_pro = False
    if datos.get("plan") == "pro" and datos.get("vencimiento_pro"):
        venc_pro = datetime.strptime(datos["vencimiento_pro"], "%Y-%m-%d").date()
        if hoy <= venc_pro: es_pro = True

    esta_en_trial = False
    if not es_pro and datos.get("vencimiento_trial"):
        venc_trial = datetime.strptime(datos["vencimiento_trial"], "%Y-%m-%d").date()
        if hoy <= venc_trial: esta_en_trial = True

    if not es_pro and not esta_en_trial:
        st.error("Tu tiempo de acceso ha expirado.")
        st.link_button("🚀 Activar Plan Pro ($9.500 ARS)", "https://mpago.la/1f481Uj", use_container_width=True)
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            st.rerun()
        st.stop()

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown(f"👤 **{datos['usuario']}**")
        if es_pro: st.warning("💎 Plan PRO Activo")
        else: st.info("🎁 Prueba Gratis Activa")
        st.divider()
        if st.button("➕ Nueva Consulta", type="primary", use_container_width=True):
            nueva_id = f"Consulta {len(datos['historial']) + 1}"
            datos['historial'][nueva_id] = []
            st.session_state.sesion_actual = nueva_id
            supabase.table("usuarios").update({"historial": datos['historial']}).eq("email", user.email).execute()
            st.rerun()
        
        historial = datos.get("historial") or {"Nueva Consulta": []}
        if "sesion_actual" not in st.session_state: st.session_state.sesion_actual = list(historial.keys())[-1]
        for chat_id in reversed(list(historial.keys())):
            col_btn, col_del = st.columns([0.8, 0.2])
            with col_btn:
                if st.button(f"{'🟢' if chat_id == st.session_state.sesion_actual else '📄'} {chat_id}", key=f"btn_{chat_id}", use_container_width=True):
                    st.session_state.sesion_actual = chat_id
                    st.rerun()
            with col_del:
                if st.button("❌", key=f"del_{chat_id}"):
                    del historial[chat_id]
                    st.session_state.sesion_actual = list(historial.keys())[-1] if historial else "Nueva Consulta"
                    supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
                    st.rerun()
        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            st.rerun()

    chat_actual = historial.get(st.session_state.sesion_actual, [])
    for m in chat_actual:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
        chat_actual.append({"role": "user", "content": prompt})
        historial[st.session_state.sesion_actual] = chat_actual
        supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
        st.rerun()

    if chat_actual and chat_actual[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Analizando jurisprudencia..."):
                docs = vdb.similarity_search(chat_actual[-1]["content"], k=6)
                contexto_final = "\n\n".join([f"📅 FECHA: {d.metadata.get('fecha_completa')}\n🔗 URL: {d.metadata.get('link_pdf')}\n📄 CONTENIDO:\n{d.page_content}" for d in docs])
                
                instruccion = f"Sos Chubut.IA jurídico. Contexto:\n{contexto_final}\n\nUsa viñetas, emojis y links crudos."
                mensajes = [SystemMessage(content=instruccion)]
                for m in chat_actual[:-1]:
                    mensajes.append(HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"]))
                mensajes.append(HumanMessage(content=chat_actual[-1]["content"]))
                
                respuesta = llm.invoke(mensajes)
                st.markdown(respuesta.content)
                chat_actual.append({"role": "assistant", "content": respuesta.content})
                
                if st.session_state.sesion_actual.startswith("Consulta ") and len(chat_actual) == 2:
                    tit_p = f"Resume esto en 3 palabras: {chat_actual[0]['content']}"
                    nuevo_titulo = llm.invoke([HumanMessage(content=tit_p)]).content.replace('"', '').strip()
                    historial[nuevo_titulo] = historial.pop(st.session_state.sesion_actual)
                    st.session_state.sesion_actual = nuevo_titulo

                supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
                st.rerun()

# ==========================================
# GESTOR CENTRAL DE PANTALLAS (RUTEADOR)
# ==========================================
if st.session_state.user_data is not None:
    pantalla_chat()
elif st.session_state.show_login:
    pantalla_acceso()
else:
    pantalla_invitado()
