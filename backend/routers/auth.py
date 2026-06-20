from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, Request, status
from pydantic import BaseModel, EmailStr

from services.supabase_client import get_supabase

router = APIRouter()

COOKIE_NAME = "sb_token"
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


# ── Helpers ───────────────────────────────────────────────────────────────────
def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
    )
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


# ── Endpoints ─────────────────────────────────────────────────────────────────
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

    # Obtener datos del usuario de la tabla personalizada
    db_res = supabase.table("usuarios").select("*").eq("email", payload.email).execute()
    datos = db_res.data[0] if db_res.data else {}

    return {
        "ok": True,
        "user": {
            "id": res.user.id,
            "email": res.user.email,
            "usuario": datos.get("usuario", ""),
            "plan": datos.get("plan", "gratis"),
            "vencimiento_trial": datos.get("vencimiento_trial"),
            "vencimiento_pro": datos.get("vencimiento_pro"),
            "historial": datos.get("historial", {"Nueva Consulta": []}),
        },
    }


@router.post("/register")
async def register(payload: RegisterPayload):
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

    supabase = get_supabase()

    # Verificar duplicados
    check_nombre = supabase.table("usuarios").select("usuario").eq("usuario", payload.nombre).execute()
    check_email = supabase.table("usuarios").select("email").eq("email", payload.email).execute()

    if check_nombre.data:
        raise HTTPException(status_code=409, detail="Ese nombre de usuario ya está en uso.")
    if check_email.data:
        raise HTTPException(status_code=409, detail="Este correo electrónico ya está registrado.")

    try:
        supabase.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": {"data": {"display_name": payload.nombre}},
            }
        )
        venc_trial = (datetime.now() - timedelta(hours=3)).date() + timedelta(days=7)
        supabase.table("usuarios").insert(
            {
                "usuario": payload.nombre,
                "email": payload.email,
                "plan": "gratis",
                "vencimiento_trial": str(venc_trial),
                "historial": {"Nueva Consulta": []},
            }
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la cuenta: {str(e)}")

    return {
        "ok": True,
        "message": "Cuenta creada. Revisá tu correo (incluyendo Spam) para confirmar tu cuenta.",
    }


@router.post("/refresh")
async def refresh_session(payload: RefreshPayload, response: Response):
    supabase = get_supabase()
    try:
        res = supabase.auth.refresh_session(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token de refresco inválido o expirado.")

    _set_auth_cookies(response, res.session.access_token, res.session.refresh_token)

    db_res = supabase.table("usuarios").select("*").eq("email", res.user.email).execute()
    datos = db_res.data[0] if db_res.data else {}

    return {
        "ok": True,
        "user": {
            "id": res.user.id,
            "email": res.user.email,
            "usuario": datos.get("usuario", ""),
            "plan": datos.get("plan", "gratis"),
            "vencimiento_trial": datos.get("vencimiento_trial"),
            "vencimiento_pro": datos.get("vencimiento_pro"),
            "historial": datos.get("historial", {"Nueva Consulta": []}),
        },
    }


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
        supabase.auth.verify_otp(
            {"email": payload.email, "token": payload.otp_code, "type": "recovery"}
        )
        supabase.auth.update_user({"password": payload.new_password})
        supabase.auth.sign_out()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo validar el código: {str(e)}")

    _clear_auth_cookies(response)
    return {"ok": True, "message": "Contraseña actualizada. Ya podés iniciar sesión."}


@router.get("/me")
async def get_me(request: Request):
    """Valida la cookie activa y retorna datos frescos del usuario."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado.")

    supabase = get_supabase()
    try:
        user_res = supabase.auth.get_user(token)
        email = user_res.user.email
    except Exception:
        raise HTTPException(status_code=401, detail="Sesión expirada.")

    db_res = supabase.table("usuarios").select("*").eq("email", email).execute()
    if not db_res.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado en la base de datos.")

    datos = db_res.data[0]
    return {
        "ok": True,
        "user": {
            "id": user_res.user.id,
            "email": email,
            "usuario": datos.get("usuario", ""),
            "plan": datos.get("plan", "gratis"),
            "vencimiento_trial": datos.get("vencimiento_trial"),
            "vencimiento_pro": datos.get("vencimiento_pro"),
            "historial": datos.get("historial", {"Nueva Consulta": []}),
        },
    }
