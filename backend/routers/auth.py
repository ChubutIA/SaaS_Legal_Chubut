import os
from datetime import datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response, Request, status
from pydantic import BaseModel, EmailStr

from middleware.auth_guard import extract_token
from services.supabase_client import get_supabase

router = APIRouter()

COOKIE_NAME    = "sb_token"
REFRESH_COOKIE = "sb_refresh"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 días


# ── Modelos de entrada ────────────────────────────────────────────────────────
class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class RegisterPayload(BaseModel):
    nombre: str
    email: EmailStr
    password: str


class ResetRequestPayload(BaseModel):
    email: EmailStr


class ResetConfirmPayload(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str


class RefreshPayload(BaseModel):
    refresh_token: str


class GoogleCallbackPayload(BaseModel):
    """
    El frontend envía el access_token (y opcionalmente el refresh_token)
    que recibió en el hash de la URL después del redirect de Google/Supabase.
    """
    access_token: str
    refresh_token: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────
def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Settea cookies httpOnly seguras para ambos tokens."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
    )
    if refresh_token:
        response.set_cookie(
            key=REFRESH_COOKIE,
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=COOKIE_MAX_AGE,
        )


def _clear_auth_cookies(response: Response):
    response.delete_cookie(COOKIE_NAME)
    response.delete_cookie(REFRESH_COOKIE)


def _build_user_response(supabase_user, datos: dict) -> dict:
    """Construye el objeto de usuario estandarizado para el frontend."""
    return {
        "id":                supabase_user.id,
        "email":             supabase_user.email,
        "usuario":           datos.get("usuario", ""),
        "plan":              datos.get("plan", "gratis"),
        "vencimiento_trial": datos.get("vencimiento_trial"),
        "vencimiento_pro":   datos.get("vencimiento_pro"),
        "historial":         datos.get("historial", {"Nueva Consulta": []}),
    }


def _get_or_create_profile(supabase, supabase_user) -> dict:
    """
    Busca el perfil del usuario en la tabla 'usuarios'.
    Si no existe (primer login con Google), lo crea automáticamente con 7 días de trial.
    Retorna el dict de datos del usuario.
    """
    email = supabase_user.email
    db_res = supabase.table("usuarios").select("*").eq("email", email).execute()

    if db_res.data:
        return db_res.data[0]

    # ── Auto-provisioning: primer login OAuth ────────────────────────────────
    # El nombre viene de los metadatos que Google le pasa a Supabase.
    meta        = supabase_user.user_metadata or {}
    nombre      = (
        meta.get("full_name")
        or meta.get("name")
        or meta.get("preferred_username")
        or email.split("@")[0]  # fallback: parte local del email
    )

    venc_trial  = (datetime.now() - timedelta(hours=3)).date() + timedelta(days=7)
    nuevo_perfil = {
        "usuario":           nombre,
        "email":             email,
        "plan":              "gratis",
        "vencimiento_trial": str(venc_trial),
        "historial":         {"Nueva Consulta": []},
    }

    supabase.table("usuarios").insert(nuevo_perfil).execute()

    # Re-fetch para devolver el registro tal como quedó guardado
    db_res2 = supabase.table("usuarios").select("*").eq("email", email).execute()
    return db_res2.data[0] if db_res2.data else nuevo_perfil


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/login")
async def login(payload: LoginPayload, response: Response):
    supabase = get_supabase()
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas o email no confirmado.",
        )

    _set_auth_cookies(response, res.session.access_token, res.session.refresh_token)
    datos = _get_or_create_profile(supabase, res.user)

    return {"ok": True, "user": _build_user_response(res.user, datos)}


