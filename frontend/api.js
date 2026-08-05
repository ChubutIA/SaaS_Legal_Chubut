// ================================================================
// API — Chubut.IA
// All HTTP calls to the FastAPI backend
// Cookies are sent automatically via credentials: 'include'
// ================================================================

const BASE = '/api';

const DEFAULT_OPTS = {
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
};

async function handleResponse(res) {
  if (res.ok) {
    const ct = res.headers.get('Content-Type') || '';
    if (ct.includes('application/pdf')) return res.blob();
    return res.json();
  }
  let detail = `Error ${res.status}`;
  try {
    const body = await res.json();
    detail = body.detail || detail;
  } catch { /* not json */ }
  throw new Error(detail);
}

// ── Google OAuth Nuevos Endpoints ─────────────────────────────────
export async function apiGetGoogleUrl() {
  const res = await fetch(`${BASE}/auth/google-url`, {
    credentials: 'include',
  });
  return handleResponse(res);
}

export async function apiGoogleCallback(accessToken, refreshToken = '') {
  const res = await fetch(`${BASE}/auth/google-callback`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify({ access_token: accessToken, refresh_token: refreshToken }),
  });
  return handleResponse(res);
}

// ── Auth ──────────────────────────────────────────────────────────
export async function apiLogin(email, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  return handleResponse(res);
}

export async function apiRegister(nombre, email, password) {
  const res = await fetch(`${BASE}/auth/register`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify({ nombre, email, password }),
  });
  return handleResponse(res);
}

export async function apiLogout() {
  const res = await fetch(`${BASE}/auth/logout`, {
    ...DEFAULT_OPTS,
    method: 'POST',
  });
  return handleResponse(res);
}

export async function apiGetMe() {
  const res = await fetch(`${BASE}/auth/me`, {
    credentials: 'include',
  });
  return handleResponse(res);
}

export async function apiRefreshSession(refreshToken) {
  const res = await fetch(`${BASE}/auth/refresh`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  return handleResponse(res);
}

export async function apiResetRequest(email) {
  const res = await fetch(`${BASE}/auth/reset-request`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify({ email }),
  });
  return handleResponse(res);
}

export async function apiResetConfirm(email, otp_code, new_password) {
  const res = await fetch(`${BASE}/auth/reset-confirm`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify({ email, otp_code, new_password }),
  });
  return handleResponse(res);
}

// ── Chat ──────────────────────────────────────────────────────────
export async function apiChat(historial, sesion_id) {
  const res = await fetch(`${BASE}/chat/`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify({ historial, sesion_id }),
  });
  return handleResponse(res);
}

export async function apiChatGuest(historial) {
  const res = await fetch(`${BASE}/chat/guest`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify({ historial, sesion_id: 'guest' }),
  });
  return handleResponse(res);
}

export async function apiNewSession() {
  const res = await fetch(`${BASE}/chat/nueva-sesion`, {
    ...DEFAULT_OPTS,
    method: 'POST',
  });
  return handleResponse(res);
}

export async function apiDeleteSession(sesionId) {
  const encoded = encodeURIComponent(sesionId);
  const res = await fetch(`${BASE}/chat/sesion/${encoded}`, {
    ...DEFAULT_OPTS,
    method: 'DELETE',
  });
  return handleResponse(res);
}

// ── Upload ────────────────────────────────────────────────────────
export async function apiUploadDocument(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/upload/document`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  return handleResponse(res);
}

export async function apiUploadAudio(blob) {
  const form = new FormData();
  form.append('file', blob, 'audio.webm');
  const res = await fetch(`${BASE}/upload/audio`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  return handleResponse(res);
}

// ── Export ────────────────────────────────────────────────────────
export async function apiExportPDF(historial, titulo, isGuest = false) {
  const endpoint = isGuest ? `${BASE}/export/pdf/guest` : `${BASE}/export/pdf`;
  const res = await fetch(endpoint, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify({ historial, titulo }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Error al generar PDF');
  }
  return res.blob();
}
// ── Pagos (Mercado Pago) ──────────────────────────────────────────
export async function processPayment(formData) {
  const body = {
    token: formData.token,
    payment_method_id: formData.payment_method_id,
    transaction_amount: formData.transaction_amount,
    installments: formData.installments || 1,
    issuer_id: formData.issuer_id || null,
    description: 'Plan Pro - Chubut.IA',
    tipo_plan: formData.tipo_plan || 'mensual', // <-- ACÁ ENVIAMOS EL TIPO DE PLAN AL BACKEND
    payer: {
      email: formData.payer.email,
      first_name: formData.payer.first_name || '',
      last_name: formData.payer.last_name || '',
      identification: {
        type: formData.payer.identification?.type || 'DNI',
        number: formData.payer.identification?.number || ''
      }
    }
  };

  const res = await fetch(`${BASE}/payments/process`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    body: JSON.stringify(body)
  });
  
  return handleResponse(res);
}
