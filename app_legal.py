import os
import streamlit as st
from supabase import create_client, Client
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Chubut.IA - Legal", page_icon="logo.png", layout="wide")

# --- CSS PROFESIONAL ---
st.markdown("""
    <style>
        footer {visibility: hidden;}
        .stButton>button { width: 100%; border-radius: 10px; text-align: left; padding-left: 15px; }
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
try:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception:
    st.error("🚨 Error de configuración en Secrets.")
    st.stop()

# 3. ESTADO DE SESIÓN BÁSICO
if "user_data" not in st.session_state: st.session_state.user_data = None

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
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Contraseña", type="password", key="login_pass")
            if st.button("Iniciar Sesión", type="primary", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user_data = res.user
                    st.rerun()
                except Exception as e:
                    if "Email not confirmed" in str(e):
                        st.warning("⚠️ Confirma tu email en la carpeta de Spam.")
                    else:
                        st.error("Credenciales incorrectas.")

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
                        st.success("¡Cuenta creada! Revisa tu email (mira en Spam).")
                    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# PANTALLA DE CHAT (CON PERSISTENCIA)
# ==========================================
def pantalla_chat():
    user = st.session_state.user_data
    nombre = user.user_metadata.get("display_name", user.email.split("@")[0])
    
    # Cargar datos desde Supabase
    db_res = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    
    if len(db_res.data) == 0:
        # Usuario nuevo
        historial_db = {"Consulta 1": []}
        supabase.table("usuarios").insert({
            "usuario": nombre, 
            "email": user.email, 
            "consultas": 3, 
            "password": "AUTH",
            "historial": historial_db
        }).execute()
        creditos = 3
    else:
        # Usuario existente
        creditos = db_res.data[0]["consultas"]
        historial_db = db_res.data[0].get("historial")
        # Si la columna historial está vacía (NULL), le creamos una estructura base
        if not historial_db:
            historial_db = {"Consulta 1": []}

    # Sincronizar Base de Datos con Streamlit (Solo 1 vez al entrar)
    if "chat_iniciado" not in st.session_state:
        st.session_state.sesiones_chat = historial_db
        # Seleccionar la última consulta como activa
        st.session_state.sesion_actual = list(historial_db.keys())[-1] if historial_db else "Consulta 1"
        st.session_state.chat_iniciado = True

    # --- BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown(f"👤 **{nombre}**")
        st.success(f"Consultas: **{creditos}**")
        
        st.divider()
        st.subheader("Tus Consultas")
        
        # Botón para Nueva Consulta
        if st.button("➕ Nueva Consulta", type="primary", use_container_width=True):
            # Generar nombre único para la consulta
            num_consulta = len(st.session_state.sesiones_chat) + 1
            nueva_id = f"Consulta {num_consulta}"
            
            # Actualizar memoria
            st.session_state.sesiones_chat[nueva_id] = []
            st.session_state.sesion_actual = nueva_id
            
            # GUARDAR EN SUPABASE INMEDIATAMENTE
            supabase.table("usuarios").update({"historial": st.session_state.sesiones_chat}).eq("email", user.email).execute()
            st.rerun()

        # Generar lista de botones del Historial
        st.write("") # Espacio
        for nombre_chat in list(st.session_state.sesiones_chat.keys()):
            # Marcador visual para el chat seleccionado
            prefijo = "🟢" if nombre_chat == st.session_state.sesion_actual else "📄"
            if st.button(f"{prefijo} {nombre_chat}", key=f"btn_{nombre_chat}", use_container_width=True):
                st.session_state.sesion_actual = nombre_chat
                st.rerun()
        
        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            if "chat_iniciado" in st.session_state:
                del st.session_state["chat_iniciado"]
            st.rerun()

    # --- CUERPO DEL CHAT ---
    st.title(f"{st.session_state.sesion_actual}")
    
    @st.cache_resource
    def load_ia():
        emb = OpenAIEmbeddings(model="text-embedding-3-small")
        vdb = Chroma(persist_directory="MI_BASE_VECTORIAL", embedding_function=emb)
        return vdb, ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    vdb, llm = load_ia()
    
    # Cargar mensajes de la sesión actual
    historial_actual = st.session_state.sesiones_chat.get(st.session_state.sesion_actual, [])
    
    for m in historial_actual:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    # Entrada de mensaje
    if prompt := st.chat_input("¿En qué puedo ayudarte con la jurisprudencia de Chubut?"):
        if creditos > 0:
            historial_actual.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Buscando en fallos..."):
                    docs = vdb.similarity_search(prompt, k=4)
                    ctx = "\n\n".join([d.page_content for d in docs])
                    
                    instruccion = f"""Sos Chubut.IA. Contexto legal: {ctx}
                    REGLAS:
                    1. Si es una consulta nueva, usa el formato: 📌 Carátula, 📅 Fecha, 📝 Cita, ⚖️ Resolución.
                    2. Si el usuario te repregunta sobre lo anterior, responde de forma natural usando el historial."""
                    
                    msgs_ia = [SystemMessage(content=instruccion)]
                    for m in historial_actual:
                        if m["role"] == "user": msgs_ia.append(HumanMessage(content=m["content"]))
                        else: msgs_ia.append(AIMessage(content=m["content"]))
                    
                    res = llm.invoke(msgs_ia)
                    st.markdown(res.content)
                    historial_actual.append({"role": "assistant", "content": res.content})
                    
                    # ACTUALIZAR SUPABASE CON EL NUEVO MENSAJE Y DESCONTAR CRÉDITO
                    st.session_state.sesiones_chat[st.session_state.sesion_actual] = historial_actual
                    supabase.table("usuarios").update({
                        "consultas": creditos - 1,
                        "historial": st.session_state.sesiones_chat
                    }).eq("email", user.email).execute()
                    
                    st.rerun()
        else:
            st.error("Se terminaron tus consultas gratis. ¡Suscribite para seguir!")

# --- ARRANQUE ---
if st.session_state.user_data is None: pantalla_acceso()
else: pantalla_chat()
