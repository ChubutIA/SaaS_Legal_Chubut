import os
import httpx

RESEND_API_URL = "https://api.resend.com/emails"


async def send_confirmation_email(to_email: str, nombre: str, confirm_url: str) -> bool:
    """
    Envía el mail de confirmación de cuenta vía Resend.
    Devuelve True si Resend aceptó el envío, False si falló — nunca
    lanza excepción, para no romper el registro si Resend está caído.
    """
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL", "Chubut.IA <no-reply@chubutia.com.ar>")

    if not api_key:
        print("⚠️  RESEND_API_KEY no configurada — no se pudo enviar el mail de confirmación.")
        return False

    html = f"""
    <div style="font-family: Arial, sans-serif; background:#0A0F1D; padding:32px; color:#E6EEFC;">
      <div style="max-width:480px; margin:0 auto; background:#0F1526; border:1px solid #D4AF3733; border-radius:12px; padding:32px;">
        <h1 style="color:#D4AF37; font-size:20px; margin-bottom:8px;">Chubut.IA</h1>
        <p style="font-size:15px; line-height:1.6;">Hola {nombre},</p>
        <p style="font-size:15px; line-height:1.6;">
          Gracias por registrarte. Confirmá tu cuenta para empezar a usar tus 5 consultas gratuitas:
        </p>
        <p style="text-align:center; margin:28px 0;">
          <a href="{confirm_url}" style="background:#D4AF37; color:#0A0F1D; padding:12px 28px; border-radius:8px; text-decoration:none; font-weight:600; display:inline-block;">
            Confirmar mi cuenta
          </a>
        </p>
        <p style="font-size:13px; color:#94A3B8; line-height:1.6;">
          Si el botón no funciona, copiá y pegá este link en tu navegador:<br>
          <a href="{confirm_url}" style="color:#D4AF37;">{confirm_url}</a>
        </p>
        <p style="font-size:12px; color:#64748B; margin-top:24px;">
          Este enlace expira en 24 horas. Si no creaste esta cuenta, ignorá este correo.
        </p>
      </div>
    </div>
    """.strip()

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": "Confirmá tu cuenta en Chubut.IA",
        "html": html,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                RESEND_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if resp.status_code >= 400:
            print(f"⚠️  Resend respondió {resp.status_code}: {resp.text}")
            return False
        return True
    except Exception as exc:
        print(f"⚠️  Error enviando mail vía Resend: {exc}")
        return False
