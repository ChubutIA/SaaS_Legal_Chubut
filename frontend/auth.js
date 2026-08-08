// ================================================================
// AUTH — Chubut.IA
// Session management, login, register, logout, password reset
// ================================================================

import { state, setState, getUserPlanStatus } from './state.js';
import { apiGetMe, apiLogin, apiRegister, apiLogout, apiResetRequest, apiResetConfirm, apiGetGoogleUrl, apiGoogleCallback } from './api.js';
import { showToast, setFeedback, hideModal, switchPanel, renderSidebar, renderHero, showAccessWall } from './ui.js';
import { renderAllMessages } from './chat.js';

// ── Session Check on Page Load ────────────────────────────────────
export async function checkSession() {
  // 1. Detectar si volvemos de Google con tokens en la URL
  if (window.location.hash && window.location.hash.includes('access_token')) {
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    const accessToken = hashParams.get('access_token');
    const refreshToken = hashParams.get('refresh_token') || '';

    // Limpiamos la URL para que no se vea el token feo en la barra del navegador
    window.history.replaceState(null, '', window.location.pathname);

    if (accessToken) {
      try {
        const data = await apiGoogleCallback(accessToken, refreshToken);
        if (data?.user) {
          onAuthSuccess(data.user);
          showToast(`¡Bienvenido, ${data.user.usuario}!`, 'success');
          return true;
        }
      } catch (err) {
        console.error('Error en callback de Google:', err);
        showToast('No se pudo completar el acceso con Google.', 'error');
      }
    }
  }

  // 2. Verificación normal con la cookie (si no venimos de Google)
  try {
    const data = await apiGetMe();
    if (data?.user) {
      onAuthSuccess(data.user);
      return true;
    }
  } catch {
    // Not authenticated — stay in guest mode
  }
  return false;
}

// ── Google Login ──────────────────────────────────────────────────
export async function doGoogleLogin() {
  const btn = document.getElementById('btn-google-login');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Conectando...';
  }

  try {
    const data = await apiGetGoogleUrl();
    window.location.href = data.url; // Redirigimos a la pantalla de Google
  } catch (err) {
    console.error('Error al obtener URL de Google:', err);
    setFeedback('login-feedback', 'No se pudo iniciar la autenticación con Google.');
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Continuar con Google';
    }
  }
}

// ── Login ─────────────────────────────────────────────────────────
export async function doLogin() {
  const email = document.getElementById('login-email')?.value.trim();
  const password = document.getElementById('login-password')?.value;

  if (!email || !password) {
    setFeedback('login-feedback', 'Completá ambos campos.');
    return;
  }

  const btn = document.getElementById('btn-do-login');
  if (btn) { btn.disabled = true; btn.textContent = 'Autenticando...'; }

  try {
    const data = await apiLogin(email, password);
    onAuthSuccess(data.user);
    hideModal();
    showToast(`Bienvenido, ${data.user.usuario}`, 'success');
  } catch (err) {
    setFeedback('login-feedback', err.message || 'Credenciales incorrectas.');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Iniciar Sesión'; }
  }
}

// ── Register ──────────────────────────────────────────────────────
export async function doRegister() {
  const nombre = document.getElementById('reg-nombre')?.value.trim();
  const email  = document.getElementById('reg-email')?.value.trim();
  const pass   = document.getElementById('reg-pass')?.value;
  const pass2  = document.getElementById('reg-pass2')?.value;

  if (!nombre || !email || !pass || !pass2) {
    setFeedback('register-feedback', 'Completá todos los campos.');
    return;
  }
  if (pass !== pass2) {
    setFeedback('register-feedback', 'Las contraseñas no coinciden.');
    return;
  }
  if (pass.length < 6) {
    setFeedback('register-feedback', 'La contraseña debe tener al menos 6 caracteres.');
    return;
  }

  const turnstileToken = window.turnstile ? window.turnstile.getResponse() : '';
  if (!turnstileToken) {
    setFeedback('register-feedback', 'Completá la verificación de seguridad antes de continuar.');
    return;
  }

  const btn = document.getElementById('btn-do-register');
  if (btn) { btn.disabled = true; btn.textContent = 'Creando cuenta...'; }

  try {
    const data = await apiRegister(nombre, email, pass, turnstileToken);
    setFeedback(
      'register-feedback',
      data.message || 'Cuenta creada. Revisá tu correo para confirmarla.',
      false
    );
  } catch (err) {
    setFeedback('register-feedback', err.message || 'Error al crear la cuenta.');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Crear Cuenta'; }
    window.turnstile?.reset();
  }
}

