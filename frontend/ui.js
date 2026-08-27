// ================================================================
// UI — Chubut.IA
// Sidebar, toasts, modals, typing indicator, hero
// ================================================================

import { state, getUserPlanStatus, formatDate } from './state.js';

// ── Toast System ─────────────────────────────────────────────────
export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { success: '✓', error: '✕', info: '◆' };
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
  container.appendChild(el);

  setTimeout(() => {
    el.classList.add('toast-removing');
    el.addEventListener('animationend', () => el.remove(), { once: true });
  }, 3800);
}

// ── Modal System ─────────────────────────────────────────────────
export function showModal(panelName = 'login') {
  const overlay = document.getElementById('auth-overlay');
  overlay.classList.remove('hidden');
  state.activeModal = panelName;
  switchPanel(panelName);
  document.getElementById('auth-overlay').focus?.();
}

export function hideModal() {
  const overlay = document.getElementById('auth-overlay');
  overlay.classList.add('hidden');
  state.activeModal = null;
  clearModalFeedback();
}

export function switchPanel(name) {
  ['panel-login', 'panel-register', 'panel-reset'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  });
  const target = document.getElementById(`panel-${name}`);
  if (target) target.classList.remove('hidden');
}

function clearModalFeedback() {
  ['login-feedback', 'register-feedback', 'reset-step1-feedback', 'reset-step2-feedback']
    .forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = '';
    });
}

export function setFeedback(elementId, message, isError = true) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerHTML = `<div class="${isError ? 'form-error' : 'form-success'}">${message}</div>`;
}

// ── Sidebar Rendering ─────────────────────────────────────────────
export function renderSidebar() {
  const user = state.user;
  const planStatus = getUserPlanStatus(user);

  renderUserArea(user, planStatus);
  renderPlanArea(planStatus);
  renderSessionButtons(user);
  renderHistoryList();
  renderFooterButtons(user);
  // El bloqueador revisa las puertas cada vez que cambia el menú
  applyPlanRestrictions(planStatus);
}

function renderUserArea(user, planStatus) {
  const el = document.getElementById('sidebar-user-area');
  if (!el) return;

  if (!user) {
    // Guest
    const remaining = Math.max(0, 2 - state.guestCount);
    el.innerHTML = `
      <div class="guest-counter-card">
        <div class="user-card__label">Modo de acceso</div>
        <div class="user-card__name">Acceso Invitado</div>
        <span class="badge badge--guest">Sin cuenta</span>
        <div class="guest-counter-card__count">
          Consultas restantes: <span>${remaining}</span> / 2
        </div>
      </div>`;
    return;
  }

  const badgeMap = {
    pro: `<span class="badge badge--pro">✦ Plan Pro</span>
          <div class="user-card__footer">Vigente hasta el ${formatDate(user.vencimiento_pro)}</div>`,
    trial: `<span class="badge badge--trial">Prueba Gratuita</span>
            <div class="user-card__footer">Vence el ${formatDate(user.vencimiento_trial)}</div>`,
    expired: `<span class="badge badge--expired">Acceso Expirado</span>`,
  };

  el.innerHTML = `
    <div class="user-card">
      <div class="user-card__label">Cuenta verificada</div>
      <div class="user-card__name">${escapeHtml(user.usuario)}</div>
      ${badgeMap[planStatus] || ''}
    </div>`;
}

export function renderPlanArea(planStatus) {
  const el = document.getElementById('sidebar-plan-area');
  if (!el) return;

  if (planStatus === 'pro') {
    el.innerHTML = '';
    return;
  }

  el.innerHTML = `
    <div class="plan-upgrade-box" style="text-align: center;">
      <div class="plan-upgrade-box__label" style="color: var(--gold-light); margin-bottom: 5px;">Planes Pro</div>
      <div style="font-size: 0.8rem; color: #aaa; margin-bottom: 8px;">Mensual o Anual con 25% OFF</div>
    </div>
    <button id="btn-show-plans" class="btn-primary btn-primary--gold"
        style="display:block; width:100%; text-align:center; padding:9px 14px; border-radius:6px; font-size:0.83rem; font-weight:500; letter-spacing:0.04em; border:none; cursor:pointer;">
      ✦ Ver Planes y Suscribirse
    </button>`;

  // Escuchamos el clic y abrimos el muro de pago
  setTimeout(() => {
    const btnShowPlans = document.getElementById('btn-show-plans');
    btnShowPlans?.addEventListener('click', () => {
      showAccessWall('expired'); 
    });
  }, 50);
}

