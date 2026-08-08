import secrets
from datetime import datetime, timedelta

TOKEN_TTL_HOURS = 24


def generar_token_confirmacion() -> tuple[str, str]:
    """
    Genera un token aleatorio y su fecha de expiración (24hs por default).
    Devuelve (token, expira_iso) listos para guardar en la fila del usuario.
    """
    token = secrets.token_urlsafe(32)
    expira = datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS)
    return token, expira.isoformat()
