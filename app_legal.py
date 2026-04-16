# 0. PARCHE PARA CHROMADB EN LINUX (RAILWAY)
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
import zipfile
import urllib.request
import time  
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

# 2. SISTEMA BLINDADO DE COOKIES
cookie_manager = stx.CookieManager()

# Leemos las cookies directamente
access_token = cookie_manager.get(cookie="supa_access")
refresh_token = cookie_manager.get(cookie="supa_refresh")
galleta_invitado = cookie_manager.get(cookie="chubut_invitado")

# 3. VARIABLES DE ENTORNO Y SERVICIOS
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not OPENAI_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    st.error("🚨 Error crítico: Faltan variables de configuración en Railway.")
    st.stop()
else:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- RECUPERACIÓN AUTOMÁTICA DE SESIÓN ---
if "user_data" not in st.session_state: 
    st.session_state.user_data = None

if access_token and refresh_token and st.session_state.user_data is None:
    try:
        res = supabase.auth.set_session(access_token, refresh_token)
        st.session_state.user_data = res.user
    except Exception:
        pass 

if "show_login" not in st.session_state: st.session_state.show_login = False
if "guest_history" not in st.session_state: st.session_state.guest_history = []
if "consultas_gastadas" not in st.session_state: st.session_state.consultas_gastadas = 0

if galleta_invitado:
    st.session_state.consultas_gastadas = max(st.session_state.consultas_gastadas, int(galleta_invitado))

# ==========================================
# INSTRUCCIÓN ESTRICTA PARA LA IA (CHALECO DE FUERZA)
# ==========================================
def generar_instruccion_ia(contexto):
    return f"""Sos Chubut.IA, un asistente jurídico estrictamente enfocado en la Provincia de Chubut.
TU ÚNICA MISIÓN ES MOSTRAR JURISPRUDENCIA.
REGLA DE ORO: Si el usuario te saluda, te hace charla, o te pide cosas fuera del ámbito legal (ej: películas, recetas, noticias), DEBES NEGARTE CORTÉSMENTE y recordarle que solo estás capacitado para buscar fallos legales de Chubut.

CONTEXTO DE LA BASE DE DATOS:
{contexto}

REGLAS ESTRICTAS DE FORMATO (No uses otro):
Si la consulta es legal, debes estructurar CADA fallo encontrado exactamente así:

📌 **[Nombre o Título del Fallo]**
* 📅 **Fecha del Fallo:** [Copia la 'FECHA' exacta]
* 📖 **Cita Textual:** "[Extracto más relevante]"
* 📝 **Resumen de los Hechos:** [Breve resumen]
* ⚖️ **Resolución:** [Decisión final]
* 🔗 **Ver fallo oficial:** [Pega la 'URL' tal cual, sin corchetes ni formato markdown. Solo el link crudo]"""

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
            if not st.session_state.get("login_exitoso"):
                with st.form("form_login", clear_on_submit=False):
                    email = st.text_input("Email")
                    password = st.text_input("Contraseña", type="password")
                    btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True)

                if btn_login:
                    if email and password:
                        with st.spinner("Autenticando y guardando sesión segura..."):
                            try:
                                res = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password})
                                
                                # GUARDAMOS EL PASE VIP
                                vencimiento_sesion = datetime.now() + timedelta(days=30)
                                cookie_manager.set("supa_access", res.session.access_token, expires_at=vencimiento_sesion, key="set_acc_log")
                                cookie_manager.set("supa_refresh", res.session.refresh_token, expires_at=vencimiento_sesion, key="set_ref_log")
                                
                                st.session_state.temp_user = res.user
                                st.session_state.login_exitoso = True
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error al iniciar sesión. Verificá tus credenciales o si confirmaste tu email.")
                    else:
                        st.warning("⚠️ Completá ambos campos.")

            if st.session_state.get("login_exitoso"):
                st.success("✅ ¡Cookies de seguridad guardadas con éxito!")
                if st.button("👉 Entrar a mi cuenta", type="primary", use_container_width=True):
                    st.session_state.user_data = st.session_state.temp_user
                    st.session_state.show_login = False
                    st.session_state.login_exitoso = False
                    st.rerun()

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
                                st.success("✅ ¡Cuenta creada con éxito! POR FAVOR: Revisá tu correo electrónico (y tu carpeta de Spam) para confirmar tu cuenta antes de iniciar sesión.")
                            except Exception as e: 
                                st.error(f"Error técnico: {e}")

