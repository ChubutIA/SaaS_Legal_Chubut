# 0. PARCHE PARA CHROMADB EN LINUX (RAILWAY)
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
import zipfile
import urllib.request
import time
import json
import gdown
import PyPDF2  # <-- Lector de PDFs
from openai import OpenAI  # <-- Motor de transcripción de audio
import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
from supabase import create_client, Client
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from fpdf import FPDF

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO PREMIUM
st.set_page_config(page_title="Chubut.IA - Jurisprudencia", page_icon="favicon.png", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@600;700&display=swap');

        /* ── BORDE BLANCO PARA EL LOGO ────────────────────── */
        [data-testid="stImage"] {
            filter: drop-shadow(1.5px 1.5px 0px white) 
                    drop-shadow(-1.5px -1.5px 0px white) 
                    drop-shadow(1.5px -1.5px 0px white) 
                    drop-shadow(-1.5px 1.5px 0px white);
        }

        /* ── VARIABLES DORADAS ─────────────────────────────── */
        :root {
            --gold-light:   #E8C97A;
            --gold-main:    #D4AF37;
            --gold-deep:    #C5A028;
            --gold-muted:   #A8882A;
            --gold-dark:    #7A6118;
            --gold-glow:    rgba(212, 175, 55, 0.18);
            --gold-border:  rgba(212, 175, 55, 0.28);
            --gold-border-strong: rgba(212, 175, 55, 0.55);
            --navy-deep:    #070B17;
            --navy-card:    #0C1120;
            --navy-surface: #0F172A;
            --navy-hover:   #111827;
        }

        /* ── BASE ─────────────────────────────────────────── */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        footer { visibility: hidden; }

        /* ── FONDO GENERAL ────────────────────────────────── */
        .stApp {
            background-color: var(--navy-deep);
            background-image:
                radial-gradient(ellipse 80% 60% at 50% -10%, rgba(212,175,55,0.06) 0%, transparent 70%);
        }

        /* ── SIDEBAR ──────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background-color: var(--navy-card) !important;
            border-right: 1px solid var(--gold-border) !important;
            box-shadow: 4px 0 24px rgba(0,0,0,0.5) !important;
        }
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] .stMarkdown span {
            color: #94A3B8;
            font-size: 0.82rem;
        }

        /* ── DIVISOR DORADO SIDEBAR ───────────────────────── */
        [data-testid="stSidebar"] hr {
            border: none !important;
            border-top: 1px solid var(--gold-border) !important;
            margin: 1rem 0 !important;
            background: linear-gradient(90deg, transparent, var(--gold-main), transparent) !important;
            height: 1px !important;
        }

        /* ── BOTONES SIDEBAR ──────────────────────────────── */
        [data-testid="stSidebar"] .stButton > button {
            width: 100%;
            text-align: left;
            padding: 9px 14px;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 400;
            letter-spacing: 0.01em;
            color: #94A3B8 !important;
            background-color: transparent !important;
            border: 1px solid rgba(148, 163, 184, 0.12) !important;
            transition: all 0.22s ease;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            color: var(--gold-light) !important;
            background-color: var(--gold-glow) !important;
            border-color: var(--gold-border) !important;
            box-shadow: 0 0 10px rgba(212,175,55,0.08) !important;
        }

        /* ── BOTÓN PRIMARIO ───────────────────────────────── */
        [data-testid="stSidebar"] .stButton > button[kind="primary"],
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #1A2F6A 0%, #1D4ED8 50%, #1A2F6A 100%) !important;
            border: 1px solid var(--gold-border-strong) !important;
            color: var(--gold-light) !important;
            font-weight: 500 !important;
            letter-spacing: 0.04em !important;
            border-radius: 6px !important;
            transition: all 0.22s ease !important;
            box-shadow: 0 1px 8px rgba(212,175,55,0.15), inset 0 1px 0 rgba(212,175,55,0.12) !important;
            text-shadow: 0 1px 3px rgba(0,0,0,0.4) !important;
        }
        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #1E3A8A 100%) !important;
            box-shadow: 0 2px 16px rgba(212,175,55,0.28), inset 0 1px 0 rgba(212,175,55,0.18) !important;
            border-color: var(--gold-main) !important;
        }

        /* ── BURBUJAS DE CHAT — ASISTENTE ─────────────────── */
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
            background-color: var(--navy-card);
            border: 1px solid rgba(212,175,55,0.14);
            border-left: 3px solid var(--gold-border-strong);
            border-radius: 2px 16px 16px 16px;
            padding: 1.4rem 1.6rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.35), 0 0 0 1px rgba(212,175,55,0.04);
        }
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) p {
            color: #CBD5E1;
            font-size: 0.925rem;
            line-height: 1.78;
        }

        /* ── BURBUJAS DE CHAT — USUARIO ───────────────────── */
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
            background: linear-gradient(135deg, #172554 0%, #1E3A8A 100%) !important;
            border: 1px solid var(--gold-border) !important;
            border-right: 3px solid var(--gold-border-strong) !important;
            border-radius: 16px 2px 16px 16px !important;
            padding: 1.2rem 1.6rem !important;
            margin-bottom: 1.2rem !important;
            margin-left: auto !important;
            max-width: 85% !important;
            box-shadow: 0 4px 20px rgba(30,58,138,0.4), 0 0 0 1px rgba(212,175,55,0.06) !important;
        }
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) * {
            color: #DBEAFE !important;
            font-size: 0.925rem !important;
        }

        /* ── CHAT INPUT ───────────────────────────────────── */
        [data-testid="stChatInput"] textarea {
            background-color: var(--navy-card) !important;
            border: 1px solid var(--gold-border) !important;
            border-radius: 10px !important;
            color: #E2E8F0 !important;
            font-size: 0.9rem !important;
            caret-color: var(--gold-main);
            transition: border-color 0.22s, box-shadow 0.22s;
        }
        [data-testid="stChatInput"] textarea:focus {
            border-color: var(--gold-main) !important;
            box-shadow: 0 0 0 3px rgba(212,175,55,0.10), 0 0 20px rgba(212,175,55,0.06) !important;
        }
        [data-testid="stChatInput"] textarea::placeholder {
            color: #475569 !important;
        }

        /* ── DIVISORES GLOBALES ───────────────────────────── */
        hr {
            border: none !important;
            height: 1px !important;
            background: linear-gradient(90deg, transparent, var(--gold-border), transparent) !important;
            margin: 1rem 0 !important;
        }

        /* ── BOTONES DE SUGERENCIA ────────────────────────── */
        .botones-sugerencia button {
            border: 1px solid var(--gold-border) !important;
            border-radius: 8px !important;
            padding: 14px 16px !important;
            text-align: left !important;
            background-color: var(--navy-card) !important;
            color: #94A3B8 !important;
            font-size: 0.82rem !important;
            font-weight: 400 !important;
            line-height: 1.5 !important;
            transition: all 0.22s ease !important;
            box-shadow: inset 0 1px 0 rgba(212,175,55,0.05) !important;
        }
        .botones-sugerencia button:hover {
            border-color: var(--gold-main) !important;
            background-color: var(--gold-glow) !important;
            color: var(--gold-light) !important;
            box-shadow: 0 4px 16px rgba(212,175,55,0.12), inset 0 1px 0 rgba(212,175,55,0.12) !important;
        }

        /* ── TABS ─────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            background-color: transparent;
            border-bottom: 1px solid var(--gold-border);
            gap: 0;
        }
        .stTabs [data-baseweb="tab"] {
            color: #475569;
            font-size: 0.85rem;
            font-weight: 400;
            padding: 10px 22px;
            border-bottom: 2px solid transparent;
            transition: all 0.18s;
        }
        .stTabs [aria-selected="true"] {
            color: var(--gold-light) !important;
            border-bottom: 2px solid var(--gold-main) !important;
            background-color: transparent !important;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: var(--gold-light) !important;
        }

        /* ── INPUTS DE FORMULARIO ─────────────────────────── */
        .stTextInput input, .stTextArea textarea {
            background-color: var(--navy-card) !important;
            border: 1px solid var(--gold-border) !important;
            border-radius: 6px !important;
            color: #E2E8F0 !important;
            font-size: 0.875rem !important;
            transition: border-color 0.22s, box-shadow 0.22s;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: var(--gold-main) !important;
            box-shadow: 0 0 0 3px rgba(212,175,55,0.10) !important;
        }
        .stTextInput label, .stTextArea label {
            color: var(--gold-muted) !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
        }

        /* ── ALERTS ───────────────────────────────────────── */
        .stAlert {
            border-radius: 8px !important;
            font-size: 0.83rem !important;
        }

        /* ── DOWNLOAD BUTTON ──────────────────────────────── */
        .stDownloadButton > button {
            background-color: transparent !important;
            border: 1px solid var(--gold-border) !important;
            border-radius: 6px !important;
            color: var(--gold-muted) !important;
            font-size: 0.8rem !important;
            font-weight: 400 !important;
            transition: all 0.22s !important;
            letter-spacing: 0.02em !important;
        }
        .stDownloadButton > button:hover {
            border-color: var(--gold-main) !important;
            color: var(--gold-light) !important;
            background-color: var(--gold-glow) !important;
            box-shadow: 0 2px 12px rgba(212,175,55,0.12) !important;
        }

        /* ── EXPANDER ─────────────────────────────────────── */
        .streamlit-expanderHeader {
            font-size: 0.82rem !important;
            color: var(--gold-dark) !important;
            font-weight: 400 !important;
        }
        .streamlit-expanderContent {
            background-color: transparent !important;
        }
        [data-testid="stExpander"] {
            border: 1px solid var(--gold-border) !important;
            border-radius: 6px !important;
        }

        /* ── LINK BUTTON ──────────────────────────────────── */
        .stLinkButton > a {
            border: 1px solid var(--gold-border-strong) !important;
            background: linear-gradient(135deg, rgba(212,175,55,0.10), rgba(212,175,55,0.04)) !important;
            color: var(--gold-light) !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            transition: all 0.22s !important;
        }
        .stLinkButton > a:hover {
            background: linear-gradient(135deg, rgba(212,175,55,0.20), rgba(212,175,55,0.10)) !important;
            box-shadow: 0 2px 16px rgba(212,175,55,0.22) !important;
        }

        /* ── SCROLLBAR ────────────────────────────────────── */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(212,175,55,0.20); border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(212,175,55,0.40); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNCIÓN PARA GENERAR PDF (LIMPIO DE EMOJIS)
