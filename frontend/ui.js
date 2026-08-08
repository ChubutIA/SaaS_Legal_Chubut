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
  renderProfileArea(user, planStatus);
}

function renderUserArea(user, planStatus) {
  const el = document.getElementById('sidebar-user-area');
  if (!el) return;

  if (!user) {
    // Guest
    const remaining = Math.max(0, 5 - state.guestCount);
    el.innerHTML = `
      <div class="guest-counter-card">
        <div class="user-card__label">Modo de acceso</div>
        <div class="user-card__name">Acceso Invitado</div>
        <span class="badge badge--guest">Sin cuenta</span>
        <div class="guest-counter-card__count">
          Consultas restantes: <span>${remaining}</span> / 5
        </div>
      </div>`;
    return;
  }

  // Usuarios logueados ven su cuenta en el área de perfil (footer de la sidebar)
  el.innerHTML = '';
}

export function renderPlanArea(planStatus) {
  const el = document.getElementById('sidebar-plan-area');
  if (!el) return;

  if (planStatus === 'pro') {
    el.innerHTML = '';
    return;
  }

  el.innerHTML = `
    <div class="plan-upgrade-box">
      <div class="plan-selector-tabs" style="display:flex; gap:4px; margin-bottom:10px; background:rgba(0,0,0,0.3); padding:3px; border-radius:6px;">
        <button id="tab-plan-mensual" class="plan-tab-btn active" style="flex:1; padding:4px 6px; font-size:0.70rem; border-radius:4px; background:var(--gold-glow); color:var(--gold-light); border:1px solid var(--gold-border); cursor:pointer;">Mensual</button>
        <button id="tab-plan-anual" class="plan-tab-btn" style="flex:1; padding:4px 6px; font-size:0.70rem; border-radius:4px; background:transparent; color:var(--text-muted); border:none; cursor:pointer;">Anual 🔥</button>
      </div>

      <div id="plan-price-display">
        <div class="plan-upgrade-box__label">Plan Mensual Pro</div>
        <div class="plan-upgrade-box__price">$39.990 <sub>ARS / mes</sub></div>
        <div class="plan-upgrade-box__desc">Acceso completo e ilimitado.</div>
      </div>
    </div>
    <button id="btn-open-checkout" data-plan="mensual" class="btn-primary btn-primary--gold"
        style="display:block; width:100%; text-align:center; padding:9px 14px; border-radius:6px; font-size:0.83rem; font-weight:500; letter-spacing:0.04em; margin-top:6px; border:none; cursor:pointer;">
      ✦ Activar Plan Pro
    </button>`;

  // Listeners para cambiar entre mensual y anual en la barra lateral
  setTimeout(() => {
    const btnMensual = document.getElementById('tab-plan-mensual');
    const btnAnual = document.getElementById('tab-plan-anual');
    const display = document.getElementById('plan-price-display');
    const checkoutBtn = document.getElementById('btn-open-checkout');

    btnMensual?.addEventListener('click', () => {
      btnMensual.style.background = 'var(--gold-glow)';
      btnMensual.style.color = 'var(--gold-light)';
      btnMensual.style.border = '1px solid var(--gold-border)';
      
      btnAnual.style.background = 'transparent';
      btnAnual.style.color = 'var(--text-muted)';
      btnAnual.style.border = 'none';

      if (display) {
        display.innerHTML = `
          <div class="plan-upgrade-box__label">Plan Mensual Pro</div>
          <div class="plan-upgrade-box__price">$39.990 <sub>ARS / mes</sub></div>
          <div class="plan-upgrade-box__desc">Acceso completo e ilimitado.</div>`;
      }
      if (checkoutBtn) checkoutBtn.dataset.plan = 'mensual';
    });

    btnAnual?.addEventListener('click', () => {
      btnAnual.style.background = 'var(--gold-glow)';
      btnAnual.style.color = 'var(--gold-light)';
      btnAnual.style.border = '1px solid var(--gold-border)';
      
      btnMensual.style.background = 'transparent';
      btnMensual.style.color = 'var(--text-muted)';
      btnMensual.style.border = 'none';

      if (display) {
        display.innerHTML = `
          <div class="plan-upgrade-box__label" style="color:#34D399;">Plan Anual (Ahorrá 16%)</div>
          <div class="plan-upgrade-box__price">$399.900 <sub>ARS / año</sub></div>
          <div class="plan-upgrade-box__desc" style="color:#34D399;">¡2 meses GRATIS incluidos!</div>`;
      }
      if (checkoutBtn) checkoutBtn.dataset.plan = 'anual';
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

function renderProfileArea(user, planStatus) {
  const el = document.getElementById('sidebar-profile-area');
  if (!el) return;

  if (!user) {
    el.innerHTML = '';
    return;
  }

  const planLabelMap = {
    pro: `Plan Pro · vence ${formatDate(user.vencimiento_pro)}`,
    trial: `Prueba · vence ${formatDate(user.vencimiento_trial)}`,
    expired: 'Acceso expirado',
  };
  const planLabel = planLabelMap[planStatus] || '';
  const displayName = user.usuario || user.email || 'Mi cuenta';

  el.innerHTML = `
    <div class="profile-bar" id="profile-bar" tabindex="0" title="${escapeHtml(displayName)}">
      <div class="profile-avatar">${getInitials(displayName)}</div>
      <div class="profile-info">
        <div class="profile-name">${escapeHtml(displayName)}</div>
        <div class="profile-plan${planStatus === 'expired' ? ' profile-plan--expired' : ''}">${planLabel}</div>
      </div>
      <svg class="profile-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
        <polyline points="18 15 12 9 6 15"/>
      </svg>

      <div class="profile-dropdown" id="profile-dropdown">
        <button class="profile-dropdown__item" id="btn-profile-settings" type="button">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
          Configuración
        </button>
        <div class="profile-dropdown__divider"></div>
        <button class="profile-dropdown__item profile-dropdown__item--danger" id="btn-logout" type="button">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          Cerrar sesión
        </button>
      </div>
    </div>`;
}

function getInitials(name) {
  if (!name) return '?';
  const parts = String(name).trim().split(/\s+/);
  const initials = parts.slice(0, 2).map(p => p[0]?.toUpperCase() || '').join('');
  return initials || '?';
}

export function toggleProfileMenu() {
  const bar = document.getElementById('profile-bar');
  const dd = document.getElementById('profile-dropdown');
  if (!bar || !dd) return;
  const isOpen = dd.classList.toggle('open');
  bar.classList.toggle('open', isOpen);
}

export function closeProfileMenu() {
  document.getElementById('profile-dropdown')?.classList.remove('open');
  document.getElementById('profile-bar')?.classList.remove('open');
}

// ── Sidebar Collapse (desktop) ─────────────────────────────────────
const SIDEBAR_COLLAPSE_KEY = 'chubut_sidebar_collapsed';

export function initSidebarCollapse() {
  let collapsed = false;
  try {
    collapsed = localStorage.getItem(SIDEBAR_COLLAPSE_KEY) === '1';
  } catch { /* localStorage bloqueado */ }
  applyCollapseState(collapsed);
}

export function toggleSidebarCollapse() {
  const shell = document.getElementById('app-shell');
  const collapsed = !shell?.classList.contains('sidebar-collapsed');
  applyCollapseState(collapsed);
  try {
    localStorage.setItem(SIDEBAR_COLLAPSE_KEY, collapsed ? '1' : '0');
  } catch { /* localStorage bloqueado */ }
}

function applyCollapseState(collapsed) {
  const shell = document.getElementById('app-shell');
  if (!shell) return;
  shell.classList.toggle('sidebar-collapsed', collapsed);
  state.sidebarCollapsed = collapsed;

  const btn = document.getElementById('btn-sidebar-collapse');
  if (btn) btn.title = collapsed ? 'Expandir barra lateral' : 'Colapsar barra lateral';

  closeProfileMenu();
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
    if (eyebrow) eyebrow.textContent = 'Jurisprudencia · Provincia de Chubut';
    if (title) title.innerHTML = 'Consultá la jurisprudencia<br>sin registrarte.';
    if (subtitle) subtitle.textContent = '5 consultas gratuitas · Sin tarjeta de crédito';
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

  if (type === 'guest-limit') {
    el.innerHTML = `
      <div class="upgrade-wall" style="margin:12px 20px">
        <h3>Alcanzaste el límite de consultas gratuitas.</h3>
        <p style="margin-top:6px">Creá una cuenta gratuita para continuar con 7 días de prueba completa.</p>
        <button id="wall-btn-register" class="btn-primary" style="margin-top:14px; width:100%">
          Crear cuenta — 7 días sin costo
        </button>
      </div>`;
    // Hide input
    if (inputArea) inputArea.style.display = 'none';
  } else if (type === 'expired') {
    el.innerHTML = `
      <div class="upgrade-wall upgrade-wall--expired" style="margin:12px 20px">
        <h3>Tu período de acceso ha finalizado.</h3>
        <p>Activá el Plan Pro para continuar consultando jurisprudencia sin límites.</p>
        <button id="btn-open-checkout" data-plan="mensual" class="btn-primary btn-primary--gold"
            style="display:block; width:100%; text-align:center; margin-top:14px; padding:9px 14px; border-radius:6px; font-size:0.83rem; border:none; cursor:pointer;">
          ✦ Activar Plan Pro
        </button>
      </div>`;
    if (inputArea) inputArea.style.display = 'none';
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
