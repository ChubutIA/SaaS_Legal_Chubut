from fastapi import Request, HTTPException, status
from services.supabase_client import get_supabase


def extract_token(request: Request) -> str | None:
    """
    Extrae el JWT de Supabase desde dos fuentes posibles, en orden de prioridad:

    1. Header  'Authorization: Bearer <token>'
       → Usado por el flujo de Google OAuth (token llega en el hash de la URL,
         el frontend lo guarda en localStorage y lo inyecta en cada request).

    2. Cookie httpOnly 'sb_token'
       → Usado por el flujo de email/password (el backend la settea en /login).

    Al unificar ambas fuentes acá, todos los endpoints protegidos funcionan
    sin importar cómo autenticó el usuario.
    """
    # Prioridad 1: Authorization header (Google OAuth / token en localStorage)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):].strip()
        if token:
            return token

    # Prioridad 2: Cookie httpOnly (login tradicional email/password)
    return request.cookies.get("sb_token") or None


async def get_current_user(request: Request) -> dict:
    """
    Dependency de FastAPI. Valida el token (de cualquier fuente) contra Supabase
    y retorna {"user": <objeto usuario de Supabase>, "token": <str>}.
    Lanza HTTP 401 si no hay token o si es inválido/expirado.
    """
    token = extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Iniciá sesión primero.",
        )

    supabase = get_supabase()
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido.",
            )
        return {"user": user_res.user, "token": token}
    except HTTPException:
        raise  # re-raise los nuestros sin envolverlos
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada. Iniciá sesión nuevamente.",
        )
