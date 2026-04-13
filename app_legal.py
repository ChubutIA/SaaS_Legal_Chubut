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
# PANTALLA DE CHAT (TÍTULOS A PRUEBA DE BALAS)
# ==========================================
def pantalla_chat():
    user = st.session_state.user_data
    nombre = user.user_metadata.get("display_name", user.email.split("@")[0])
    
    # Cargar datos desde Supabase
    db_res = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    
    if len(db_res.data) == 0:
        historial_db = {"Nueva Consulta": []}
        supabase.table("usuarios").insert({
            "usuario": nombre, 
            "email": user.email, 
            "consultas": 3, 
            "password": "AUTH",
            "historial": historial_db
        }).execute()
        creditos = 3
    else:
        creditos = db_res.data[0]["consultas"]
        historial_db = db_res.data[0].get("historial")
        if not historial_db: historial_db = {"Nueva Consulta": []}

    # Sincronizar Base de Datos con Streamlit
    if "chat_iniciado" not in st.session_state:
        st.session_state.sesiones_chat = historial_db
        st.session_state.sesion_actual = list(historial_db.keys())[-1] if historial_db else "Nueva Consulta"
        st.session_state.chat_iniciado = True

    # --- BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown(f"👤 **{nombre}**")
        st.success(f"Consultas: **{creditos}**")
        
        st.divider()
        st.subheader("Tus Consultas")
        
        # Botón Inteligente para Nueva Consulta
        if st.button("➕ Nueva Consulta", type="primary", use_container_width=True):
            num_consulta = 1
            nueva_id = f"Consulta {num_consulta}"
            while nueva_id in st.session_state.sesiones_chat:
                num_consulta += 1
                nueva_id = f"Consulta {num_consulta}"
            
            st.session_state.sesiones_chat[nueva_id] = []
            st.session_state.sesion_actual = nueva_id
            
            supabase.table("usuarios").update({"historial": st.session_state.sesiones_chat}).eq("email", user.email).execute()
            st.rerun()

        # Generar lista de botones del Historial
        st.write("")
        # Mostrar los chats al revés (los más nuevos arriba)
        for nombre_chat in reversed(list(st.session_state.sesiones_chat.keys())):
            prefijo = "🟢" if nombre_chat == st.session_state.sesion_actual else "📄"
            if st.button(f"{prefijo} {nombre_chat}", key=f"btn_{nombre_chat}", use_container_width=True):
                st.session_state.sesion_actual = nombre_chat
                st.rerun()
        
        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            if "chat_iniciado" in st.session_state: del st.session_state["chat_iniciado"]
            st.rerun()

    # --- CUERPO DEL CHAT ---
    st.title(f"{st.session_state.sesion_actual}")
    
    @st.cache_resource
    def load_ia():
        emb = OpenAIEmbeddings(model="text-embedding-3-small")
        vdb = Chroma(persist_directory="MI_BASE_VECTORIAL", embedding_function=emb)
        return vdb, ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    vdb, llm = load_ia()
    
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
                    1. Si es consulta nueva, usa formato: 📌 Carátula, 📅 Fecha, 📝 Cita, ⚖️ Resolución.
                    2. Si repregunta, responde conversando y explicando."""
                    
                    msgs_ia = [SystemMessage(content=instruccion)]
                    for m in historial_actual:
                        if m["role"] == "user": msgs_ia.append(HumanMessage(content=m["content"]))
                        else: msgs_ia.append(AIMessage(content=m["content"]))
                    
                    res = llm.invoke(msgs_ia)
                    st.markdown(res.content)
                    historial_actual.append({"role": "assistant", "content": res.content})
                    
                    # --- LÓGICA DE TÍTULOS 100% SEGURA ---
                    sesion_vieja = st.session_state.sesion_actual
                    if sesion_vieja.startswith("Consulta ") and len(historial_actual) == 2:
                        try:
                            # Intentamos IA pura
                            sys_tit = SystemMessage(content="Resume el texto en un título de 3 a 5 palabras máximo. SÓLO el título. Cero comillas.")
                            nuevo_titulo = llm.invoke([sys_tit, HumanMessage(content=prompt)]).content.replace('"', '').strip()
                        except:
                            # Fallback: agarramos las primeras palabras del usuario
                            nuevo_titulo = (prompt[:25] + '...') if len(prompt) > 25 else prompt
                        
                        # Si la IA devolvió algo en blanco o muy raro, usamos el fallback
                        if len(nuevo_titulo) < 3:
                            nuevo_titulo = (prompt[:25] + '...') if len(prompt) > 25 else prompt

                        # Evitar nombres duplicados lógicamente
                        base_titulo = nuevo_titulo
                        contador = 1
                        while nuevo_titulo in st.session_state.sesiones_chat:
                            nuevo_titulo = f"{base_titulo} {contador}"
                            contador += 1
                        
                        # Reemplazamos la llave
                        st.session_state.sesiones_chat[nuevo_titulo] = st.session_state.sesiones_chat.pop(sesion_vieja)
                        st.session_state.sesion_actual = nuevo_titulo
                    else:
                        st.session_state.sesiones_chat[st.session_state.sesion_actual] = historial_actual
                    # ------------------------------------
                    
                    # Actualizar DB
                    supabase.table("usuarios").update({
                        "consultas": creditos - 1,
                        "historial": st.session_state.sesiones_chat
                    }).eq("email", user.email).execute()
                    
                    st.rerun()
        else:
            st.error("Se terminaron tus consultas gratis. ¡Suscribite para seguir!")

# --- ARRANQUE ---
if st.session_state.user_data is None: pantalla_
