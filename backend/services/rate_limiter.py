from slowapi import Limiter
from starlette.requests import Request


def get_real_ip(request: Request) -> str:
    """
    Railway pone tu app detrás de un proxy, así que request.client.host
    es la IP interna del proxy, no la del usuario real. La IP real viaja
    en X-Forwarded-For, que Railway sí completa correctamente. Tomamos la
    primera IP de la lista (la del cliente original; las siguientes son
    proxies intermedios).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Contador en memoria del propio proceso. Válido mientras el backend
# corra en UNA sola instancia de Railway. Si el día de mañana escalás
# a varias réplicas, agregá el addon de Redis de Railway y cambiá
# esta línea por:
#   limiter = Limiter(key_func=get_real_ip, storage_uri="redis://<host>:6379")
limiter = Limiter(key_func=get_real_ip)