function renderSessionButtons(user) {
  const btnNew = document.getElementById('btn-new-chat');
  const btnAuth = document.getElementById('btn-open-auth');
  const histLabel = document.getElementById('history-label');

  if (user) {
    btnNew?.classList.remove('hidden');
    btnAuth?.classList.add('hidden');
    if (histLabel) histLabel.style.display = 'block';
  } else {
    btnNew?.classList.add('hidden');
    btnAuth?.classList.remove('hidden');
    if (histLabel) histLabel.style.display = 'none';
  }
}

function renderFooterButtons(user) {
  const btnLogout = document.getElementById('btn-logout');
  if (!btnLogout) return;
  if (user) btnLogout.classList.remove('hidden');
  else btnLogout.classList.add('hidden');
}

export function renderHistoryList() {
  const container = document.getElementById('chat-history-list');
  if (!container) return;

  if (!state.user || !state.historial) {
    container.innerHTML = '';
    return;
  }

  const keys = Object.keys(state.historial).reverse();
  container.innerHTML = keys.map(id => `
    <div class="chat-history-item">
      <button class="chat-history-item__btn ${id === state.currentSessionId ? 'active' : ''}"
              data-session="${escapeHtml(id)}">
        <span class="dot"></span>
        <span class="chat-history-item__label">${escapeHtml(id)}</span>
      </button>
      <button class="chat-history-item__del" data-del-session="${escapeHtml(id)}" title="Eliminar">×</button>
    </div>
  `).join('');
}

// ── Welcome Hero ──────────────────────────────────────────────────
export function renderHero() {
  const user = state.user;
  const eyebrow = document.getElementById('hero-eyebrow');
  const title = document.getElementById('hero-title');
  const subtitle = document.getElementById('hero-subtitle');

  if (user) {
    if (eyebrow) eyebrow.textContent = `Bienvenido, ${user.usuario}`;
    if (title) title.innerHTML = '¿En qué puedo<br>asistirte hoy?';
    if (subtitle) subtitle.textContent = 'Jurisprudencia completa de la Provincia de Chubut';
  } else {
    if (eyebrow) eyebrow.textContent = 'Asistente Legal Inteligente';
    if (title) title.innerHTML = 'Redactá demandas y fundamentá<br>tus casos en minutos.';
    if (subtitle) subtitle.textContent = '2 consultas gratuitas · Enlaces oficiales garantizados';
  }
}

// ── Chat Display Helpers ──────────────────────────────────────────
export function showHero(show = true) {
  const hero = document.getElementById('welcome-hero');
  const msgs = document.getElementById('messages-container');
  const exportBar = document.getElementById('export-bar');

  if (show) {
    hero?.classList.remove('hidden');
    msgs?.classList.add('hidden');
    exportBar?.classList.add('hidden');
  } else {
    hero?.classList.add('hidden');
    msgs?.classList.remove('hidden');
  }
}

export function showExportBar(show = true) {
  const el = document.getElementById('export-bar');
  if (!el) return;
  if (show) el.classList.remove('hidden');
  else el.classList.add('hidden');
}

