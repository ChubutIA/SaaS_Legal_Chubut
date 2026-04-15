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

# 2. CONEXIÓN A SERVICIOS
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
# PANTALLA DE ACCESO
# ==========================================
def pantalla_acceso():
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.markdown("<h3 style='text-align: center;'>Acceso al Sistema</h3>", unsafe_allow_html=True)
        tab_in, tab_reg = st.tabs(["🔑 Entrar", "📝 Registrarse"])
        
        with tab_in:
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            if st.button("Iniciar Sesión", type="primary", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user_data = res.user
                    st.rerun()
                except: st.error("Email o contraseña incorrectos, o falta confirmar el correo.")

        with tab_reg:
            new_user = st.text_input("Nombre y Apellido")
            new_email = st.text_input("Correo Electrónico")
            new_pass = st.text_input("Crea una contraseña", type="password")
            confirm_pass = st.text_input("Confirmar contraseña", type="password")
            
            if st.button("Crear Cuenta", use_container_width=True):
                if not new_user or not new_email or not new_pass or not confirm_pass:
                    st.warning("⚠️ Por favor, completá todos los campos.")
                elif new_pass != confirm_pass:
                    st.error("❌ Las contraseñas no coinciden. Intentá de nuevo.")
                elif len(new_pass) < 6:
                    st.error("❌ La contraseña debe tener al menos 6 caracteres.")
                else:
                    with st.spinner("Verificando datos..."):
                        check_user = supabase.table("usuarios").select("usuario").eq("usuario", new_user).execute()
                        check_email = supabase.table("usuarios").select("email").eq("email", new_email).execute()
                        
                        if len(check_user.data) > 0:
                            st.error("⚠️ Ese Nombre ya está en uso. Por favor, elegí otro.")
                        elif len(check_email.data) > 0:
                            st.error("⚠️ Este correo electrónico ya está registrado. Iniciá sesión o usá otro.")
                        else:
                            try:
                                venc_trial = (datetime.now() + timedelta(days=7)).date()
                                supabase.auth.sign_up({
                                    "email": new_email, 
                                    "password": new_pass, 
                                    "options": {"data": {"display_name": new_user}}
                                })
                                
                                supabase.table("usuarios").insert({
                                    "usuario": new_user, "email": new_email, "plan": "gratis",
                                    "vencimiento_trial": str(venc_trial), "historial": {"Nueva Consulta": []}
                                }).execute()
                                
                                st.success("✅ ¡Cuenta creada con éxito! Por favor, revisá tu correo y confirmá tu email para poder iniciar sesión.")
                            except Exception as e: st.error(f"Error técnico: {e}")

# ==========================================
# PANTALLA DE CHAT
# ==========================================
def pantalla_chat():
    user = st.session_state.user_data
    verificar_pago_entrante(user.email)
    
    db_res = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    if not db_res.data:
        st.error("Error al cargar perfil.")
        st.stop()

    datos = db_res.data[0]
    hoy = datetime.now().date()
    
    # FORMATEO DE FECHAS (Día/Mes/Año) PARA MOSTRAR AL USUARIO
    fecha_trial_formateada = ""
    if datos.get("vencimiento_trial"):
        fecha_trial_formateada = datetime.strptime(datos["vencimiento_trial"], "%Y-%m-%d").strftime("%d/%m/%Y")

    fecha_pro_formateada = ""
    if datos.get("vencimiento_pro"):
        fecha_pro_formateada = datetime.strptime(datos["vencimiento_pro"], "%Y-%m-%d").strftime("%d/%m/%Y")

    # VERIFICACIÓN DE ACCESOS
    es_pro = False
    if datos.get("plan") == "pro" and datos.get("vencimiento_pro"):
        venc_pro = datetime.strptime(datos["vencimiento_pro"], "%Y-%m-%d").date()
        if hoy <= venc_pro: es_pro = True

    esta_en_trial = False
    if not es_pro and datos.get("vencimiento_trial"):
        venc_trial = datetime.strptime(datos["vencimiento_trial"], "%Y-%m-%d").date()
        if hoy <= venc_trial: esta_en_trial = True

    # PANTALLA DE BLOQUEO (FIN DE TRIAL)
    if not es_pro and not esta_en_trial:
        st.markdown(f"""
            <div style="text-align: center; padding: 40px; border: 2px solid #ef4444; border-radius: 15px; background-color: rgba(239, 68, 68, 0.1);">
                <h2 style="color: #ef4444;">Tu tiempo de acceso ha expirado</h2>
                <p>Tu semana de prueba gratuita terminó. Activá el Plan Pro para seguir consultando jurisprudencia de Chubut.</p>
            </div>
        """, unsafe_allow_html=True)
        st.link_button("🚀 Activar Plan Pro ($9.500 ARS)", "https://mpago.la/1f481Uj", use_container_width=True)
        if st.button("Cerrar Sesión"):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            st.rerun()
        st.stop()

    # BARRA LATERAL
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown(f"👤 **{datos['usuario']}**")
        
        # INDICADOR DE PLAN CON FECHA FORMATEADA
        if es_pro: 
            st.warning(f"💎 Plan PRO hasta el {fecha_pro_formateada}")
        else: 
            st.info(f"🎁 Prueba Gratis hasta el {fecha_trial_formateada}")
        
        st.divider()
        
        # UPSELL DE VENTA CONSTANTE (CAJA ESTILIZADA)
        if not es_pro:
            st.markdown("""
                <div style="border: 2px solid #1E3A8A; border-radius: 10px; padding: 15px; background-color: #f8fafc; text-align: center; margin-bottom: 10px;">
                    <h4 style="color: #1E3A8A; margin-top: 0; margin-bottom: 5px;">🚀 Plan Mensual Pro</h4>
                    <p style="font-size: 1.2rem; font-weight: bold; color: #0f172a; margin: 0;">$9.500 ARS <span style="font-size: 0.9rem; font-weight: normal;">/ mes</span></p>
                    <p style="font-size: 0.85rem; color: #475569; margin-top: 5px; margin-bottom: 0;">Consultas ilimitadas de jurisprudencia.</p>
                </div>
            """, unsafe_allow_html=True)
            st.link_button("💳 Pasarme a Pro", "https://mpago.la/1f481Uj", type="primary", use_container_width=True)
            st.divider()

        if st.button("➕ Nueva Consulta", type="primary", use_container_width=True):
            nueva_id = f"Consulta {len(datos['historial']) + 1}"
            datos['historial'][nueva_id] = []
            st.session_state.sesion_actual = nueva_id
            supabase.table("usuarios").update({"historial": datos['historial']}).eq("email", user.email).execute()
            st.rerun()

        # HISTORIAL DE CHATS
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

    # MOTOR DE IA (CEREBRO)
    @st.cache_resource(show_spinner="Conectando el cerebro jurídico de Chubut...")
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

    # INTERFAZ PRINCIPAL
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

    if prompt := st.chat_input("¿Qué duda legal tenés sobre Chubut?"):
        chat_actual.append({"role": "user", "content": prompt})
        
        historial[st.session_state.sesion_actual] = chat_actual
        supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
        st.rerun()

    if chat_actual and chat_actual[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Buscando fallos y jurisprudencia..."):
                docs = vdb.similarity_search(chat_actual[-1]["content"], k=4)
                contexto = "\n\n".join([d.page_content for d in docs])
                
                # INSTRUCCIONES MEJORADAS (Múltiples fallos, no alucinar links)
                instruccion = f"""Sos Chubut.IA, asistente jurídico de la Provincia de Chubut.
Basate ÚNICAMENTE en el siguiente contexto legal extraído de la base de datos para responder:
{contexto}

REGLAS DE FORMATO Y CONTENIDO:
1. MOSTRAR TODOS LOS FALLOS: El contexto contiene información de varios fallos. Debes analizar todo el texto y mostrar TODOS los fallos que sean relevantes para la consulta. No te limites a uno solo.
2. DATOS REALES: No inventes fechas, enlaces ni resoluciones. Si un dato no está en el contexto, escribe "No especificado en el documento".
3. ESTRUCTURA OBLIGATORIA: Para CADA fallo que cites, usa exactamente esta estructura:

📌 **[Nombre de la Carátula o Título del Fallo]**
* 📅 **Fecha del Fallo:** [Fecha real extraída del contexto]
* 📖 **Cita Textual:** "[El extracto más relevante del fallo]"
* 📝 **Resumen de los Hechos:** [Breve resumen de la situación]
* ⚖️ **Resolución:** [Decisión final del tribunal]
* 🔗 **Fuente:** [Si el contexto incluye un enlace real o número de expediente, ponlo aquí. Si no lo tiene, pon "Enlace no disponible en la base de datos"]

4. ANÁLISIS: Puedes hacer una breve introducción antes de listar los fallos, pero la jurisprudencia siempre debe ir con la estructura de la Regla 3."""
                
                mensajes = [SystemMessage(content=instruccion)]
                for m in chat_actual[:-1]:
                    mensajes.append(HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"]))
                
                mensajes.append(HumanMessage(content=chat_actual[-1]["content"]))
                
                respuesta = llm.invoke(mensajes)
                st.markdown(respuesta.content)
                chat_actual.append({"role": "assistant", "content": respuesta.content})
                
                historial[st.session_state.sesion_actual] = chat_actual
                
                sesion_vieja = st.session_state.sesion_actual
                if sesion_vieja.startswith("Consulta ") and len(chat_actual) == 2:
                    try:
                        tit_p = f"Resume esto en 3 palabras: {chat_actual[0]['content']}"
                        nuevo_titulo = llm.invoke([HumanMessage(content=tit_p)]).content.replace('"', '').strip()
                        historial[nuevo_titulo] = historial.pop(sesion_vieja)
                        st.session_state.sesion_actual = nuevo_titulo
                    except: pass

                supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
                st.rerun()

# --- EJECUCIÓN ---
if st.session_state.user_data is None:
    pantalla_acceso()
else:
    pantalla_chat()
