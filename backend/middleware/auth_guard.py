from fastapi import Request, HTTPException, status
from services.supabase_client import get_supabase


async def get_current_user(request: Request) -> dict:
    """
    Extrae y valida el token de sesión de Supabase desde la cookie 'sb_token'.
    Retorna los datos del usuario autenticado o lanza 401.
    """
    token = request.cookies.get("sb_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Iniciá sesión primero.",
        )

    supabase = get_supabase()
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
        return {"user": user_res.user, "token": token}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada. Iniciá sesión nuevamente.",
        )
