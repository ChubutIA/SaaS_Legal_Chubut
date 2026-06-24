// ================================================================
// APP — Chubut.IA
// Main orchestrator: init, event binding, routing
// ================================================================

import { state, loadGuestCount } from './state.js';
import { checkSession, doLogin, doRegister, doLogout, doResetRequest, doResetConfirm } from './auth.js';
import { checkSession, doLogin, doRegister, doLogout, doResetRequest, doResetConfirm, doGoogleLogin } from './auth.js';
import { sendMessage, handleFileSelect, clearPendingFile, toggleRecording, exportToPDF, switchSession, renderAllMessages } from './chat.js';
import { apiNewSession, apiDeleteSession } from './api.js';
import {
  renderSidebar, renderHero, renderHistoryList, showModal, hideModal, switchPanel,
  showToast, autoResizeTextarea, updateSendBtn, checkPaymentRedirect,
  openSidebar, closeSidebar
} from './ui.js';

// ── App Init ──────────────────────────────────────────────────────
async function init() {
  // Load guest count from localStorage
  loadGuestCount();

  // Check for logged-in session (via cookie)
  await checkSession();

  // Initial renders
  renderSidebar();
  renderHero();
  renderAllMessages();

  // Check if returning from MercadoPago payment
  checkPaymentRedirect();

  // Bind all events
  bindSidebarEvents();
  bindInputEvents();
  bindModalEvents();
  bindSuggestionButtons();
}

// ── Sidebar Events ────────────────────────────────────────────────
function bindSidebarEvents() {
  // Mobile toggle
  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    if (state.sidebarOpen) closeSidebar(); else openSidebar();
  });

  document.getElementById('sidebar-backdrop')?.addEventListener('click', closeSidebar);

  // Login / Register button (guest mode)
  document.getElementById('btn-open-auth')?.addEventListener('click', () => showModal('login'));

 // New chat button (auth mode)
  document.getElementById('btn-new-chat')?.addEventListener('click', async () => {
    if (!state.user) return;
    try {
      // Creamos un ID único usando la hora exacta para que NUNCA se mezclen
      const timestamp = new Date().toLocaleTimeString();
      const nuevaSesion = "Consulta " + timestamp;

      // Forzamos un chat totalmente en blanco
      state.historial[nuevaSesion] = [];
      state.currentSessionId = nuevaSesion;

      renderHistoryList();
      renderAllMessages();
    } catch (err) {
      showToast('Error al crear nueva consulta.', 'error');
    }
  });

  // Logout
  document.getElementById('btn-logout')?.addEventListener('click', doLogout);

  // Chat history: click (switch) and delete
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

  // Terms toggle
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

  // Auto-resize + enable send
  textarea?.addEventListener('input', () => {
    autoResizeTextarea(textarea);
    updateSendBtn();
  });

  // Send on Enter (Shift+Enter = newline)
  textarea?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!state.isLoading && !btnSend.disabled) sendMessage();
    }
  });

  // Send button
  btnSend?.addEventListener('click', () => {
    if (!state.isLoading) sendMessage();
  });

  // File attach
  btnAttach?.addEventListener('click', () => fileInput?.click());

  fileInput?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  });

  // Remove pending file
  document.getElementById('btn-remove-file')?.addEventListener('click', () => {
    clearPendingFile();
    updateSendBtn();
  });

  // Audio record
  btnRecord?.addEventListener('click', toggleRecording);

  // Export PDF
  document.getElementById('btn-export-pdf')?.addEventListener('click', exportToPDF);

  // Suggestion buttons (delegated, since they exist in #suggestions-grid)
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

// ── Suggestion Buttons re-bind (public, for re-render after auth) ──
function bindSuggestionButtons() {
  // Already handled via delegation in bindInputEvents
}

// ── Modal Events ──────────────────────────────────────────────────
function bindModalEvents() {
  // Close modal
  document.getElementById('btn-close-modal')?.addEventListener('click', hideModal);

  // Close on overlay click (not on modal content)
  document.getElementById('auth-overlay')?.addEventListener('click', (e) => {
    if (e.target.id === 'auth-overlay') hideModal();
  });

  // Close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && state.activeModal) hideModal();
  });

  // Tab switcher (Login ↔ Register panels)
  document.querySelectorAll('.modal-tab[data-panel]').forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.panel;
      switchPanel(target);
      // Update active tab styling
      document.querySelectorAll('.modal-tab[data-panel]').forEach(t => {
        t.classList.toggle('active', t.dataset.panel === target);
      });
    });
  });

  // Google Login submit
  document.getElementById('btn-google-login')?.addEventListener('click', doGoogleLogin);

  // Login submit
  document.getElementById('btn-do-login')?.addEventListener('click', doLogin);
  document.getElementById('login-password')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doLogin();
  });

  // Register submit
  document.getElementById('btn-do-register')?.addEventListener('click', doRegister);

  // Forgot password
  document.getElementById('btn-show-reset')?.addEventListener('click', () => {
    switchPanel('reset');
    document.getElementById('reset-step-1')?.classList.remove('hidden');
    document.getElementById('reset-step-2')?.classList.add('hidden');
  });

  // Reset: back to login
  document.getElementById('btn-back-to-login')?.addEventListener('click', () => {
    switchPanel('login');
  });

  // Reset step 1: send email
  document.getElementById('btn-do-reset-request')?.addEventListener('click', doResetRequest);

  // Reset step 2: confirm code + new password
  document.getElementById('btn-do-reset-confirm')?.addEventListener('click', doResetConfirm);

  // Reset: back to step 1
  document.getElementById('btn-reset-back')?.addEventListener('click', () => {
    document.getElementById('reset-step-1')?.classList.remove('hidden');
    document.getElementById('reset-step-2')?.classList.add('hidden');
  });
}

// ── Boot ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