# ==========================================
# CEREBRO GLOBAL (DESCARGA DIRECTA DE GITHUB RELEASES)
# ==========================================
@st.cache_resource(show_spinner="Conectando el cerebro jurídico de Chubut (Puede demorar unos minutos)...")
def load_ia():
    if not os.path.exists("MI_BASE_VECTORIAL"):
        
        # 👇👇👇 PEGÁ EL ENLACE QUE COPIASTE DE GITHUB RELEASES ACÁ 👇👇👇
        url_directa = "https://github.com/ChubutIA/SaaS_Legal_Chubut/releases/download/v1.0/MI_BASE_VECTORIAL.zip"
        
        urllib.request.urlretrieve(url_directa, "base.zip")
        with zipfile.ZipFile("base.zip", 'r') as zr: 
            zr.extractall()
    
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    vdb = Chroma(persist_directory="MI_BASE_VECTORIAL", embedding_function=emb)
    return vdb, ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

vdb, llm = load_ia()

# ==========================================
# PANTALLA MODO INVITADO (LÍMITE: 1 CONSULTA)
# ==========================================
def pantalla_invitado():
    consultas_restantes = 1 - st.session_state.consultas_gastadas

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown("👤 **Modo Invitado**")
        st.info(f"🎁 Consulta de prueba: {max(0, consultas_restantes)} / 1")
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

    if st.session_state.consultas_gastadas >= 1:
        st.warning("⚠️ Consumiste tu única consulta gratuita.")
        if st.button("🚀 Crear cuenta gratis de 7 días para continuar", type="primary", use_container_width=True):
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
                
                mensajes = [SystemMessage(content=generar_instruccion_ia(contexto_final))]
                
                for m in st.session_state.guest_history[:-1]:
                    mensajes.append(HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"]))
                mensajes.append(HumanMessage(content=st.session_state.guest_history[-1]["content"]))
                
                respuesta = llm.invoke(mensajes)
                st.markdown(respuesta.content)
                st.session_state.guest_history.append({"role": "assistant", "content": respuesta.content})
                
                st.session_state.consultas_gastadas += 1
                vencimiento = datetime.now() + timedelta(days=365)
                # LLAVE ÚNICA ACÁ TAMBIÉN
                cookie_manager.set("chubut_invitado", str(st.session_state.consultas_gastadas), expires_at=vencimiento, key="set_inv")
                
                st.markdown("---")
                if st.button("🚀 ¡Excelente! Quiero crear mi cuenta gratis para seguir consultando", type="primary", use_container_width=True):
                    st.session_state.show_login = True
                    st.rerun()
                    
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
    
    fecha_trial_formateada = ""
    if datos.get("vencimiento_trial"):
        fecha_trial_formateada = datetime.strptime(datos["vencimiento_trial"], "%Y-%m-%d").strftime("%d/%m/%Y")

    fecha_pro_formateada = ""
    if datos.get("vencimiento_pro"):
        fecha_pro_formateada = datetime.strptime(datos["vencimiento_pro"], "%Y-%m-%d").strftime("%d/%m/%Y")

    es_pro = False
    if datos.get("plan") == "pro" and datos.get("vencimiento_pro"):
        venc_pro = datetime.strptime(datos["vencimiento_pro"], "%Y-%m-%d").date()
        if hoy <= venc_pro: es_pro = True

    esta_en_trial = False
    if not es_pro and datos.get("vencimiento_trial"):
        venc_trial = datetime.strptime(datos["vencimiento_trial"], "%Y-%m-%d").date()
        if hoy <= venc_trial: esta_en_trial = True

    if not es_pro and not esta_en_trial:
        st.markdown(f"""
            <div style="text-align: center; padding: 40px; border: 2px solid #ef4444; border-radius: 15px; background-color: rgba(239, 68, 68, 0.1);">
                <h2 style="color: #ef4444;">Tu tiempo de acceso ha expirado</h2>
                <p>Tu semana de prueba gratuita terminó. Activá el Plan Pro para seguir consultando jurisprudencia de Chubut.</p>
            </div>
        """, unsafe_allow_html=True)
        # 👇 ACÁ ESTÁ EL PRIMER LINK DE MERCADO PAGO A REEMPLAZAR 👇
        st.link_button("🚀 Activar Plan Pro ($6.500 ARS)", "https://mpago.la/2nDaBRx", use_container_width=True)
        
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            cookie_manager.delete("supa_access", key="del_acc_exp")
            cookie_manager.delete("supa_refresh", key="del_ref_exp")
            time.sleep(1) 
            st.session_state.user_data = None
            st.rerun()
        st.stop()

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown(f"👤 **{datos['usuario']}**")
        
        if es_pro: 
            st.warning(f"💎 Plan PRO hasta el {fecha_pro_formateada}")
        else: 
            st.info(f"🎁 Prueba Gratis hasta el {fecha_trial_formateada}")
        
        st.divider()
        
        if not es_pro:
            st.markdown("""
                <div style="border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 15px; background-color: rgba(255, 255, 255, 0.05); text-align: center; margin-bottom: 10px;">
                    <h4 style="color: #60A5FA; margin-top: 0; margin-bottom: 5px;">🚀 Plan Mensual Pro</h4>
                    <p style="font-size: 1.2rem; font-weight: bold; color: white; margin: 0;">$6.500 ARS <span style="font-size: 0.9rem; font-weight: normal; color: #9CA3AF;">/ mes</span></p>
                    <p style="font-size: 0.85rem; color: #9CA3AF; margin-top: 5px; margin-bottom: 0;">Consultas ilimitadas de jurisprudencia.</p>
                </div>
            """, unsafe_allow_html=True)
            # 👇 ACÁ ESTÁ EL SEGUNDO LINK DE MERCADO PAGO A REEMPLAZAR 👇
            st.link_button("💳 Pasarme a Pro", "https://mpago.la/2nDaBRx", type="primary", use_container_width=True)
            st.divider()

        if st.button("➕ Nueva Consulta", type="primary", use_container_width=True):
            nueva_id = f"Consulta {len(datos['historial']) + 1}"
            datos['historial'][nueva_id] = []
            st.session_state.sesion_actual = nueva_id
            supabase.table("usuarios").update({"historial": datos['historial']}).eq("email", user.email).execute()
            st.rerun()
        
        st.write("") 
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
            cookie_manager.delete("supa_access", key="del_acc_out")
            cookie_manager.delete("supa_refresh", key="del_ref_out")
            time.sleep(1)
            st.session_state.user_data = None
            st.rerun()

    chat_actual = historial.get(st.session_state.sesion_actual, [])
    
    if not chat_actual:
        st.markdown(f"""
            <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 60vh; text-align: center;">
                <h3 style="color: #9CA3AF; font-weight: 400; margin-bottom: 5px;">Hola, {datos['usuario']}</h3>
                <h1 style="font-size: 3rem; font-weight: 600; margin-top: 0;">¿En qué puedo ayudarte hoy?</h1>
            </div>
        """, unsafe_allow_html=True)
    else:
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
                
                mensajes = [SystemMessage(content=generar_instruccion_ia(contexto_final))]
                for m in chat_actual[:-1]:
                    mensajes.append(HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"]))
                mensajes.append(HumanMessage(content=chat_actual[-1]["content"]))
                
                respuesta = llm.invoke(mensajes)
                st.markdown(respuesta.content)
                chat_actual.append({"role": "assistant", "content": respuesta.content})
                
                if st.session_state.sesion_actual.startswith("Consulta ") and len(chat_actual) == 2:
                    try:
                        tit_p = f"Resume esta consulta en 3 o 4 palabras: '{chat_actual[0]['content']}'"
                        nuevo_titulo = llm.invoke([HumanMessage(content=tit_p)]).content.replace('"', '').strip()
                        if nuevo_titulo in historial: nuevo_titulo += " (1)" 
                        historial[nuevo_titulo] = historial.pop(st.session_state.sesion_actual)
                        st.session_state.sesion_actual = nuevo_titulo
                    except: pass

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