@router.post("/register")
async def register(payload: RegisterPayload):
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

    supabase = get_supabase()

    check_nombre = supabase.table("usuarios").select("usuario").eq("usuario", payload.nombre).execute()
    check_email  = supabase.table("usuarios").select("email").eq("email", payload.email).execute()

    if check_nombre.data:
        raise HTTPException(status_code=409, detail="Ese nombre de usuario ya está en uso.")
    if check_email.data:
        raise HTTPException(status_code=409, detail="Este correo electrónico ya está registrado.")

    try:
        supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
            "options": {"data": {"display_name": payload.nombre}},
        })
        venc_trial = (datetime.now() - timedelta(hours=3)).date() + timedelta(days=7)
        supabase.table("usuarios").insert({
            "usuario":           payload.nombre,
            "email":             payload.email,
            "plan":              "gratis",
            "vencimiento_trial": str(venc_trial),
            "historial":         {"Nueva Consulta": []},
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la cuenta: {str(e)}")

    return {
        "ok":      True,
        "message": "Cuenta creada. Revisá tu correo (incluyendo Spam) para confirmar tu cuenta.",
    }


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google-url")
async def get_google_oauth_url(request: Request):
    """
    Genera la URL de autorización de Google OAuth a través de Supabase.
    El frontend redirige al usuario a esta URL en vez de hardcodear
    la URL de Supabase en el JS.
    El 'redirect_to' apunta a la raíz de la app, donde checkSession()
    capturará el token del hash de la URL.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        raise HTTPException(status_code=500, detail="SUPABASE_URL no configurada.")

    # Construimos el redirect_to a partir de la URL base de la request.
    # Esto funciona tanto en localhost como en Railway sin hardcodear dominios.
    origin      = str(request.base_url).rstrip("/")
    redirect_to = origin  # raíz de la app

    oauth_url = (
        f"{supabase_url}/auth/v1/authorize"
        f"?provider=google"
        f"&redirect_to={quote(redirect_to)}"
    )
    return {"ok": True, "url": oauth_url}


@router.post("/google-callback")
async def google_callback(payload: GoogleCallbackPayload, response: Response):
    """
    Recibe el access_token que Google/Supabase dejó en el hash de la URL.
    
    Responsabilidades:
      1. Validar el token contra Supabase Auth.
      2. Auto-crear el perfil en 'usuarios' si es el primer login del usuario.
      3. Settear la cookie httpOnly 'sb_token' para que todos los endpoints
         protegidos funcionen de ahí en adelante sin necesidad de enviar
         el header Authorization en cada request.
      4. Devolver los datos del usuario al frontend.
    """
    supabase = get_supabase()

    # 1. Validar el token
    try:
        user_res = supabase.auth.get_user(payload.access_token)
        if not user_res or not user_res.user:
            raise ValueError("Token vacío")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de Google inválido o expirado.",
        )

    supabase_user = user_res.user

    # 2. Obtener o crear el perfil en la tabla 'usuarios'
    try:
        datos = _get_or_create_profile(supabase, supabase_user)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear el perfil de usuario: {str(e)}",
        )

    # 3. Settear cookies httpOnly → de acá en adelante no necesita el header Bearer
    _set_auth_cookies(response, payload.access_token, payload.refresh_token)

    # 4. Responder
    return {"ok": True, "user": _build_user_response(supabase_user, datos)}


# ── Endpoints estándar ────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_session(payload: RefreshPayload, response: Response):
    supabase = get_supabase()
    try:
        res = supabase.auth.refresh_session(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token de refresco inválido o expirado.")

    _set_auth_cookies(response, res.session.access_token, res.session.refresh_token)
    datos = _get_or_create_profile(supabase, res.user)

    return {"ok": True, "user": _build_user_response(res.user, datos)}


@router.post("/logout")
async def logout(response: Response):
    supabase = get_supabase()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    _clear_auth_cookies(response)
    return {"ok": True}


@router.post("/reset-request")
async def reset_request(payload: ResetRequestPayload):
    supabase = get_supabase()
    try:
        supabase.auth.reset_password_email(payload.email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error técnico: {str(e)}")
    return {"ok": True, "message": f"Código enviado a {payload.email}"}


@router.post("/reset-confirm")
async def reset_confirm(payload: ResetConfirmPayload, response: Response):
    supabase = get_supabase()
    try:
        supabase.auth.verify_otp({
            "email": payload.email,
            "token": payload.otp_code,
            "type":  "recovery",
        })
        supabase.auth.update_user({"password": payload.new_password})
        supabase.auth.sign_out()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo validar el código: {str(e)}")

    _clear_auth_cookies(response)
    return {"ok": True, "message": "Contraseña actualizada. Ya podés iniciar sesión."}


@router.get("/me")
async def get_me(request: Request):
    """
    Valida la sesión activa y retorna datos frescos del usuario.
    Acepta tanto la cookie 'sb_token' (email/password) como el header
    'Authorization: Bearer' (Google OAuth), vía extract_token().
    """
    token = extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado.")

    supabase = get_supabase()
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise Exception("vacío")
    except Exception:
        raise HTTPException(status_code=401, detail="Sesión expirada.")

    datos = _get_or_create_profile(supabase, user_res.user)

    return {"ok": True, "user": _build_user_response(user_res.user, datos)}
