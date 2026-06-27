// ================================================================
// APP — Chubut.IA
// Main orchestrator: init, event binding, routing
// ================================================================

import { state, loadGuestCount } from './state.js';
import { checkSession, doLogin, doRegister, doLogout, doResetRequest, doResetConfirm, doGoogleLogin } from './auth.js';
import { sendMessage, handleFileSelect, clearPendingFile, toggleRecording, exportToPDF, switchSession, renderAllMessages } from './chat.js';
import { apiNewSession, apiDeleteSession } from './api.js';
import {
  renderSidebar, renderHero, renderHistoryList, showModal, hideModal, switchPanel,
  showToast, autoResizeTextarea, updateSendBtn, checkPaymentRedirect,
  openSidebar, closeSidebar
} from './ui.js';
import { setupCheckoutListeners } from './checkout.js';
// ── App Init ──────────────────────────────────────────────────────
async function init() {
  loadGuestCount();
  await checkSession();

  renderSidebar();
  renderHero();
  renderAllMessages();

  checkPaymentRedirect();

  bindSidebarEvents();
  bindInputEvents();
  bindModalEvents();
  bindSuggestionButtons();
  setupCheckoutListeners();
}

// ── Sidebar Events ────────────────────────────────────────────────
function bindSidebarEvents() {
  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    if (state.sidebarOpen) closeSidebar(); else openSidebar();
  });

  document.getElementById('sidebar-backdrop')?.addEventListener('click', closeSidebar);
  document.getElementById('btn-open-auth')?.addEventListener('click', () => showModal('login'));

  document.getElementById('btn-new-chat')?.addEventListener('click', async () => {
    if (!state.user) return;
    try {
      const timestamp = new Date().toLocaleTimeString();
      const nuevaSesion = "Consulta " + timestamp;
      
      state.historial[nuevaSesion] = [];
      state.currentSessionId = nuevaSesion;
      
      renderHistoryList();
      renderAllMessages();
    } catch (err) {
      showToast('Error al crear nueva consulta.', 'error');
    }
  });

  document.getElementById('btn-logout')?.addEventListener('click', doLogout);

  document.getElementById('chat-history-list')?.addEventListener('click', async (e) => {
    const btnSession = e.target.closest('[data-session]');
    if (btnSession) {
      const id = btnSession.dataset.session;
      switchSession(id);
      closeSidebar();
      return;
    }

    const btnDel = e.target.closest('[data-del-session]');
    if (btnDel) {
      const id = btnDel.dataset.delSession;
      try {
        const data = await apiDeleteSession(id);
        state.historial = data.historial;
        state.currentSessionId = data.sesion_activa;
        renderHistoryList();
        renderAllMessages();
      } catch (err) {
        showToast(err.message || 'Error al eliminar la consulta.', 'error');
      }
    }
  });

  document.getElementById('terms-toggle')?.addEventListener('click', () => {
    const content = document.getElementById('terms-content');
    content?.classList.toggle('open');
  });
}

// ── Input Events ──────────────────────────────────────────────────
function bindInputEvents() {
  const textarea = document.getElementById('chat-textarea');
  const btnSend   = document.getElementById('btn-send');
  const btnAttach = document.getElementById('btn-attach');
  const btnRecord = document.getElementById('btn-record');
  const fileInput = document.getElementById('hidden-file-input');

  textarea?.addEventListener('input', () => {
    autoResizeTextarea(textarea);
    updateSendBtn();
  });

  textarea?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!state.isLoading && !btnSend.disabled) sendMessage();
    }
  });

  btnSend?.addEventListener('click', () => {
    if (!state.isLoading) sendMessage();
  });

  btnAttach?.addEventListener('click', () => fileInput?.click());

  fileInput?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  });

  document.getElementById('btn-remove-file')?.addEventListener('click', () => {
    clearPendingFile();
    updateSendBtn();
  });

  btnRecord?.addEventListener('click', toggleRecording);
  document.getElementById('btn-export-pdf')?.addEventListener('click', exportToPDF);

  document.getElementById('suggestions-grid')?.addEventListener('click', (e) => {
    const btn = e.target.closest('.suggestion-btn');
    if (!btn) return;
    const query = btn.dataset.query;
    if (query) {
      const ta = document.getElementById('chat-textarea');
      if (ta) {
        ta.value = query;
        ta.dispatchEvent(new Event('input'));
      }
      sendMessage();
    }
  });
}

function bindSuggestionButtons() {}

// ── Modal Events ──────────────────────────────────────────────────
function bindModalEvents() {
  document.getElementById('btn-close-modal')?.addEventListener('click', hideModal);
  document.getElementById('auth-overlay')?.addEventListener('click', (e) => {
    if (e.target.id === 'auth-overlay') hideModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && state.activeModal) hideModal();
  });

  document.querySelectorAll('.modal-tab[data-panel]').forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.panel;
      switchPanel(target);
      document.querySelectorAll('.modal-tab[data-panel]').forEach(t => {
        t.classList.toggle('active', t.dataset.panel === target);
      });
    });
  });

  document.getElementById('btn-do-login')?.addEventListener('click', doLogin);
  document.getElementById('login-password')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doLogin();
  });

  // ACÁ CONECTAMOS EL BOTÓN DE GOOGLE
  document.getElementById('btn-google-login')?.addEventListener('click', doGoogleLogin);

  document.getElementById('btn-do-register')?.addEventListener('click', doRegister);

  document.getElementById('btn-show-reset')?.addEventListener('click', () => {
    switchPanel('reset');
    document.getElementById('reset-step-1')?.classList.remove('hidden');
    document.getElementById('reset-step-2')?.classList.add('hidden');
  });

  document.getElementById('btn-back-to-login')?.addEventListener('click', () => {
    switchPanel('login');
  });

  document.getElementById('btn-do-reset-request')?.addEventListener('click', doResetRequest);
  document.getElementById('btn-do-reset-confirm')?.addEventListener('click', doResetConfirm);
  document.getElementById('btn-reset-back')?.addEventListener('click', () => {
    document.getElementById('reset-step-1')?.classList.remove('hidden');
    document.getElementById('reset-step-2')?.classList.add('hidden');
  });
}

// ── Boot ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
