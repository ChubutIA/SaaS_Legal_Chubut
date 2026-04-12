import streamlit as st
from supabase import create_client, Client
import os

# --- CONEXIÓN ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def mostrar_pantalla_registro():
    st.subheader("Crear Cuenta con Verificación")
    email = st.text_input("Correo Electrónico")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Registrarme"):
        try:
            # Esto manda el mail de confirmación automáticamente
            res = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })
            st.success("¡Casi listo! Te enviamos un mail de confirmación. Por favor, hacé clic en el link para activar tu cuenta.")
            st.info("Una vez que confirmes el mail, podrás iniciar sesión.")
        except Exception as e:
            st.error(f"Error al registrar: {e}")

def mostrar_pantalla_login():
    st.subheader("Iniciar Sesión")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Contraseña", type="password", key="login_pass")
    
    if st.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            # Verificamos si el usuario ya confirmó su mail
            if res.user:
                st.session_state.user_data = res.user
                st.success("Sesión iniciada correctamente")
                st.rerun()
        except Exception as e:
            st.error("Credenciales inválidas o mail no verificado.")

# --- LÓGICA DE NAVEGACIÓN ---
if "user_data" not in st.session_state:
    tab1, tab2 = st.tabs(["Ingresar", "Registrarse"])
    with tab1: mostrar_pantalla_login()
    with tab2: mostrar_pantalla_registro()
else:
    st.write(f"Bienvenido, {st.session_state.user_data.email}")
    if st.button("Cerrar Sesión"):
        supabase.auth.sign_out()
        st.session_state.user_data = None
        st.rerun()