export function showAccessWall(type = null) {
  const el = document.getElementById('access-wall');
  const inputArea = document.getElementById('input-area');
  if (!el) return;

  if (!type) {
    el.classList.add('hidden');
    return;
  }

  el.classList.remove('hidden');
  
  // Ocultamos la barra de chat para que no puedan escribir
  if (inputArea) inputArea.style.display = 'none';

  if (type === 'guest-limit') {
    el.innerHTML = `
      <div class="upgrade-wall" style="margin:12px 20px; max-width: 600px; margin: 0 auto; text-align: center;">
        <h3 style="font-size: 1.4rem; color: #fff; margin-bottom: 10px;">Límite de prueba alcanzado</h3>
        <p style="color: #aaa; margin-bottom: 20px;">Para seguir buscando jurisprudencia y leyes, creá una cuenta gratuita.</p>
        
        <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 20px; text-align: left;">
            <ul style="list-style: none; padding: 0; margin: 0; color: #ddd; font-size: 0.9rem;">
                <li style="margin-bottom: 10px;">✅ Guardá tu historial de consultas</li>
                <li style="margin-bottom: 10px;">✅ Accedé a leyes nacionales (InfoLEG)</li>
                <li>✅ 7 días de prueba completa sin tarjeta</li>
            </ul>
        </div>

        <button id="wall-btn-register" class="btn-primary" style="margin-top:20px; width:100%; font-size: 1rem; padding: 12px;">
          Crear cuenta gratis
        </button>
      </div>`;
 } else if (type === 'expired') {
    el.innerHTML = `
      <div class="upgrade-wall upgrade-wall--expired" style="margin:12px 20px; max-width: 700px; margin: 0 auto; text-align: center;">
        <h2 style="font-size: 1.8rem; color: #fff; margin-bottom: 10px;">Elegí el plan ideal para tu estudio</h2>
        <p style="color: #aaa; margin-bottom: 20px;">Redactá demandas y fundamentá tus casos en minutos, no en horas.</p>
        
        <!-- PESTAÑAS MENSUAL / ANUAL -->
        <div style="display: flex; justify-content: center; margin-bottom: 25px;">
            <div style="background: rgba(0,0,0,0.4); padding: 4px; border-radius: 8px; display: inline-flex; gap: 5px; border: 1px solid rgba(255,255,255,0.1);">
                <button id="wall-tab-mensual" style="padding: 6px 16px; border-radius: 6px; border: none; background: #333; color: #fff; cursor: pointer; font-weight: bold;">Mensual</button>
                <button id="wall-tab-anual" style="padding: 6px 16px; border-radius: 6px; border: none; background: transparent; color: #aaa; cursor: pointer;">Anual (Ahorrá 25%)</button>
            </div>
        </div>

        <div class="plans-wall-grid" style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; text-align: left;">
            
            <!-- PLAN INICIAL -->
            <div class="plan-card" style="flex: 1; min-width: 250px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 25px; display: flex; flex-direction: column;">
                <h3 style="font-size: 1.2rem; margin-bottom: 5px;">Plan Inicial</h3>
                
                <!-- PRECIOS INICIAL -->
                <div id="price-inicial-mensual" style="font-size: 1.5rem; font-weight: bold; color: #fff; margin-bottom: 15px;">$19.990 <span style="font-size: 0.9rem; font-weight: normal; color: #aaa;">/mes</span></div>
                <div id="price-inicial-anual" style="display: none; font-size: 1.5rem; font-weight: bold; color: #fff; margin-bottom: 15px;">$179.900 <span style="font-size: 0.9rem; font-weight: normal; color: #aaa;">/año</span></div>
                
                <p style="font-size: 0.85rem; color: #aaa; margin-bottom: 20px; min-height: 40px;">Para consultas rápidas y legislación oficial.</p>
                
                <ul style="list-style: none; padding: 0; margin: 0 0 25px 0; font-size: 0.9rem; flex-grow: 1;">
                    <li style="margin-bottom: 12px; color: #ddd;">✅ Leyes Nacionales (InfoLEG)</li>
                    <li style="margin-bottom: 12px; color: #ddd;">✅ Leyes Provinciales (Chubut)</li>
                    <li style="margin-bottom: 12px; color: #ddd;">✅ Ordenanzas Municipales</li>
                    <li style="margin-bottom: 12px; color: #eab308;">⚠️ Jurisprudencia (Solo resúmenes)</li>
                    <li style="margin-bottom: 12px; color: #555;">❌ Análisis de PDFs (Expedientes)</li>
                    <li style="margin-bottom: 12px; color: #555;">❌ Calculadora de Liquidaciones</li>
                    <li style="color: #555;">❌ Calculadora de Plazos</li>
                    <li style="color: #555;">❌ Calculadora IPC</li>
                </ul>
                
                <button id="btn-comprar-inicial" data-plan="inicial" style="width: 100%; border-radius: 8px; padding: 10px; border: 1px solid #555; background: #333; color: #fff; cursor: pointer; font-weight: 500;">Elegir Inicial</button>
            </div>

            <!-- PLAN PRO (Recomendado) -->
            <div class="plan-card" style="flex: 1; min-width: 250px; background: rgba(201, 168, 76, 0.1); border: 1px solid #c9a84c; border-radius: 12px; padding: 25px; position: relative; display: flex; flex-direction: column;">
                <div style="position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #c9a84c; color: #000; font-size: 0.75rem; font-weight: bold; padding: 4px 12px; border-radius: 20px;">RECOMENDADO</div>
                
                <h3 style="font-size: 1.2rem; margin-bottom: 5px; color: #c9a84c;">Plan Pro</h3>
                
                <!-- PRECIOS PRO -->
                <div id="price-pro-mensual" style="font-size: 1.5rem; font-weight: bold; color: #fff; margin-bottom: 15px;">$29.990 <span style="font-size: 0.9rem; font-weight: normal; color: #aaa;">/mes</span></div>
                <div id="price-pro-anual" style="display: none; font-size: 1.5rem; font-weight: bold; color: #fff; margin-bottom: 15px;">$269.900 <span style="font-size: 0.9rem; font-weight: normal; color: #aaa;">/año</span></div>

                <p style="font-size: 0.85rem; color: #aaa; margin-bottom: 20px; min-height: 40px;">El arsenal completo para el abogado moderno.</p>
                
                <ul style="list-style: none; padding: 0; margin: 0 0 25px 0; font-size: 0.9rem; flex-grow: 1;">
                    <li style="margin-bottom: 12px; color: #fff; font-weight: 500;">✅ Todo lo del Plan Inicial</li>
                    <li style="margin-bottom: 12px; color: #ddd;">✅ Jurisprudencia Completa y Profunda</li>
                    <li style="margin-bottom: 12px; color: #ddd;">✅ Subida y análisis de PDFs</li>
                    <li style="margin-bottom: 12px; color: #c9a84c; font-weight: 500;">✦ Calculadora de Liquidaciones</li>
                    <li style="color: #c9a84c; font-weight: 500;">✦ Calculadora de Plazos</li>
                    <li style="color: #c9a84c; font-weight: 500;">✦ Calculadora IPC</li>
                </ul>
                
                <button id="btn-comprar-pro" data-plan="pro_mensual" class="btn-primary btn-primary--gold" style="width: 100%; border-radius: 8px; padding: 10px; border: none;">✦ Elegir Pro</button>
            </div>
        </div>
      </div>`;
      // Lógica para cambiar entre mensual y anual dentro del muro
      setTimeout(() => {
        const tabMensual = document.getElementById('wall-tab-mensual');
        const tabAnual = document.getElementById('wall-tab-anual');
        
        const priceIniMensual = document.getElementById('price-inicial-mensual');
        const priceIniAnual = document.getElementById('price-inicial-anual');
        const priceProMensual = document.getElementById('price-pro-mensual');
        const priceProAnual = document.getElementById('price-pro-anual');
        
        const btnInicial = document.getElementById('btn-comprar-inicial');
        const btnPro = document.getElementById('btn-comprar-pro');

        tabMensual?.addEventListener('click', () => {
            tabMensual.style.background = '#333'; tabMensual.style.color = '#fff'; tabMensual.style.fontWeight = 'bold';
            tabAnual.style.background = 'transparent'; tabAnual.style.color = '#aaa'; tabAnual.style.fontWeight = 'normal';
            
            priceIniMensual.style.display = 'block'; priceIniAnual.style.display = 'none';
            priceProMensual.style.display = 'block'; priceProAnual.style.display = 'none';
            
            if(btnInicial) btnInicial.dataset.plan = 'inicial';
            if(btnPro) btnPro.dataset.plan = 'pro_mensual';
        });

        tabAnual?.addEventListener('click', () => {
            tabAnual.style.background = '#333'; tabAnual.style.color = '#fff'; tabAnual.style.fontWeight = 'bold';
            tabMensual.style.background = 'transparent'; tabMensual.style.color = '#aaa'; tabMensual.style.fontWeight = 'normal';
            
            priceIniMensual.style.display = 'none'; priceIniAnual.style.display = 'block';
            priceProMensual.style.display = 'none'; priceProAnual.style.display = 'block';
            
            // Si tenés un plan anual para el inicial, crealo en payments.py. Por ahora uso 'inicial_anual' de ejemplo.
            if(btnInicial) btnInicial.dataset.plan = 'inicial_anual'; 
            if(btnPro) btnPro.dataset.plan = 'pro_anual';
        });
      }, 50);
  }
}
// ── Typing Indicator ──────────────────────────────────────────────
let typingEl = null;