# ==========================================
def generar_pdf(historial, titulo_chat):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Reporte de Jurisprudencia - Chubut.IA", ln=True, align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 10, f"Generado el: {(datetime.now() - timedelta(hours=3)).strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.multi_cell(0, 10, f"Consulta: {titulo_chat}")
    pdf.ln(5)
    
    for msg in historial:
        rol = "Usuario" if msg["role"] == "user" else "Chubut.IA"
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 10, f"{rol}:", ln=True)
        
        pdf.set_font("helvetica", "", 10)
        texto_limpio = msg["content"].encode('latin-1', 'ignore').decode('latin-1')
        texto_limpio = texto_limpio.replace('**', '')
        pdf.multi_cell(0, 6, texto_limpio)
        pdf.ln(4)
        
    return bytes(pdf.output())

# ==========================================
# 2. SISTEMA BLINDADO DE COOKIES EN LA RAÍZ
# ==========================================
cookie_manager = stx.CookieManager(key="gestor_chubut")

if "set_refresh_token" in st.session_state:
    vencimiento = datetime.now() + timedelta(days=30)
    cookie_manager.set("chubut_refresh", st.session_state.set_refresh_token, expires_at=vencimiento, key="set_ref_root")
    del st.session_state.set_refresh_token

if "del_tokens" in st.session_state:
    cookie_manager.delete("chubut_refresh", key="del_ref_root")
    del st.session_state.del_tokens

if "set_invitado" in st.session_state:
    vencimiento_inv = datetime.now() + timedelta(days=365)
    cookie_manager.set("chubut_invitado", str(st.session_state.set_invitado), expires_at=vencimiento_inv, key="set_inv_root")
    del st.session_state.set_invitado

