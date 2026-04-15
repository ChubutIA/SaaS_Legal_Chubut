# 0. PARCHE PARA CHROMADB EN LINUX (RAILWAY)
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
import streamlit as st
from supabase import create_client, Client
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Chubut.IA - Legal", page_icon="logo.png", layout="wide")

# --- CSS PROFESIONAL MEJORADO ---
st.markdown("""
    <style>
        footer {visibility: hidden;}
        [data-testid="stSidebar"] .stButton>button { 
            width: 100%; 
            border-radius: 8px; 
            text-align: left; 
            padding-left: 10px; 
            background-color: transparent; 
            border: 1px solid rgba(128, 128, 128, 0.3); 
            color: inherit;
            transition: all 0.2s ease-in-out;
        }
        [data-testid="stSidebar"] .stButton>button:hover {
            border-color: rgba(128, 128, 128, 0.8);
            background-color: rgba(128, 128, 128, 0.1);
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

# 2. CONEXIÓN A SERVICIOS (MODIFICADO Y BLINDADO)
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if OPENAI_KEY: OPENAI_KEY = str(OPENAI_KEY).strip().replace('"', '').replace("'", "")
if SUPABASE_URL: SUPABASE_URL = str(SUPABASE_URL).strip().replace('"', '').replace("'", "").rstrip('/')
if SUPABASE_KEY: SUPABASE_KEY = str(SUPABASE_KEY).strip().replace('"', '').replace("'", "")

if not OPENAI_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    st.error("🚨 Error de configuración: No se encontraron las llaves de acceso.")
    st.info("Asegurate de que OPENAI_API_KEY, SUPABASE_URL y SUPABASE_KEY estén en las Variables de Railway.")
    st.stop()
else:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. ESTADO DE SESIÓN BÁSICO
if "user_data" not in st.session_state: st.session_state.user_data = None
if "reset_step" not in st.session_state: st.session_state.reset_step = False
if "reset_email" not in st.session_state: st.session_state.reset_email = ""

# ==========================================
# PANTALLA DE ACCESO
# ==========================================
def pantalla_acceso():
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.markdown("<h3 style='text-align: center;'>Acceso al Sistema</h3>", unsafe_allow_html=True)
        tab_in, tab_reg = st.tabs(["🔑 Entrar", "📝 Registrarse"])
        
        with tab_in:
            if not st.session_state.reset_step:
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Contraseña", type="password", key="login_pass")
                
                if st.button("¿Olvidaste tu contraseña?", type="secondary"):
                    if email:
                        try:
                            supabase.auth.reset_password_email(email)
                            st.session_state.reset_step = True
                            st.session_state.reset_email = email
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error técnico: {e}")
                    else:
                        st.warning("Escribí tu email arriba para que podamos enviarte el código de recuperación.")
                
                st.write("") 
                if st.button("Iniciar Sesión", type="primary", use_container_width=True):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user_data = res.user
                        st.rerun()
                    except Exception as e:
                        st.error("Credenciales incorrectas o email no confirmado.")
            else:
                st.info(f"Revisá tu correo ({st.session_state.reset_email}). Te enviamos un código de seguridad.")
                codigo_otp = st.text_input("Código de recuperación", placeholder="Pegá el código de tu correo acá")
                nueva_pass = st.text_input("Nueva Contraseña", type="password")
                
                if st.button("Confirmar Cambio de Contraseña", type="primary", use_container_width=True):
                    if len(nueva_pass) >= 6:
                        try:
                            supabase.auth.verify_otp({"email": st.session_state.reset_email, "token": codigo_otp, "type": "recovery"})
                            supabase.auth.update_user({"password": nueva_pass})
                            st.success("¡Contraseña actualizada con éxito! Ya podés iniciar sesión.")
                            st.session_state.reset_step = False
                        except Exception as e:
                            st.error("El código es incorrecto o ya expiró. Revisá bien el correo.")
                    else:
                        st.error("La contraseña debe tener al menos 6 caracteres.")
                        
                if st.button("Cancelar / Volver"):
                    st.session_state.reset_step = False
                    st.rerun()

        with tab_reg:
            new_user = st.text_input("Nombre / Estudio", placeholder="Ej: Roman_Juridico")
            new_email = st.text_input("Tu Gmail")
            new_pass = st.text_input("Contraseña", type="password")
            confirm_pass = st.text_input("Confirmar Contraseña", type="password")
            if st.button("Crear Cuenta", use_container_width=True):
                if new_pass != confirm_pass: st.error("Las contraseñas no coinciden.")
                else:
                    try:
                        supabase.auth.sign_up({"email": new_email, "password": new_pass, "options": {"data": {"display_name": new_user}}})
                        st.success("¡Cuenta creada! Revisa tu email (Spam incluido).")
                    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# PANTALLA DE CHAT
# ==========================================
def pantalla_chat():
    user = st.session_state.user_data
    nombre = user.user_metadata.get("display_name", user.email.split("@")[0])
    
    db_res = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    
    if len(db_res.data) == 0:
        historial_db = {"Nueva Consulta": []}
        supabase.table("usuarios").insert({
            "usuario": nombre, "email": user.email, "consultas": 3, "plan": "gratis", "historial": historial_db
        }).execute()
        creditos = 3
        es_pro = False
    else:
        creditos = db_res.data[0]["consultas"]
        es_pro = db_res.data[0].get("plan") == "pro"
        historial_db = db_res.data[0].get("historial") or {"Nueva Consulta": []}

    if "chat_iniciado" not in st.session_state:
        st.session_state.sesiones_chat = historial_db
        st.session_state.sesion_actual = list(historial_db.keys())[-1]
        st.session_state.chat_iniciado = True

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown(f"👤 **{nombre}**")
        
        if es_pro:
            st.warning("💎 **PLAN PRO ACTIVADO**")
        else:
            st.success(f"Consultas restantes: **{creditos}**")
            if creditos <= 0:
                st.error("🚫 Consultas agotadas")
                link_mp = "https://mpago.la/1f481Uj" 
                st.link_button("Suscribirme ahora", link_mp, type="primary", use_container_width=True)

        st.divider()
        if st.button("➕ Nueva Consulta", type="primary", use_container_width=True):
            nueva_id = f"Consulta {len(st.session_state.sesiones_chat) + 1}"
            st.session_state.sesiones_chat[nueva_id] = []
            st.session_state.sesion_actual = nueva_id
            supabase.table("usuarios").update({"historial": st.session_state.sesiones_chat}).eq("email", user.email).execute()
            st.rerun()

        st.write("") 
        
        lista_chats = list(st.session_state.sesiones_chat.keys())
        
        for nombre_chat in reversed(lista_chats):
            col_btn, col_del = st.columns([0.8, 0.2]) 
            
            with col_btn:
                prefijo = "🟢" if nombre_chat == st.session_state.sesion_actual else "📄"
                if st.button(f"{prefijo} {nombre_chat}", key=f"btn_{nombre_chat}", use_container_width=True):
                    st.session_state.sesion_actual = nombre_chat
                    st.rerun()

            with col_del:
                if st.button("❌", key=f"del_{nombre_chat}", help="Borrar", use_container_width=True):
                    del st.session_state.sesiones_chat[nombre_chat]
                    
                    if st.session_state.sesion_actual == nombre_chat:
                        if len(st.session_state.sesiones_chat) > 0:
                            st.session_state.sesion_actual = list(st.session_state.sesiones_chat.keys())[-1]
                        else:
                            st.session_state.sesiones_chat = {"Nueva Consulta": []}
                            st.session_state.sesion_actual = "Nueva Consulta"
                    
                    supabase.table("usuarios").update({
                        "historial": st.session_state.sesiones_chat
                    }).eq("email", user.email).execute()
                    
                    st.rerun()
        
        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            if "chat_iniciado" in st.session_state: del st.session_state["chat_iniciado"]
            st.rerun()

    # ACÁ ESTÁ LA MAGIA QUE DESCARGA LA BASE DE DATOS
    @st.cache_resource(show_spinner="Descargando y conectando el cerebro jurídico (esto puede tardar unos minutos)...")
    def load_ia():
        if not os.path.exists("MI_BASE_VECTORIAL"):
            import gdown
            import zipfile
            
            # 👇👇👇 TU LINK DE GOOGLE DRIVE YA ESTÁ PUESTO ACÁ 👇👇👇
            link_drive = "https://drive.google.com/file/d/188KmlAHVcg4bbomeXG7Z6mP6dUm0Fqju/view?usp=sharing"
            
            if "drive.google.com" in link_drive:
                gdown.download(link_drive, "base.zip", quiet=False, fuzzy=True)
                with zipfile.ZipFile("base.zip", 'r') as zip_ref:
                    zip_ref.extractall()
                    
        emb = OpenAIEmbeddings(model="text-embedding-3-small")
        vdb = Chroma(persist_directory="MI_BASE_VECTORIAL", embedding_function=emb)
        return vdb, ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    vdb, llm = load_ia()
    historial_actual = st.session_state.sesiones_chat.get(st.session_state.sesion_actual, [])
    
    if len(historial_actual) == 0:
        st.markdown(f"""
            <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 60vh; text-align: center;">
                <h3 style="color: #9CA3AF; font-weight: 400; margin-bottom: 5px;">Hola, {nombre}</h3>
                <h1 style="font-size: 3rem; font-weight: 600; margin-top: 0;">¿En qué puedo ayudarte hoy?</h1>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"### {st.session_state.sesion_actual}") 
        for m in historial_actual:
            with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("¿Qué duda legal tenés sobre Chubut?"):
        if creditos > 0 or es_pro:
            historial_actual.append({"role": "user", "content": prompt})
            st.rerun() 
        else:
            st.error("No te quedan consultas. Suscribite al plan Pro para continuar.")
            
    if len(historial_actual) > 0 and historial_actual[-1]["role"] == "user":
        prompt = historial_actual[-1]["content"]
        
        with st.chat_message("assistant"):
            with st.spinner("Buscando fallos..."):
                docs = vdb.similarity_search(prompt, k=4)
                ctx = "\n\n".join([d.page_content for d in docs])
                
                instruccion_base = f"""Sos Chubut.IA, asistente jurídico de Chubut.
Contexto: {ctx}

REGLAS DE FORMATO:
1. VISUALIZACIÓN DE FALLOS: Si el usuario pide jurisprudencia o un fallo, usá EXACTAMENTE este formato visual con emojis y viñetas:

📌 **[Título del Fallo]**
* 📅 **Fecha del Fallo:** [Fecha]
* 📖 **Cita Textual:** "[Extracto clave]"
* 📝 **Resumen de los Hechos:** [Resumen]
* ⚖️ **Resolución:** [Decisión]
* 🔗 **Ver fallo oficial:** https://pdf.ai/

2. ANÁLISIS: Respondé fluido en párrafos si es una consulta general o un análisis. Si dentro del análisis citás un fallo, aplicá estrictamente la estructura de viñetas y emojis de la Regla 1.
"""
                msgs_ia = [SystemMessage(content=instruccion_base)]
                
                for m in historial_actual[:-1]:
                    role = HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"])
                    msgs_ia.append(role)
                
                msgs_ia.append(HumanMessage(content=prompt))
                
                res = llm.invoke(msgs_ia)
                st.markdown(res.content)
                historial_actual.append({"role": "assistant", "content": res.content})
                
                nuevo_conteo = creditos if es_pro else creditos - 1
                
                sesion_vieja = st.session_state.sesion_actual
                if sesion_vieja.startswith("Consulta ") and len(historial_actual) == 2:
                    try:
                        tit_p = f"Resume esto en 3 palabras: {prompt}"
                        nuevo_titulo = llm.invoke([HumanMessage(content=tit_p)]).content.replace('"', '').strip()
                        st.session_state.sesiones_chat[nuevo_titulo] = st.session_state.sesiones_chat.pop(sesion_vieja)
                        st.session_state.sesion_actual = nuevo_titulo
                    except: pass
                else:
                    st.session_state.sesiones_chat[st.session_state.sesion_actual] = historial_actual

                supabase.table("usuarios").update({
                    "consultas": nuevo_conteo,
                    "historial": st.session_state.sesiones_chat
                }).eq("email", user.email).execute()
                st.rerun()

# --- ARRANQUE ---
if st.session_state.user_data is None:
    pantalla_acceso()
else:
    pantalla_chat()