export function showTypingIndicator() {
  const container = document.getElementById('messages-container');
  if (!container || typingEl) return;

  typingEl = document.createElement('div');
  typingEl.className = 'message message--ai';
  typingEl.id = 'typing-indicator';
  typingEl.innerHTML = `
    <div class="message-bubble">
      <div class="message-avatar message-avatar--loading">IA</div>
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>`;
  container.appendChild(typingEl);
  scrollToBottom();
}

export function hideTypingIndicator() {
  if (typingEl) {
    typingEl.remove();
    typingEl = null;
  }
}

// ── Scroll ────────────────────────────────────────────────────────
export function scrollToBottom() {
  const sc = document.getElementById('scroll-container');
  if (sc) sc.scrollTop = sc.scrollHeight;
}

// ── Recording indicator on mic button ─────────────────────────────
export function setRecordingUI(active) {
  const btn = document.getElementById('btn-record');
  if (!btn) return;
  if (active) {
    btn.classList.add('input-icon-btn--recording');
    btn.title = 'Detener grabación';
  } else {
    btn.classList.remove('input-icon-btn--recording');
    btn.title = 'Grabar mensaje de voz';
  }
}

// ── Send button enable/disable ─────────────────────────────────────
export function updateSendBtn() {
  const ta = document.getElementById('chat-textarea');
  const btn = document.getElementById('btn-send');
  if (!ta || !btn) return;
  const hasContent = ta.value.trim().length > 0 || state.pendingFile || state.pendingAudio;
  btn.disabled = !hasContent || state.isLoading;
}

