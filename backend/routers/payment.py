from datetime import datetime, timedelta

from fastapi import APIRouter, Request, HTTPException, Query
from services.supabase_client import get_supabase

router = APIRouter()


@router.get("/webhook")
async def mercadopago_redirect(
    status: str = Query(None),
    email: str = Query(None),
):
    """
    Endpoint receptor de redirección de Mercado Pago.
    MercadoPago redirige al usuario a esta URL con ?status=approved&email=...
    después del pago. El email puede pasarse como parámetro extra en la URL de retorno
    configurada en el panel de MercadoPago.
    """
    if status != "approved":
        return {"ok": False, "message": f"Estado de pago: {status}"}

    if not email:
        raise HTTPException(
            status_code=400,
            detail="No se recibió el email del usuario en el callback.",
        )

    supabase = get_supabase()
    venc_pro = (datetime.now() - timedelta(hours=3)).date() + timedelta(days=30)

    supabase.table("usuarios").update(
        {"plan": "pro", "vencimiento_pro": str(venc_pro)}
    ).eq("email", email).execute()

    return {
        "ok": True,
        "message": f"Plan Pro activado para {email} hasta {venc_pro.strftime('%d/%m/%Y')}.",
    }


@router.post("/webhook/ipn")
async def mercadopago_ipn(request: Request):
    """
    Webhook IPN de Mercado Pago para notificaciones de pago server-to-server.
    Configurar esta URL en el panel de Mercado Pago > IPN.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload inválido.")

    # MercadoPago envía: {"action": "payment.created", "data": {"id": "..."}}
    # Se puede expandir para validar el pago via API de MP y obtener el email del pagador.
    # Por ahora registramos el evento para depuración.
    print(f"[IPN MercadoPago] Evento recibido: {data}")

    return {"ok": True}
