import os
import httpx

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    """
    Valida el token de Cloudflare Turnstile contra la API de Cloudflare.
    Devuelve True si el token es válido, False en cualquier otro caso
    (token vacío, expirado, ya usado, o error de red con Cloudflare).
    """
    secret = os.getenv("TURNSTILE_SECRET_KEY")
    if not secret:
        # Sin secret configurada (ej. entorno local sin .env completo) no
        # bloqueamos el registro, pero lo dejamos bien visible en los logs
        # para que nunca quede así en producción sin que lo notes.
        print("⚠️  TURNSTILE_SECRET_KEY no configurada — el CAPTCHA no se está validando.")
        return True

    if not token:
        return False

    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            data = resp.json()
    except Exception as exc:
        print(f"⚠️  Error validando Turnstile: {exc}")
        return False

    return bool(data.get("success"))
