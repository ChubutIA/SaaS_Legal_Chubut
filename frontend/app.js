// ================================================================
// APP — Chubut.IA
// Main orchestrator: init, event binding, routing
// ================================================================

import { state, loadGuestCount, getUserPlanStatus } from './state.js';
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
  bindPlazosEvents();
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

// ── Calculadora de Plazos Events ──────────────────────────────────
function bindPlazosEvents() {
  const btnCalcularPlazo = document.getElementById('btn-calcular-plazo');

  if (btnCalcularPlazo) {
    btnCalcularPlazo.addEventListener('click', async () => {
      const fecha = document.getElementById('plazo-fecha').value;
      const dias = document.getElementById('plazo-dias').value;
      const ciudad = document.getElementById('plazo-ciudad').value;

      if (!fecha || !dias) {
        alert("Por favor, completá la fecha de notificación y los días hábiles.");
        return;
      }

      try {
        const response = await fetch('/api/plazos/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fecha_notificacion: fecha,
            dias_habiles: parseInt(dias),
            ciudad: ciudad
          })
        });

        if (response.ok) {
          const data = await response.json();
          
          // 1. Mostrar Resultado Final y botón Google Calendar
          const partes = data.fecha_vencimiento.split("-");
          const fechaFormateada = `${partes[2]}/${partes[1]}/${partes[0]}`;
          document.getElementById('plazo-fecha-texto').innerText = fechaFormateada;
          document.getElementById('btn-gcal').href = data.google_calendar_url;
          document.getElementById('plazo-resultado').style.display = 'block';

          // 2. Dibujar Calendario Visual
          const calContainer = document.getElementById('calendario-plazos-container');
          const calGrid = document.getElementById('calendario-plazos-grid');
          calGrid.innerHTML = ''; // Limpiar grilla anterior

          if (data.detalle_calendario && data.detalle_calendario.length > 0) {
            // Parseamos la primera fecha para saber en qué día de la semana cae
            const parseDate = (d) => new Date(d + 'T00:00:00');
            const firstDay = parseDate(data.detalle_calendario[0].fecha);
            
            // JS: 0 es Domingo, 1 es Lunes. Lo ajustamos para que 0 sea Lunes.
            let startDayOfWeek = firstDay.getDay();
            startDayOfWeek = startDayOfWeek === 0 ? 6 : startDayOfWeek - 1;

            // Rellenar espacios en blanco antes del primer día
            for (let i = 0; i < startDayOfWeek; i++) {
              const emptyCell = document.createElement('div');
              emptyCell.className = 'cal-day empty';
              calGrid.appendChild(emptyCell);
            }

            // Dibujar los días
            data.detalle_calendario.forEach(dia => {
              const cell = document.createElement('div');
              const dDate = parseDate(dia.fecha);
              const diaMes = dDate.getDate();
              const mesStr = dDate.toLocaleDateString('es-AR', { month: 'short' });

              // Asignar clases base
              cell.className = `cal-day ${dia.tipo}`;

              // Sub-clasificación para colores estilo Chronos
              if (dia.tipo === 'inhabíl') {
                const desc = dia.descripcion.toLowerCase();
                if (desc.includes('suspensión')) cell.classList.add('suspension');
                else if (desc.includes('sábado') || desc.includes('domingo')) cell.classList.add('finde');
                else cell.classList.add('feriado'); // Feriados
              }

              // Inyectar HTML de la tarjeta del día
              cell.innerHTML = `
                <div class="cal-date">${diaMes} ${mesStr}</div>
                <div class="cal-desc">${dia.descripcion}</div>
              `;
              calGrid.appendChild(cell);
            });

            calContainer.classList.remove('hidden');
          }

        } else {
          alert("Hubo un error al calcular el plazo. Revisá los datos.");
        }
      } catch (error) {
        console.error(error);
        alert("Error de conexión con el servidor.");
      }
    });
  }
}
// ── Boot ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
