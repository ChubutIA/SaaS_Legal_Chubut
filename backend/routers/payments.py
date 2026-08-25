import os
import uuid
import mercadopago
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field

from services.supabase_client import get_supabase
from middleware.auth_guard import get_current_user

router = APIRouter()

# Inicializamos el SDK de Mercado Pago
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

# Configuración de Precios y Días
PLANES = {
    "inicial": {
        "monto": 19990.0,
        "dias": 30,
        "titulo": "Plan Inicial Mensual - Chubut.IA"
    },
    "inicial_anual": {
        "monto": 179900.0,
        "dias": 365,
        "titulo": "Plan Inicial Anual - Chubut.IA (Ahorro 25%)"
    },
    "pro_mensual": {
        "monto": 29990.0,
        "dias": 30,
        "titulo": "Plan Pro Mensual - Chubut.IA"
    },
    "pro_anual": {
        "monto": 269900.0,  # 3 meses gratis
        "dias": 365,
        "titulo": "Plan Pro Anual - Chubut.IA (Ahorro 25%)"
    }
}

if not MP_ACCESS_TOKEN:
    print("ADVERTENCIA: No se encontró MP_ACCESS_TOKEN en las variables de entorno.")
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ── Modelos de Datos (Pydantic) ───────────────────────────────────────────────
class PreferenceRequest(BaseModel):
    tipo_plan: str = "mensual" # "mensual" o "anual"

class PayerIdentification(BaseModel):
    type: str = Field(..., examples=["DNI", "CUIL"])
    number: str

class PayerData(BaseModel):
    email: EmailStr
    identification: PayerIdentification
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class ProcessPaymentRequest(BaseModel):
    token: str
    payment_method_id: str
    transaction_amount: float
    installments: int
    issuer_id: Optional[str] = None
    payer: PayerData
    tipo_plan: str = "mensual"
    description: Optional[str] = "Plan Pro - Chubut.IA"

class PaymentResponse(BaseModel):
    status: str
    payment_id: Optional[int] = None
    status_detail: str
    message: str

# ── Funciones de ayuda ────────────────────────────────────────────────────────
def _get_user_friendly_message(status: str, status_detail: str) -> str:
    messages = {
        "accredited": "¡Pago acreditado! Tu plan ya está activo.",
        "pending_contingency": "Tu pago está en proceso. Te avisaremos por email.",
        "pending_review_manual": "Tu pago está siendo revisado. Puede demorar hasta 2 días hábiles.",
        "cc_rejected_bad_filled_card_number": "Número de tarjeta incorrecto. Verificá los datos.",
        "cc_rejected_bad_filled_date": "Fecha de vencimiento incorrecta.",
        "cc_rejected_bad_filled_other": "Datos de tarjeta incorrectos. Intentá nuevamente.",
        "cc_rejected_bad_filled_security_code": "Código de seguridad incorrecto.",
        "cc_rejected_blacklist": "La tarjeta no puede ser procesada en este momento.",
        "cc_rejected_call_for_authorize": "Debés autorizar el pago con tu banco antes de continuar.",
        "cc_rejected_card_disabled": "La tarjeta está desactivada. Contactá a tu banco.",
        "cc_rejected_duplicated_payment": "Ya realizaste un pago idéntico recientemente.",
        "cc_rejected_high_risk": "El pago fue rechazado por seguridad. Usá otro medio de pago.",
        "cc_rejected_insufficient_amount": "Fondos insuficientes en la tarjeta.",
        "cc_rejected_invalid_installments": "La cantidad de cuotas no está disponible para esta tarjeta.",
        "cc_rejected_max_attempts": "Superaste el límite de intentos. Intentá mañana o usá otra tarjeta."
    }
    return messages.get(status_detail, f"Estado del pago: {status}. Detalle: {status_detail}")

# ── Endpoint para crear Preferencia (Habilita Billetera) ──────────────────────
@router.post("/create-preference")
async def create_preference(payload: PreferenceRequest, auth: dict = Depends(get_current_user)):
    user = auth["user"]
    tipo = payload.tipo_plan if payload.tipo_plan in PLANES else "pro_mensual"
    config_plan = PLANES[tipo]
    
    preference_data = {
        "items": [
            {
                "id": f"plan_{tipo}",
                "title": config_plan["titulo"],
                "quantity": 1,
                "unit_price": config_plan["monto"],
                "currency_id": "ARS"
            }
        ],
        "payer": {
            "email": user.email
        },
        "back_urls": {
            "success": "https://chubutia.com.ar/?status=approved",
            "failure": "https://chubutia.com.ar/?status=failure",
            "pending": "https://chubutia.com.ar/?status=pending"
        },
        "auto_return": "approved",
        "external_reference": f"{user.id}:{tipo}",
        "statement_descriptor": "CHUBUT.IA"
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response.get("response", {})
        return {"preference_id": preference["id"], "amount": config_plan["monto"]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail=f"Error al crear preferencia de Mercado Pago: {str(e)}"
        )

# ── Endpoint de Pago ──────────────────────────────────────────────────────────
@router.post("/process", response_model=PaymentResponse)
async def process_payment(payload: ProcessPaymentRequest, auth: dict = Depends(get_current_user)):
    user = auth["user"]
    user_email = user.email
    supabase = get_supabase()

    tipo = payload.tipo_plan if payload.tipo_plan in PLANES else "pro_mensual"
    config_plan = PLANES[tipo]

    # 1. Armar la información para MP
    payment_data = {
        "transaction_amount": float(payload.transaction_amount),
        "token": payload.token,
        "description": config_plan["titulo"],
        "installments": payload.installments,
        "payment_method_id": payload.payment_method_id,
        "external_reference": f"{user.id}:{tipo}", 
        "payer": {
            "email": user_email, 
            "identification": {
                "type": payload.payer.identification.type,
                "number": payload.payer.identification.number
            }
        }
    }

    if payload.issuer_id:
        payment_data["issuer_id"] = payload.issuer_id

    # 2. Llave de idempotencia
    request_options = mercadopago.config.RequestOptions()
    request_options.custom_headers = {
        "x-idempotency-key": str(uuid.uuid4())
    }

    # 3. Procesar el pago
    try:
        payment_response = sdk.payment().create(payment_data, request_options)
        payment = payment_response.get("response", {})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, 
            detail="No se pudo conectar con Mercado Pago. Intentá en unos minutos."
        )

    mp_status = payment.get("status", "")
    mp_status_detail = payment.get("status_detail", "")
    payment_id = payment.get("id")

    # 4. Actualizamos el Plan correspondiente en Supabase
    if mp_status == "approved":
        dias_a_sumar = config_plan["dias"]
        venc_pro = (datetime.now() - timedelta(hours=3)).date() + timedelta(days=dias_a_sumar)
        
        # Determinar si guardar "inicial" o "pro"
        plan_a_guardar = "inicial" if "inicial" in tipo else "pro"

        try:
            supabase.table("usuarios").update({
                "plan": plan_a_guardar,
                "vencimiento_pro": str(venc_pro)
            }).eq("email", user_email).execute()
        except Exception as e:
            print(f"CRÍTICO: Pago {payment_id} aprobado pero falló BD para {user_email}. Error: {e}")

    # 5. Respuesta
    return PaymentResponse(
        status=mp_status,
        payment_id=payment_id,
        status_detail=mp_status_detail,
        message=_get_user_friendly_message(mp_status, mp_status_detail)
    )
