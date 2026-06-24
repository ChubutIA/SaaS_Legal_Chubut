// ================================================================
// API — Chubut.IA
// ================================================================

const BASE = '/api';

const DEFAULT_OPTS = {
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
};

// AYUDANTE: Aquí está el puente que faltaba para enviar el token
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
export async function apiGetGoogleUrl() {
  const res = await fetch(`${BASE}/auth/google-url`, { credentials: 'include' });
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
  const res = await fetch(`${BASE}/auth/logout`, { ...DEFAULT_OPTS, method: 'POST' });
  return handleResponse(res);
}

export async function apiGetMe() {
  // Ahora usa el puente getAuthHeaders()
  const res = await fetch(`${BASE}/auth/me`, {
    method: 'GET',
    headers: { ...DEFAULT_OPTS.headers, ...getAuthHeaders() },
    credentials: 'include',
  });
  return handleResponse(res);
}

// (El resto de las funciones de Chat/Upload también deben usar getAuthHeaders igual que apiGetMe)
export async function apiChat(historial, sesion_id) {
  const res = await fetch(`${BASE}/chat/`, {
    ...DEFAULT_OPTS,
    method: 'POST',
    headers: { ...DEFAULT_OPTS.headers, ...getAuthHeaders() },
    body: JSON.stringify({ historial, sesion_id }),
  });
  return handleResponse(res);
}