// ── Textarea auto-resize ───────────────────────────────────────────
export function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 180) + 'px';
}

// ── Payment redirect check ─────────────────────────────────────────
export function checkPaymentRedirect() {
  const params = new URLSearchParams(window.location.search);

  if (params.get('status') === 'approved') {
    showToast('¡Pago procesado! Tu Plan Pro está activo.', 'success');
    window.history.replaceState({}, '', window.location.pathname);
    return;
  }

  const confirmacion = params.get('confirmacion');
  if (confirmacion) {
    const mensajes = {
      ok: ['Cuenta confirmada exitosamente. ¡Ya podés hacer tus consultas gratuitas!', 'success'],
      invalido: ['El enlace de confirmación no es válido.', 'error'],
      expirado: ['El enlace de confirmación expiró. Iniciá sesión para pedir uno nuevo.', 'error'],
    };
    const [mensaje, tipo] = mensajes[confirmacion] || ['No pudimos confirmar tu cuenta.', 'error'];
    showToast(mensaje, tipo);
    window.history.replaceState({}, '', window.location.pathname);
  }
}

// ── Utilities ─────────────────────────────────────────────────────
export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Sidebar mobile
export function openSidebar() {
  document.getElementById('sidebar')?.classList.add('open');
  document.getElementById('sidebar-backdrop')?.classList.remove('hidden');
  state.sidebarOpen = true;
}

