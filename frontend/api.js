// ================================================================
// API — Chubut.IA
// All HTTP calls to the FastAPI backend
// ================================================================

const BASE = '/api';

const DEFAULT_OPTS = {
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
};

// Ayudante para inyectar el token de Google/Supabase
function getAuthHeaders() {
  const token = localStorage.getItem('access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

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
    method: 'GET',
    headers: { ...DEFAULT_OPTS.headers, ...getAuthHeaders() },
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
    headers: { ...DEFAULT_OPTS.headers, ...getAuthHeaders() },
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
    headers: { ...DEFAULT_OPTS.headers, ...getAuthHeaders() },
  });
  return handleResponse(res);
}

export async function apiDeleteSession(sesionId) {
  const encoded = encodeURIComponent(sesionId);
  const res = await fetch(`${BASE}/chat/sesion/${encoded}`, {
    ...DEFAULT_OPTS,
    method: 'DELETE',
    headers: { ...DEFAULT_OPTS.headers, ...getAuthHeaders() },
  });
  return handleResponse(res);
}

// ── Upload ────────────────────────────────────────────────────────
export async function apiUploadDocument(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/upload/document`, {
    method: 'POST',
    headers: getAuthHeaders(),
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
    headers: getAuthHeaders(),
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
    headers: { ...DEFAULT_OPTS.headers, ...getAuthHeaders() },
    body: JSON.stringify({ historial, titulo }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Error al generar PDF');
  }
  return res.blob();
}