mis_cookies = cookie_manager.get_all()
if mis_cookies is None:
    st.markdown("<h3 style='text-align: center; color: #475569; margin-top: 20vh; font-family: Inter, sans-serif; font-weight: 300;'>Sincronizando entorno seguro...</h3>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. VARIABLES DE ENTORNO Y SERVICIOS
# ==========================================
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not OPENAI_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Error crítico: Faltan variables de configuración en Railway.")
    st.stop()
else:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if "user_data" not in st.session_state: 
    st.session_state.user_data = None

token_guardado = mis_cookies.get("chubut_refresh")

if token_guardado and st.session_state.user_data is None:
    try:
        res = supabase.auth.refresh_session(token_guardado)
        st.session_state.user_data = res.user
        st.session_state.set_refresh_token = res.session.refresh_token
    except Exception:
        pass 

if "show_login" not in st.session_state: st.session_state.show_login = False
if "guest_history" not in st.session_state: st.session_state.guest_history = []
if "consultas_gastadas" not in st.session_state: st.session_state.consultas_gastadas = 0

# VARIABLES DE ESTADO PARA RECUPERACIÓN DE CONTRASEÑA
if "reset_estado" not in st.session_state: st.session_state.reset_estado = "inicio"
if "reset_email" not in st.session_state: st.session_state.reset_email = ""

galleta_invitado = mis_cookies.get("chubut_invitado")
if galleta_invitado:
    st.session_state.consultas_gastadas = max(st.session_state.consultas_gastadas, int(galleta_invitado))

# ==========================================
# INSTRUCCIÓN PARA LA IA (REGLA DE ORO ACTUALIZADA)
# ==========================================
def generar_instruccion_ia(contexto):
    return f"""Sos Chubut.IA, el motor y asistente jurídico experto de la Provincia de Chubut.

A continuación te proporciono los fragmentos de sentencias reales recuperados de la base de datos oficial o proporcionados por el usuario:
{contexto}

REGLA DE ORO:
Como asistente, tu deber es SIEMPRE mostrar los fallos relevantes. Tienes estrictamente prohibido usar frases evasivas o disculpas. Si los fallos responden a la pregunta, preséntalos con absoluta seguridad. NUNCA inventes fallos que no estén en el contexto. Si el usuario te envía un documento para analizar, compáralo con la base legal disponible de manera profesional.

REGLA PARA PREGUNTAS DE SEGUIMIENTO (¡MUY IMPORTANTE!):
Si el usuario te pide resumir más, explicar mejor, o te hace una pregunta sobre un fallo que ya le mostraste en el mensaje anterior, responde de manera fluida, natural, conversacional y detallada. En estos casos de charla continua, NO es obligatorio que uses el formato estricto de viñetas, simplemente compórtate como un abogado explicando a fondo el caso usando tu memoria y el contexto.

FORMATO PARA BÚSQUEDAS NUEVAS (Respeta este formato estrictamente cuando te pidan buscar casos nuevos):
📌 **[Título Descriptivo del Caso - Ej: Amparo ambiental]**
* 📅 **Fecha del Fallo:** [Transforma la FECHA del contexto ESTRICTAMENTE al formato numérico DD/MM/AAAA. Ej: si dice '29 de Abril de 2026', escribe '29/04/2026'. Si el contexto solo dice 'Año 2026' y no hay día ni mes, escribe 'Sin fecha exacta (2026)']
* 📖 **Cita Textual:** "[Extrae un fragmento con sustancia jurídica del contexto]"
* 📝 **Resumen de los Hechos:** [Redacta un breve resumen de qué trataba el caso según el texto]
* ⚖️ **Resolución:** [Decisión del juez, si figura]
* 🔗 **Ver fallo oficial:** [Link al PDF oficial](INSERTA_AQUI_LA_URL_DEL_CONTEXTO)
(Nota estricta para la IA: El enlace de arriba DEBE estar formateado en Markdown válido, usando los corchetes para el texto "Link al PDF oficial" y los paréntesis para la URL exacta)."""

# ==========================================
# DESCARGO DE RESPONSABILIDAD LEGAL Y SOPORTE
# ==========================================
def mostrar_disclaimer():
    st.markdown("""
        <div style="
            font-size: 0.72rem;
            color: #94A3B8;
            text-align: center;
            margin-top: 28px;
            padding: 12px 10px;
            border-top: 1px solid rgba(212,175,55,0.18);
            line-height: 1.6;
            font-style: italic;
        ">
            Chubut.IA es una herramienta de asistencia basada en inteligencia artificial.
            Los fallos mostrados deben ser verificados en sus fuentes oficiales
            y no reemplazan el asesoramiento legal profesional.
        </div>
    """, unsafe_allow_html=True)

def mostrar_soporte():
    st.markdown("""
        <div style="text-align: center; font-size: 0.77rem; color: #94A3B8; margin-top: 8px; padding-bottom: 18px;">
            ¿Necesitás ayuda?<br>
            <a href="mailto:chubutiaoficial@gmail.com"
               style="color: #D4AF37; text-decoration: none; font-weight: 500; letter-spacing: 0.01em;">
                chubutiaoficial@gmail.com
            </a>
        </div>
    """, unsafe_allow_html=True)

def verificar_pago_entrante(user_email):
    params = st.query_params
    if params.get("status") == "approved" and st.session_state.user_data:
        venc_pro = (datetime.now() - timedelta(hours=3)).date() + timedelta(days=30)
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
    if st.button("← Volver al Chat de Prueba"):
        st.session_state.show_login = False
        st.rerun()

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        st.markdown("""
            <h3 style='
                text-align: center;
                font-family: "Playfair Display", serif;
                font-weight: 700;
                color: #E2E8F0;
                font-size: 1.6rem;
                letter-spacing: 0.01em;
                margin-bottom: 0.5rem;
            '>Acceso al Sistema</h3>
            <div style="
                width: 60px;
                height: 2px;
                background: linear-gradient(90deg, transparent, #D4AF37, transparent);
                margin: 0 auto 1.5rem auto;
                border-radius: 1px;
            "></div>
        """, unsafe_allow_html=True)

        tab_in, tab_reg = st.tabs(["  Entrar  ", "  Registrarse  "])
        
        with tab_in:
            if not st.session_state.get("login_exitoso"):
                with st.form("form_login", clear_on_submit=False):
                    email = st.text_input("Email")
                    password = st.text_input("Contraseña", type="password")
                    btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True)

                if btn_login:
                    if email and password:
                        with st.spinner("Autenticando..."):
                            try:
                                res = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password})
                                st.session_state.temp_user = res.user
                                st.session_state.set_refresh_token = res.session.refresh_token
                                st.session_state.login_exitoso = True
                                st.rerun()
                            except Exception as e:
                                st.error("Credenciales incorrectas o email no confirmado.")
                    else:
                        st.warning("Completá ambos campos.")

                st.write("")
                with st.expander("¿Olvidaste tu contraseña?", expanded=(st.session_state.reset_estado == "codigo_enviado")):
                    
                    if st.session_state.reset_estado == "inicio":
                        with st.form("form_recuperar", clear_on_submit=True):
                            email_recupero = st.text_input("Ingresá tu email registrado")
                            btn_recuperar = st.form_submit_button("Enviar código", use_container_width=True)
                            
                            if btn_recuperar:
                                if email_recupero:
                                    try:
                                        supabase.auth.reset_password_email(email_recupero.strip())
                                        st.session_state.reset_estado = "codigo_enviado"
                                        st.session_state.reset_email = email_recupero.strip()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error técnico: {str(e)}")
                                else:
                                    st.warning("Por favor, ingresá tu email.")
                                    
                    elif st.session_state.reset_estado == "codigo_enviado":
                        st.info(f"Revisá tu bandeja de entrada o Spam. Enviamos un código de seguridad a **{st.session_state.reset_email}**")
                        with st.form("form_nueva_clave", clear_on_submit=True):
                            otp_code = st.text_input("Ingresá el código de seguridad")
                            new_pass = st.text_input("Nueva contraseña", type="password")
                            new_pass_confirm = st.text_input("Confirmar nueva contraseña", type="password")
                            btn_cambiar = st.form_submit_button("Actualizar Contraseña", use_container_width=True)
                            
                            if btn_cambiar:
                                if not otp_code or not new_pass or not new_pass_confirm:
                                    st.warning("Completá todos los campos.")
                                elif new_pass != new_pass_confirm:
                                    st.error("Las contraseñas no coinciden.")
                                elif len(new_pass) < 6:
                                    st.error("La contraseña debe tener al menos 6 caracteres.")
                                else:
                                    try:
                                        supabase.auth.verify_otp({
                                            "email": st.session_state.reset_email,
                                            "token": otp_code.strip(),
                                            "type": "recovery"
                                        })
                                        try:
                                            supabase.auth.update_user({"password": new_pass})
                                            st.success("¡Contraseña actualizada con éxito! Ya podés iniciar sesión arriba.")
                                            st.session_state.reset_estado = "inicio"
                                            st.session_state.reset_email = ""
                                            supabase.auth.sign_out() 
                                        except Exception as pw_error:
                                            st.error(f"El código era correcto, pero falló la contraseña: {str(pw_error)}")
                                            
                                    except Exception as otp_error:
                                        st.error(f"No pudimos validar el código. Razón técnica: {str(otp_error)}")
                                        
                        if st.button("← Usar otro correo / Volver a intentar"):
                            st.session_state.reset_estado = "inicio"
                            st.session_state.reset_email = ""
                            st.rerun()

            if st.session_state.get("login_exitoso"):
                st.success("Pase generado y guardado en tu navegador.")
                st.info("Hacé clic abajo para confirmar tu entrada.")
                if st.button("ENTRAR A MI CUENTA", type="primary", use_container_width=True):
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
                    st.warning("Por favor, completá todos los campos.")
                elif new_pass != confirm_pass:
                    st.error("Las contraseñas no coinciden.")
                elif len(new_pass) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres.")
                else:
                    with st.spinner("Creando cuenta..."):
                        check_user = supabase.table("usuarios").select("usuario").eq("usuario", new_user).execute()
                        check_email = supabase.table("usuarios").select("email").eq("email", new_email.strip()).execute()
                        
                        if len(check_user.data) > 0:
                            st.error("Ese nombre de usuario ya está en uso.")
                        elif len(check_email.data) > 0:
                            st.error("Este correo electrónico ya está registrado.")
                        else:
                            try:
                                venc_trial = (datetime.now() - timedelta(hours=3)).date() + timedelta(days=7)
                                supabase.auth.sign_up({"email": new_email.strip(), "password": new_pass, "options": {"data": {"display_name": new_user}}})
                                supabase.table("usuarios").insert({
                                    "usuario": new_user, "email": new_email.strip(), "plan": "gratis",
                                    "vencimiento_trial": str(venc_trial), "historial": {"Nueva Consulta": []}
                                }).execute()
                                st.success("Cuenta creada con éxito. Revisá tu correo (incluida la carpeta de Spam) para confirmar tu cuenta antes de iniciar sesión.")
                            except Exception as e: 
                                st.error(f"Error técnico: {e}")
                                
        st.write("")
        st.write("")
        mostrar_soporte()