// ── Logout ────────────────────────────────────────────────────────
export async function doLogout() {
  try {
    await apiLogout();
  } catch { /* ignore */ }

  setState({ user: null, isGuest: true, currentSessionId: null, historial: {} });
  const inputArea = document.getElementById('input-area');
  if (inputArea) inputArea.style.display = '';
  showAccessWall(null);
  renderSidebar();
  renderHero();
  renderAllMessages();
  showToast('Sesión cerrada.', 'info');
}

// ── Password Reset ────────────────────────────────────────────────
let resetEmail = '';

export async function doResetRequest() {
  const email = document.getElementById('reset-email')?.value.trim();
  if (!email) {
    setFeedback('reset-step1-feedback', 'Ingresá tu email.');
    return;
  }

  const btn = document.getElementById('btn-do-reset-request');
  if (btn) { btn.disabled = true; btn.textContent = 'Enviando...'; }

  try {
    await apiResetRequest(email);
    resetEmail = email;

    // Show step 2
    document.getElementById('reset-step-1')?.classList.add('hidden');
    document.getElementById('reset-step-2')?.classList.remove('hidden');

    const info = document.getElementById('reset-step2-info');
    if (info) info.innerHTML = `Revisá tu bandeja o carpeta de Spam. Enviamos un código a <strong>${email}</strong>.`;

  } catch (err) {
    setFeedback('reset-step1-feedback', err.message || 'Error técnico.');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Enviar Código'; }
  }
}

export async function doResetConfirm() {
  const otp   = document.getElementById('reset-otp')?.value.trim();
  const pass  = document.getElementById('reset-new-pass')?.value;
  const pass2 = document.getElementById('reset-confirm-pass')?.value;

  if (!otp || !pass || !pass2) {
    setFeedback('reset-step2-feedback', 'Completá todos los campos.');
    return;
  }
  if (pass !== pass2) {
    setFeedback('reset-step2-feedback', 'Las contraseñas no coinciden.');
    return;
  }
  if (pass.length < 6) {
    setFeedback('reset-step2-feedback', 'Mínimo 6 caracteres.');
    return;
  }

  const btn = document.getElementById('btn-do-reset-confirm');
  if (btn) { btn.disabled = true; btn.textContent = 'Actualizando...'; }

  try {
    const data = await apiResetConfirm(resetEmail, otp, pass);
    setFeedback('reset-step2-feedback', data.message || '¡Contraseña actualizada! Podés iniciar sesión.', false);
    setTimeout(() => {
      switchPanel('login');
      document.getElementById('reset-step-1')?.classList.remove('hidden');
      document.getElementById('reset-step-2')?.classList.add('hidden');
    }, 2000);
  } catch (err) {
    setFeedback('reset-step2-feedback', err.message || 'No se pudo validar el código.');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Actualizar Contraseña'; }
  }
}

// ── Shared: on auth success ───────────────────────────────────────
function onAuthSuccess(user) {
  const historial = user.historial || { 'Nueva Consulta': [] };
  const sessionIds = Object.keys(historial);
  const currentSessionId = sessionIds[sessionIds.length - 1];

  setState({
    user,
    isGuest: false,
    historial,
    currentSessionId,
    guestHistory: [],
  });

  const planStatus = getUserPlanStatus(user);

  // Clear any access wall
  showAccessWall(null);
  const inputArea = document.getElementById('input-area');
  if (inputArea) inputArea.style.display = '';

  // Show expired wall if needed
  if (planStatus === 'expired') {
    showAccessWall('expired');
  }

  renderSidebar();
  renderHero();
  renderAllMessages();
}
