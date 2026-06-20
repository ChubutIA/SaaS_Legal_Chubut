// ================================================================
// STATE — Chubut.IA
// Central reactive-ish state store for the single-page application
// ================================================================

export const state = {
  // ── Auth ──────────────────────────────────────────────────────
  user: null,          // null = guest, object = authenticated user
  isGuest: true,

  // ── Chat (auth mode) ──────────────────────────────────────────
  currentSessionId: null,
  historial: {},       // { "Session Name": [{ role, content }] }

  // ── Chat (guest mode) ─────────────────────────────────────────
  guestHistory: [],
  guestCount: 0,       // persisted in localStorage

  // ── Pending attachments ───────────────────────────────────────
  pendingFile: null,   // { name, text, sizeKb, pages? }
  pendingAudio: null,  // transcription string

  // ── UI flags ──────────────────────────────────────────────────
  isLoading: false,
  isRecording: false,
  activeModal: null,   // 'login' | 'register' | 'reset' | null
  sidebarOpen: false,  // mobile only
};

// ── Helpers ───────────────────────────────────────────────────────
export function setState(partial) {
  Object.assign(state, partial);
}

// ── Guest count persistence ───────────────────────────────────────
const GUEST_KEY = 'chubut_guest_count';

export function loadGuestCount() {
  try {
    const stored = parseInt(localStorage.getItem(GUEST_KEY) || '0', 10);
    state.guestCount = isNaN(stored) ? 0 : stored;
  } catch {
    state.guestCount = 0;
  }
}

export function incrementGuestCount() {
  state.guestCount = Math.min(state.guestCount + 1, 99);
  try {
    localStorage.setItem(GUEST_KEY, String(state.guestCount));
  } catch { /* localStorage blocked */ }
}

// ── Plan status helpers ───────────────────────────────────────────
export function getUserPlanStatus(user) {
  if (!user) return 'guest';

  const today = new Date();
  today.setHours(today.getHours() - 3); // UTC-3

  if (user.plan === 'pro' && user.vencimiento_pro) {
    const venc = new Date(user.vencimiento_pro);
    if (today <= venc) return 'pro';
  }

  if (user.vencimiento_trial) {
    const venc = new Date(user.vencimiento_trial);
    if (today <= venc) return 'trial';
  }

  return 'expired';
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  const [y, m, d] = dateStr.split('-');
  return `${d}/${m}/${y}`;
}