# ==========================================
# CEREBRO GLOBAL (DESCARGA DIRECTA DE GOOGLE DRIVE CON GDOWN)
# ==========================================
@st.cache_resource(show_spinner="Conectando el cerebro jurídico de Chubut (puede demorar unos minutos)...")
def load_ia():
    if not os.path.exists("MI_BASE_VECTORIAL"):
        url_directa = "https://drive.google.com/uc?id=1J0O52QmGKZnx_gazbuZ7-Mq6R48pxz9E"
        gdown.download(url_directa, "base.zip", quiet=False)
        with zipfile.ZipFile("base.zip", 'r') as zr: 
            zr.extractall()
    
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    vdb = Chroma(persist_directory="MI_BASE_VECTORIAL", embedding_function=emb)
    return vdb, ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# LA FUNCIÓN SE ENCIENDE ACÁ:
vdb, llm = load_ia()

# ==========================================
# PANTALLA MODO INVITADO (LÍMITE: 5 CONSULTAS)
# ==========================================
def pantalla_invitado():
    consultas_restantes = 5 - st.session_state.consultas_gastadas

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)

        st.markdown("""
            <div style="
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(212,175,55,0.55), transparent);
                margin: 4px 0 16px 0;
            "></div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, rgba(12,17,32,0.9) 0%, rgba(15,23,42,0.7) 100%);
                border: 1px solid rgba(212,175,55,0.22);
                border-top: 2px solid rgba(212,175,55,0.50);
                border-radius: 8px;
                padding: 14px 16px;
                margin-bottom: 12px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(212,175,55,0.08);
            ">
                <p style="color: #6B7280; font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.10em; margin: 0 0 5px 0; font-weight: 500;">Modo de acceso</p>
                <p style="color: #CBD5E1; font-size: 0.88rem; font-weight: 500; margin: 0 0 8px 0;">Acceso Invitado</p>
                <p style="color: #475569; font-size: 0.78rem; margin: 0; line-height: 1.5;">
                    Consultas restantes:
                    <span style="color: #D4AF37; font-weight: 600; font-size: 0.88rem;">&nbsp;{max(0, consultas_restantes)}</span>
                    <span style="color: #334155;"> / 5</span>
                </p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("Iniciar Sesión / Registrarse", type="primary", use_container_width=True):
            st.session_state.show_login = True
            st.rerun()

        st.markdown("""
            <div style="
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(212,175,55,0.28), transparent);
                margin: 16px 0;
            "></div>
        """, unsafe_allow_html=True)
        
        with st.expander("Términos y Privacidad"):
            st.markdown("""
                <div style="font-size: 0.78rem; color: #475569; line-height: 1.7;">
                    <b style="color: #A8882A;">Propiedad Intelectual:</b> El software y la marca Chubut.IA son propiedad exclusiva del desarrollador. Queda prohibida la reproducción total o parcial.<br><br>
                    <b style="color: #A8882A;">Responsabilidad:</b> Herramienta de asistencia basada en IA. La verificación en fuentes oficiales es responsabilidad del profesional.<br><br>
                    <b style="color: #A8882A;">Privacidad:</b> Cumplimos con la Ley 25.326. Sus consultas son confidenciales.
                </div>
            """, unsafe_allow_html=True)
            
        mostrar_disclaimer()
        mostrar_soporte()

    if not st.session_state.guest_history:
        st.markdown("""
            <div style="
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 42vh;
                text-align: center;
            ">
                <p style="
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    letter-spacing: 0.22em;
                    color: #D4AF37;
                    font-weight: 500;
                    margin-bottom: 16px;
                ">Jurisprudencia · Provincia de Chubut</p>
                <h1 style="
                    font-family: 'Playfair Display', serif;
                    font-size: 2.6rem;
                    font-weight: 700;
                    color: #E2E8F0;
                    margin: 0 0 10px 0;
                    line-height: 1.22;
                    letter-spacing: -0.01em;
                ">Consultá la jurisprudencia<br>sin registrarte.</h1>
                <div style="
                    width: 80px;
                    height: 2px;
                    background: linear-gradient(90deg, transparent, #D4AF37, transparent);
                    margin: 10px auto 14px auto;
                    border-radius: 1px;
                "></div>
                <p style="
                    font-size: 1rem;
                    color: #475569;
                    margin: 0;
                    font-weight: 300;
                ">5 consultas gratuitas · Sin tarjeta de crédito</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <p style='
                text-align: center;
                color: #A8882A;
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.14em;
                font-weight: 500;
                margin: 28px 0 14px 0;
            '>Consultas frecuentes</p>
        """, unsafe_allow_html=True)

        st.markdown("<div class='botones-sugerencia'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("⚖️ Fallos sobre cuota alimentaria", use_container_width=True):
            st.session_state.guest_history.append({"role": "user", "content": "Mostrame fallos recientes sobre cuota alimentaria"})
            st.rerun()
        if c2.button("🚗 Jurisprudencia en accidentes de tránsito", use_container_width=True):
            st.session_state.guest_history.append({"role": "user", "content": "Mostrame jurisprudencia sobre accidentes de tránsito"})
            st.rerun()
        c3, c4 = st.columns(2)
        if c3.button("🏢 Fallos por despidos sin causa", use_container_width=True):
            st.session_state.guest_history.append({"role": "user", "content": "Busca fallos sobre despidos sin causa justificada"})
            st.rerun()
        if c4.button("🏥 Mala praxis médica", use_container_width=True):
            st.session_state.guest_history.append({"role": "user", "content": "Busca fallos relacionados con mala praxis médica"})
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
            
    else:
        for m in st.session_state.guest_history:
            with st.chat_message(m["role"]): st.markdown(m["content"])
            
        st.markdown("<div style='height:1px; background: linear-gradient(90deg, transparent, rgba(212,175,55,0.28), transparent); margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        
        pdf_bytes = generar_pdf(st.session_state.guest_history, "Chat de Prueba Invitado")
        st.download_button(
            label="📄 Exportar conversación a PDF",
            data=pdf_bytes,
            file_name="Reporte_ChubutIA.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.session_state.consultas_gastadas >= 5:
        st.markdown("""
            <div style="
                text-align: center;
                padding: 22px 24px;
                border: 1px solid rgba(212,175,55,0.25);
                border-top: 2px solid rgba(212,175,55,0.55);
                border-radius: 10px;
                background: linear-gradient(135deg, rgba(20,16,4,0.6) 0%, rgba(12,17,32,0.7) 100%);
                margin-top: 20px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            ">
                <p style="color: #7A6118; font-size: 0.85rem; margin: 0 0 10px 0;">
                    Alcanzaste el límite de 5 consultas gratuitas.
                </p>
                <p style="color: #D4AF37; font-size: 0.9rem; font-weight: 500; margin: 0;">
                    Creá una cuenta gratuita para continuar con 7 días de prueba completa.
                </p>
            </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("Crear cuenta — 7 días sin costo", type="primary", use_container_width=True):
            st.session_state.show_login = True
            st.rerun()
    else:
        # AQUI AGREGAMOS LA NUEVA BARRA MULTIMODAL CON MICRÓFONO Y ARCHIVOS
        if prompt := st.chat_input("Consultá, enviá un audio o subí un PDF/TXT...", accept_file=True, accept_audio=True):
            texto_usuario = ""
            archivos = []
            audio_file = None
            
            if isinstance(prompt, dict):
                texto_usuario = prompt.get("text") or ""
                archivos = prompt.get("files", [])
                audio_file = prompt.get("audio")
            elif hasattr(prompt, 'text'):
                texto_usuario = prompt.text or ""
                archivos = getattr(prompt, "files", []) or []
                audio_file = getattr(prompt, "audio", None)
            else:
                texto_usuario = str(prompt) if prompt else ""
                
            mensaje_final = texto_usuario
            
            if audio_file:
                with st.spinner("Transcribiendo mensaje de voz..."):
                    try:
                        client_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
                        audio_file.name = "audio.wav"
                        transcripcion = client_openai.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_file
                        )
                        if mensaje_final:
                            mensaje_final += f"\n\n[Mensaje de Voz]: {transcripcion.text}"
                        else:
                            mensaje_final = transcripcion.text
                    except Exception as e:
                        st.error(f"Error en transcripción: {e}")
            
            if archivos:
                with st.spinner("Procesando documento adjunto..."):
                    texto_extraido = ""
                    for f in archivos:
                        if f.name.lower().endswith('.pdf'):
                            try:
                                pdf_reader = PyPDF2.PdfReader(f)
                                for page in pdf_reader.pages:
                                    txt = page.extract_text()
                                    if txt: texto_extraido += txt + "\n"
                            except Exception:
                                texto_extraido += f"\n[Error al leer el archivo PDF: {f.name}]\n"
                        elif f.name.lower().endswith('.txt'):
                            texto_extraido += f.getvalue().decode('utf-8', errors='ignore') + "\n"
                        else:
                            texto_extraido += f"\n[Archivo adjunto: {f.name} (Por ahora solo extraemos texto de PDF y TXT)]\n"
                    
                    if texto_extraido.strip():
                        mensaje_final += f"\n\n--- DOCUMENTO ADJUNTO PARA ANALIZAR ---\n{texto_extraido.strip()}"
            
            if mensaje_final.strip():
                st.session_state.guest_history.append({"role": "user", "content": mensaje_final.strip()})
                st.rerun()

    if st.session_state.guest_history and st.session_state.guest_history[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Analizando jurisprudencia..."):
                historial_activo = st.session_state.guest_history
                query_usuario = historial_activo[-1]["content"]
                
                if len(historial_activo) > 1:
                    historial_texto = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in historial_activo[-3:-1]]) 
                    prompt_ref = f"Basado en esta charla previa:\n{historial_texto}\n\nReescribe la siguiente pregunta para que sea una consulta de búsqueda completa e independiente en una base de datos. Si el usuario dice 'ese fallo', 'resúmelo' o algo similar, incluye obligatoriamente el tema legal del que venían hablando. Pregunta del usuario: '{query_usuario[:1500]}'. Solo devuelve la pregunta reescrita sin comillas."
                    query_busqueda = llm.invoke([HumanMessage(content=prompt_ref)]).content.replace('"', '').strip()
                else:
                    query_busqueda = query_usuario
                
                # ESCUDO ANTI-CRASHEOS: Solo busca similitud con el núcleo, no con el PDF entero
                query_segura = query_busqueda[:3000]
                docs_original = vdb.similarity_search(query_segura, k=6)
                
                prompt_opt = f"Traduce esta consulta coloquial al lenguaje hiper-formal y técnico que usaría un juez en una sentencia. Enfócate en el núcleo jurídico. Solo devuelve la frase traducida, sin comillas: '{query_segura[:1000]}'"
                query_traducida = llm.invoke([HumanMessage(content=prompt_opt)]).content.replace('"', '').strip()
                docs_traducidos = vdb.similarity_search(query_traducida, k=6)
                
                docs_unicos = []
                textos_vistos = set()
                for d in (docs_original + docs_traducidos):
                    if d.page_content not in textos_vistos:
                        textos_vistos.add(d.page_content)
                        docs_unicos.append(d)
                
                docs = docs_unicos[:10] 

                contexto_final = "\n\n".join([f"📅 FECHA: {d.metadata.get('fecha_completa')}\n🔗 URL: {d.metadata.get('link_pdf')}\n📄 CONTENIDO:\n{d.page_content}" for d in docs])
                
                mensajes = [SystemMessage(content=generar_instruccion_ia(contexto_final))]
                for m in st.session_state.guest_history[:-1]:
                    mensajes.append(HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"]))
                mensajes.append(HumanMessage(content=st.session_state.guest_history[-1]["content"]))
                
                respuesta = llm.invoke(mensajes)
                st.markdown(respuesta.content)
                st.session_state.guest_history.append({"role": "assistant", "content": respuesta.content})
                
                st.session_state.consultas_gastadas += 1
                st.session_state.set_invitado = st.session_state.consultas_gastadas
                st.rerun() 

# ==========================================
# PANTALLA DE CHAT (LOGUEADOS)
# ==========================================
def pantalla_chat():
    user = st.session_state.user_data
    verificar_pago_entrante(user.email)
    db_res = supabase.table("usuarios").select("*").eq("email", user.email).execute()
    datos = db_res.data[0]
    
    hoy = (datetime.now() - timedelta(hours=3)).date()
    
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

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)

        st.markdown("""
            <div style="
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(212,175,55,0.55), transparent);
                margin: 4px 0 16px 0;
            "></div>
        """, unsafe_allow_html=True)

        if es_pro:
            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, rgba(20,16,4,0.85) 0%, rgba(12,17,32,0.9) 100%);
                    border: 1px solid rgba(212,175,55,0.40);
                    border-top: 2px solid rgba(212,175,55,0.70);
                    border-radius: 8px;
                    padding: 14px 16px;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 16px rgba(0,0,0,0.4), inset 0 1px 0 rgba(212,175,55,0.12);
                ">
                    <p style="color: #7A6118; font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.10em; font-weight: 500; margin: 0 0 4px 0;">Cuenta verificada</p>
                    <p style="color: #E2E8F0; font-size: 0.90rem; font-weight: 500; margin: 0 0 8px 0;">{datos['usuario']}</p>
                    <span style="
                        display: inline-block;
                        background: linear-gradient(135deg, rgba(212,175,55,0.18) 0%, rgba(212,175,55,0.08) 100%);
                        border: 1px solid rgba(212,175,55,0.45);
                        color: #D4AF37;
                        font-size: 0.68rem;
                        font-weight: 600;
                        padding: 3px 10px;
                        border-radius: 4px;
                        letter-spacing: 0.10em;
                        text-transform: uppercase;
                    ">✦ Plan Pro</span>
                    <p style="color: #94A3B8; font-size: 0.73rem; margin: 8px 0 0 0;">Vigente hasta el {fecha_pro_formateada}</p>
                </div>
            """, unsafe_allow_html=True)
        elif esta_en_trial:
            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, rgba(12,17,32,0.9) 0%, rgba(15,23,42,0.7) 100%);
                    border: 1px solid rgba(212,175,55,0.18);
                    border-top: 2px solid rgba(212,175,55,0.35);
                    border-radius: 8px;
                    padding: 14px 16px;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
                ">
                    <p style="color: #6B7280; font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.10em; font-weight: 500; margin: 0 0 4px 0;">Cuenta</p>
                    <p style="color: #E2E8F0; font-size: 0.90rem; font-weight: 500; margin: 0 0 8px 0;">{datos['usuario']}</p>
                    <span style="
                        display: inline-block;
                        background: rgba(148, 163, 184, 0.07);
                        border: 1px solid rgba(212,175,55,0.20);
                        color: #A8882A;
                        font-size: 0.68rem;
                        font-weight: 500;
                        padding: 3px 10px;
                        border-radius: 4px;
                        letter-spacing: 0.08em;
                        text-transform: uppercase;
                    ">Prueba Gratuita</span>
                    <p style="color: #94A3B8; font-size: 0.73rem; margin: 8px 0 0 0;">Vence el {fecha_trial_formateada}</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style="
                    background: rgba(127, 29, 29, 0.10);
                    border: 1px solid rgba(239, 68, 68, 0.18);
                    border-radius: 8px;
                    padding: 12px 14px;
                    margin-bottom: 10px;
                ">
                    <p style="color: #475569; font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.09em; font-weight: 500; margin: 0 0 4px 0;">Cuenta</p>
                    <p style="color: #E2E8F0; font-size: 0.88rem; font-weight: 500; margin: 0 0 6px 0;">{datos['usuario']}</p>
                    <span style="
                        display: inline-block;
                        background: rgba(239, 68, 68, 0.10);
                        border: 1px solid rgba(239, 68, 68, 0.25);
                        color: #F87171;
                        font-size: 0.68rem;
                        font-weight: 500;
                        padding: 3px 10px;
                        border-radius: 4px;
                        letter-spacing: 0.06em;
                        text-transform: uppercase;
                    ">Acceso Expirado</span>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("""
            <div style="
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(212,175,55,0.28), transparent);
                margin: 12px 0;
            "></div>
        """, unsafe_allow_html=True)
        
        if not es_pro:
            st.markdown("""
                <div style="
                    border: 1px solid rgba(212,175,55,0.30);
                    border-top: 2px solid rgba(212,175,55,0.60);
                    border-radius: 8px;
                    padding: 16px;
                    background: linear-gradient(135deg, rgba(20,16,4,0.7) 0%, rgba(12,17,32,0.8) 100%);
                    text-align: center;
                    margin-bottom: 12px;
                    box-shadow: 0 2px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(212,175,55,0.10);
                ">
                    <p style="color: #A8882A; font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 500; margin: 0 0 6px 0;">Plan Mensual Pro</p>
                    <p style="font-size: 1.35rem; font-weight: 700; color: #D4AF37; margin: 0; font-family: 'Playfair Display', serif; letter-spacing: 0.01em;">
                        $6.500
                        <span style="font-size: 0.78rem; font-weight: 300; color: #7A6118; font-family: Inter, sans-serif;"> ARS / mes</span>
                    </p>
                    <p style="font-size: 0.75rem; color: #4A3A10; margin: 6px 0 0 0;">Consultas ilimitadas de jurisprudencia.</p>
                </div>
            """, unsafe_allow_html=True)
            st.link_button("✦ Activar Plan Pro", "https://mpago.la/2nDaBRx", type="primary", use_container_width=True)

            st.markdown("""
                <div style="
                    height: 1px;
                    background: linear-gradient(90deg, transparent, rgba(212,175,55,0.28), transparent);
                    margin: 12px 0;
                "></div>
            """, unsafe_allow_html=True)

        if st.button("+ Nueva Consulta", type="primary", use_container_width=True):
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
                if st.button(f"{'▶' if chat_id == st.session_state.sesion_actual else '·'}  {chat_id}", key=f"btn_{chat_id}", use_container_width=True):
                    st.session_state.sesion_actual = chat_id
                    st.rerun()
            with col_del:
                if st.button("×", key=f"del_{chat_id}"):
                    del historial[chat_id]
                    st.session_state.sesion_actual = list(historial.keys())[-1] if historial else "Nueva Consulta"
                    supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
                    st.rerun()

        st.markdown("""
            <div style="
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(212,175,55,0.28), transparent);
                margin: 12px 0;
            "></div>
        """, unsafe_allow_html=True)
        
        if st.button("Cerrar Sesión", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.del_tokens = True
            st.session_state.user_data = None
            st.rerun()

        st.markdown("""
            <div style="
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(212,175,55,0.28), transparent);
                margin: 12px 0;
            "></div>
        """, unsafe_allow_html=True)
            
        with st.expander("Términos y Condiciones"):
            st.markdown("""
                <div style="font-size: 0.78rem; color: #475569; line-height: 1.7;">
                    <b style="color: #A8882A;">Propiedad Intelectual:</b> El software, la base de datos y la marca Chubut.IA son propiedad exclusiva del desarrollador. Queda prohibida la reproducción o ingeniería inversa.<br><br>
                    <b style="color: #A8882A;">Responsabilidad:</b> Chubut.IA es una herramienta de asistencia. Los resultados son informativos. La verificación en fuentes oficiales es responsabilidad del profesional.<br><br>
                    <b style="color: #A8882A;">Datos Personales:</b> Cumplimos con la Ley 25.326. Sus consultas son confidenciales y cifradas.<br><br>
                    <b style="color: #A8882A;">Uso Pro:</b> El acceso es personal e intransferible.
                </div>
            """, unsafe_allow_html=True)

        mostrar_disclaimer()
        mostrar_soporte()

    chat_actual = historial.get(st.session_state.sesion_actual, [])
    
    if not chat_actual:
        st.markdown(f"""
            <div style="
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 42vh;
                text-align: center;
            ">
                <p style="
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    letter-spacing: 0.22em;
                    color: #D4AF37;
                    font-weight: 500;
                    margin-bottom: 14px;
                ">Bienvenido, {datos['usuario']}</p>
                <h1 style="
                    font-family: 'Playfair Display', serif;
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: #E2E8F0;
                    margin: 0 0 10px 0;
                    line-height: 1.25;
                    letter-spacing: -0.01em;
                ">¿En qué puedo asistirte hoy?</h1>
                <div style="
                    width: 80px;
                    height: 2px;
                    background: linear-gradient(90deg, transparent, #D4AF37, transparent);
                    margin: 10px auto 14px auto;
                    border-radius: 1px;
                "></div>
                <p style="
                    font-size: 0.95rem;
                    color: #475569;
                    margin: 0;
                    font-weight: 300;
                ">Jurisprudencia completa de la Provincia de Chubut</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <p style='
                text-align: center;
                color: #A8882A;
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.14em;
                font-weight: 500;
                margin: 28px 0 14px 0;
            '>Consultas frecuentes</p>
        """, unsafe_allow_html=True)

        st.markdown("<div class='botones-sugerencia'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("⚖️ Fallos sobre cuota alimentaria", key="btn_sug1", use_container_width=True):
            chat_actual.append({"role": "user", "content": "Mostrame fallos recientes sobre cuota alimentaria"})
            historial[st.session_state.sesion_actual] = chat_actual
            supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
            st.rerun()
        if c2.button("🚗 Jurisprudencia en accidentes de tránsito", key="btn_sug2", use_container_width=True):
            chat_actual.append({"role": "user", "content": "Mostrame jurisprudencia sobre accidentes de tránsito"})
            historial[st.session_state.sesion_actual] = chat_actual
            supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
            st.rerun()
        c3, c4 = st.columns(2)
        if c3.button("🏢 Fallos por despidos sin causa", key="btn_sug3", use_container_width=True):
            chat_actual.append({"role": "user", "content": "Busca fallos sobre despidos sin causa justificada"})
            historial[st.session_state.sesion_actual] = chat_actual
            supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
            st.rerun()
        if c4.button("🏥 Mala praxis médica", key="btn_sug4", use_container_width=True):
            chat_actual.append({"role": "user", "content": "Busca fallos relacionados con mala praxis médica"})
            historial[st.session_state.sesion_actual] = chat_actual
            supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
    else:
        for m in chat_actual:
            with st.chat_message(m["role"]): st.markdown(m["content"])
            
        st.markdown("<div style='height:1px; background: linear-gradient(90deg, transparent, rgba(212,175,55,0.28), transparent); margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        
        pdf_bytes = generar_pdf(chat_actual, st.session_state.sesion_actual)
        st.download_button(
            label="📄 Exportar conversación a PDF",
            data=pdf_bytes,
            file_name=f"Reporte_{st.session_state.sesion_actual}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if not es_pro and not esta_en_trial:
        st.markdown("""
            <div style="
                text-align: center;
                padding: 28px 24px;
                border: 1px solid rgba(239, 68, 68, 0.15);
                border-radius: 10px;
                background: rgba(127, 29, 29, 0.06);
                margin-top: 20px;
            ">
                <p style="color: #F87171; font-size: 0.9rem; font-weight: 500; margin: 0 0 8px 0;">
                    Tu período de acceso ha finalizado.
                </p>
                <p style="color: #475569; font-size: 0.82rem; margin: 0;">
                    Activá el Plan Pro para continuar consultando jurisprudencia sin límites.
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        # AQUI AGREGAMOS LA NUEVA BARRA MULTIMODAL CON MICRÓFONO Y ARCHIVOS
        if prompt := st.chat_input("Consultá, enviá un audio o subí un PDF/TXT...", accept_file=True, accept_audio=True):
            texto_usuario = ""
            archivos = []
            audio_file = None
            
            # Desenvolver la respuesta del chat según la versión
            if isinstance(prompt, dict):
                texto_usuario = prompt.get("text") or ""
                archivos = prompt.get("files", [])
                audio_file = prompt.get("audio")
            elif hasattr(prompt, 'text'):
                texto_usuario = prompt.text or ""
                archivos = getattr(prompt, "files", []) or []
                audio_file = getattr(prompt, "audio", None)
            else:
                texto_usuario = str(prompt) if prompt else ""
                
            mensaje_final = texto_usuario
            
            # 1. Transcribir Audio
            if audio_file:
                with st.spinner("Transcribiendo mensaje de voz..."):
                    try:
                        client_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
                        audio_file.name = "audio.wav" # Forzamos el nombre para que lo entienda Whisper
                        transcripcion = client_openai.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_file
                        )
                        if mensaje_final:
                            mensaje_final += f"\n\n[Mensaje de Voz]: {transcripcion.text}"
                        else:
                            mensaje_final = transcripcion.text
                    except Exception as e:
                        st.error(f"Error en transcripción: {e}")
            
            # 2. Leer Archivos Adjuntos
            if archivos:
                with st.spinner("Procesando documento adjunto..."):
                    texto_extraido = ""
                    for f in archivos:
                        if f.name.lower().endswith('.pdf'):
                            try:
                                pdf_reader = PyPDF2.PdfReader(f)
                                for page in pdf_reader.pages:
                                    txt = page.extract_text()
                                    if txt: texto_extraido += txt + "\n"
                            except Exception:
                                texto_extraido += f"\n[Error al leer el archivo PDF: {f.name}]\n"
                        elif f.name.lower().endswith('.txt'):
                            texto_extraido += f.getvalue().decode('utf-8', errors='ignore') + "\n"
                        else:
                            texto_extraido += f"\n[Archivo adjunto: {f.name} (Por ahora solo extraemos texto de PDF y TXT)]\n"
                    
                    if texto_extraido.strip():
                        mensaje_final += f"\n\n--- DOCUMENTO ADJUNTO PARA ANALIZAR ---\n{texto_extraido.strip()}"
            
            if mensaje_final.strip():
                chat_actual.append({"role": "user", "content": mensaje_final.strip()})
                historial[st.session_state.sesion_actual] = chat_actual
                supabase.table("usuarios").update({"historial": historial}).eq("email", user.email).execute()
                st.rerun()

        if chat_actual and chat_actual[-1]["role"] == "user":
            with st.chat_message("assistant"):
                with st.spinner("Analizando jurisprudencia..."):
                    
                    historial_activo = chat_actual
                    query_usuario = historial_activo[-1]["content"]
                    
                    if len(historial_activo) > 1:
                        historial_texto = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in historial_activo[-3:-1]]) 
                        prompt_ref = f"Basado en esta charla previa:\n{historial_texto}\n\nReescribe la siguiente pregunta para que sea una consulta de búsqueda completa e independiente en una base de datos. Si el usuario dice 'ese fallo', 'resúmelo' o algo similar, incluye obligatoriamente el tema legal del que venían hablando. Pregunta del usuario: '{query_usuario[:1500]}'. Solo devuelve la pregunta reescrita sin comillas."
                        query_busqueda = llm.invoke([HumanMessage(content=prompt_ref)]).content.replace('"', '').strip()
                    else:
                        query_busqueda = query_usuario
                    
                    # ESCUDO ANTI-CRASHEOS: Limitamos el texto que busca por si suben un PDF gigante
                    query_segura = query_busqueda[:3000]
                    docs_original = vdb.similarity_search(query_segura, k=6)
                    
                    prompt_opt = f"Traduce esta consulta coloquial al lenguaje hiper-formal y técnico que usaría un juez en una sentencia. Enfócate en el núcleo jurídico. Solo devuelve la frase traducida, sin comillas: '{query_segura[:1000]}'"
                    query_traducida = llm.invoke([HumanMessage(content=prompt_opt)]).content.replace('"', '').strip()
                    docs_traducidos = vdb.similarity_search(query_traducida, k=6)
                    
                    docs_unicos = []
                    textos_vistos = set()
                    for d in (docs_original + docs_traducidos):
                        if d.page_content not in textos_vistos:
                            textos_vistos.add(d.page_content)
                            docs_unicos.append(d)
                    
                    docs = docs_unicos[:10] 

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
