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
    st.error("🚨 Error de configuración en Secrets de Streamlit.")
    st.stop()

# 3. ESTADO DE SESIÓN
if "user_data" not in st.session_state: st.session_state.user_data = None
if "sesiones_chat" not in st.session_state: st.session_state.sesiones_chat = {"Nueva Consulta": []}
if "sesion_actual" not in st.session_state: st.session_state.sesion_actual = "Nueva Consulta"

# ==========================================
# FUNCIONES DE AUTENTICACIÓN
# ==========================================
def login_screen():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        if os.path.exists("logo.png"): 
            st.image("logo.png", use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center;'>Chubut.IA</h1>", unsafe_allow_html=True)
            
        st.markdown("<h3 style='text-align: center;'>Acceso al Sistema</h3>", unsafe_allow_html=True)
        
        tab_in, tab_reg = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])
        
        with tab_in:
            email = st.text_input("Email", key="li_email")
            password = st.text_input("Contraseña", type="password", key="li_pass")
            
            if st.button("Entrar", type="primary", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user_data = res.user
                    st.rerun()
                except:
                    st.error("Correo o contraseña incorrectos.")
            
            # Botón corregido sin el error de variant="ghost"
            if st.button("¿Olvidaste tu contraseña?", key="btn_forgot"):
                if email:
                    try:
                        supabase.auth.reset_password_for_email(email)
                        st.info(f"Se envió un enlace de recuperación a: {email}")
                    except:
                        st.error("No pudimos enviar el correo de recuperación.")
                else:
                    st.warning("Por favor, ingresá tu email en el campo de arriba para recuperarlo.")

        with tab_reg:
            new_user = st.text_input("Nombre de Usuario / Estudio", placeholder="Ej: Perez_Asociados")
            new_email = st.text_input("Correo Electrónico")
            new_pass = st.text_input("Elegí una Contraseña", type="password")
            confirm_pass = st.text_input("Confirmá tu Contraseña", type="password")
            
            if st.button("Crear mi Cuenta", use_container_width=True):
                if new_pass != confirm_pass:
                    st.error("Las contraseñas no coinciden. Verificalas.")
                elif len(new_pass) < 6:
                    st.error("La contraseña es muy corta (mínimo 6 caracteres).")
                elif not new_user or not new_email or "@" not in new_email:
                    st.error("Por favor, completá todos los campos correctamente.")
                else:
                    try:
                        # Registro con Metadata para guardar el nombre de usuario
                        res = supabase.auth.sign_up({
                            "email": new_email, 
                            "password": new_pass,
                            "options": {"data": {"display_name": new_user}}
                        })
                        st.success("¡Cuenta creada con éxito! Ya podés ir a la pestaña 'Iniciar Sesión'.")
                    except Exception as e:
                        st.error(f"Error al registrar: {e}")

# ==========================================
# INTERFAZ DE CHAT IA
# ==========================================
def chat_screen():
    user = st.session_state.user_data
    # Sacamos el nombre de usuario que guardamos en el registro
    display_name = user.user_metadata.get("display_name", user.email.split("@")[0])
    
    # Sincronización de créditos con nuestra tabla 'usuarios'
    db_res = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    
    if len(db_res.data) == 0:
        # Si es nuevo, le creamos sus 3 créditos iniciales
        supabase.table("usuarios").insert({
            "usuario": display_name, 
            "email": user.email, 
            "consultas": 3, 
            "password": "AUTH_MANAGED"
        }).execute()
        creditos = 3
    else:
        creditos = db_res.data[0]["consultas"]

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.divider()
        st.markdown(f"👤 **{display_name}**")
        
        if creditos > 0:
            st.success(f"🎁 Consultas gratis: **{creditos}**")
        else:
            st.error("🚫 Consultas agotadas")
            st.markdown("### 💎 Plan Pro")
            st.write("Acceso ilimitado por **6,99 USD/mes**.")
            st.button("Pagar con Mercado Pago", type="primary", use_container_width=True)
        
        st.divider()
        if st.button("➕ Nueva Consulta", use_container_width=True):
            id_chat = len(st.session_state.sesiones_chat) + 1
            st.session_state.sesion_actual = f"Consulta {id_chat}"
            st.session_state.sesiones_chat[st.session_state.sesion_actual] = []
            st.rerun()
            
        if st.button("Cerrar Sesión", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user_data = None
            st.rerun()

    # --- LÓGICA DE IA ---
    @st.cache_resource
    def load_ai():
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectordb = Chroma(persist_directory="MI_BASE_VECTORIAL", embedding_function=embeddings)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        return vectordb, llm

    vectordb, llm = load_ai()
    
    historial = st.session_state.sesiones_chat[st.session_state.sesion_actual]
    
    # Mostrar chat anterior
    for m in historial:
        with st.chat_message(m["role"]): 
            st.markdown(m["content"])

    # Entrada de mensaje
    if pregunta := st.chat_input("Escribí tu consulta sobre jurisprudencia aquí..."):
        if creditos > 0:
            # Mostrar pregunta del usuario
            historial.append({"role": "user", "content": pregunta})
            with st.chat_message("user"): 
                st.markdown(pregunta)
            
            # Generar respuesta de la IA
            with st.chat_message("assistant"):
                with st.spinner("Buscando en fallos provinciales..."):
                    docs = vectordb.similarity_search(pregunta, k=4)
                    contexto = "\n\n".join([d.page_content for d in docs])
                    
                    sys_prompt = f"Sos Chubut.IA, experto en leyes de Chubut. Contexto: {contexto}. Formato: 📌 Carátula, 📅 Fecha, 📝 Cita, ⚖️ Resolución."
                    
                    response = llm.invoke([
                        SystemMessage(content=sys_prompt),
                        HumanMessage(content=pregunta)
                    ])
                    
                    st.markdown(response.content)
                    
                    # Guardar y actualizar créditos
                    historial.append({"role": "assistant", "content": response.content})
                    nueva_cantidad = creditos - 1
                    supabase.table("usuarios").update({"consultas": nueva_cantidad}).eq("email", user.email).execute()
                    
                    # Botón de descarga
                    st.download_button("📄 Descargar Respuesta", response.content, file_name="dictamen_chubut.txt")
        else:
            st.warning("Se terminaron tus consultas gratuitas. Suscribite al Plan Pro para continuar.")

# --- ARRANQUE ---
if st.session_state.user_data is None:
    login_screen()
else:
    chat_screen()