export function closeSidebar() {
  document.getElementById('sidebar')?.classList.remove('open');
  document.getElementById('sidebar-backdrop')?.classList.add('hidden');
  state.sidebarOpen = false;
}
// ── Checkout Modal ────────────────────────────────────────────────
export function openCheckoutModal() {
  const modal = document.getElementById('checkout-modal');
  if (modal) {
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }
}

export function closeCheckoutModal() {
  const modal = document.getElementById('checkout-modal');
  if (modal) {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
  }
}

export function showPaymentResult(status, message) {
  const container = document.getElementById('payment-brick-container');
  const resultDiv = document.getElementById('payment-result');
  
  if (container) container.style.display = 'none';
  
  if (resultDiv) {
    resultDiv.classList.remove('hidden');
    let html = '';
    
    if (status === 'approved') {
      html = `<h3 style="color: #4ade80;">✅ ¡Pago Exitoso!</h3><p>${message}</p><button onclick="location.reload()" style="margin-top: 15px; padding: 10px 20px; background: #c9a84c; border: none; border-radius: 4px; cursor: pointer; color: black; font-weight: bold;">Comenzar a usar Pro</button>`;
    } else if (status === 'pending') {
      html = `<h3 style="color: #fbbf24;">⏳ Pago Pendiente</h3><p>${message}</p><button onclick="document.getElementById('checkout-modal').classList.add('hidden')" style="margin-top: 15px; padding: 10px 20px; background: #333; border: 1px solid #555; border-radius: 4px; cursor: pointer; color: white;">Cerrar</button>`;
    } else {
      html = `<h3 style="color: #f87171;">❌ Error en el pago</h3><p>${message}</p><button id="btn-retry-payment" style="margin-top: 15px; padding: 10px 20px; background: #333; border: 1px solid #555; border-radius: 4px; cursor: pointer; color: white;">Intentar nuevamente</button>`;
    }
    
    resultDiv.innerHTML = html;

    const retryBtn = document.getElementById('btn-retry-payment');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        resultDiv.classList.add('hidden');
        container.style.display = 'block';
        document.dispatchEvent(new CustomEvent('chubut:retry-payment'));
      });
    }
  }
}
// ── Restricciones de Plan (Patovica Automático) ─────────────────────────
export function applyPlanRestrictions(status) {
  const hasFullAccess = status === 'pro' || status === 'trial';

  const btnAttach = document.getElementById('btn-attach');
  const btnLiq = document.getElementById('btn-open-liquidaciones');
  const btnPlazos = document.getElementById('btn-open-plazos');
  const btnIpc = document.getElementById('btn-open-ipc'); // Agregamos IPC

  // Íconos SVG originales para no perderlos
  const svgLiq = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><line x1="8" y1="10" x2="16" y2="10"></line><line x1="8" y1="14" x2="16" y2="14"></line></svg>`;
  const svgPlazos = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>`;
  const svgIpc = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`; // SVG de IPC

  if (!hasFullAccess) {
    if (btnAttach) btnAttach.style.display = 'none';
    if (btnLiq) {
      btnLiq.innerHTML = `🔒 Liquidaciones (Solo Pro)`;
      btnLiq.style.opacity = "0.6";
    }
    if (btnPlazos) {
      btnPlazos.innerHTML = `🔒 Plazos (Solo Pro)`;
      btnPlazos.style.opacity = "0.6";
    }
    if (btnIpc) {
      btnIpc.innerHTML = `🔒 IPC (Solo Pro)`;
      btnIpc.style.opacity = "0.6";
    }
  } else {
    if (btnAttach) btnAttach.style.display = 'flex';
    if (btnLiq) {
      btnLiq.innerHTML = `${svgLiq} Calculadora de Liquidaciones`;
      btnLiq.style.opacity = "1";
    }
    if (btnPlazos) {
      btnPlazos.innerHTML = `${svgPlazos} Calculadora de Plazos`;
      btnPlazos.style.opacity = "1";
    }
    if (btnIpc) {
      btnIpc.innerHTML = `${svgIpc} Calculadora IPC (Inflación)`;
      btnIpc.style.opacity = "1";
    }
  }
}
