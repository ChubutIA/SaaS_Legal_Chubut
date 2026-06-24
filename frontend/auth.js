// ================================================================
// AUTH — Chubut.IA
// ================================================================

import { state, setState, getUserPlanStatus } from './state.js';
import { apiGetMe, apiLogin, apiRegister, apiLogout, apiResetRequest, apiResetConfirm, apiGoogleCallback, apiGetGoogleUrl } from './api.js';
import { showToast, setFeedback, hideModal, switchPanel, renderSidebar, renderHero, showAccessWall } from './ui.js';
import { renderAllMessages } from './chat.js';

export async function checkSession() {
  if (window.location.hash && window.location.hash.includes('access_token')) {
    const hashParams   = new URLSearchParams(window.location.hash.substring(1));
    const accessToken  = hashParams.get('access_token');
    const refreshToken = hashParams.get('refresh_token') || '';

    window.history.replaceState(null, '', window.location.pathname);

    if (accessToken) {
      try {
        const data = await apiGoogleCallback(accessToken, refreshToken);
        if (data?.user) {
          localStorage.setItem('access_token', accessToken);
          onAuthSuccess(data.user);
          showToast(`¡Bienvenido, ${data.user.usuario}!`, 'success');
          return true;
        }
      } catch (err) {
        console.error('Error en callback:', err);
      }
    }
  }

  try {
    const data = await apiGetMe();
    if (data?.user) {
      onAuthSuccess(data.user);
      return true;
    }
  } catch { }
  return false;
}

export async function doGoogleLogin() {
  try {
    const data = await apiGetGoogleUrl();
    window.location.href = data.url;
  } catch (err) {
    setFeedback('login-feedback', 'Error al iniciar con Google.');
  }
}

// ... (resto de tus funciones de login/register/logout se mantienen igual) ...
// Asegurate de que este archivo termine sin ninguna llave "}" extra al final.
