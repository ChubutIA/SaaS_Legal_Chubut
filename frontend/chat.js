// ================================================================
// CHAT — Chubut.IA
// Message rendering, send logic, file upload, audio recording, export
// ================================================================

import { state, setState, getUserPlanStatus, incrementGuestCount } from './state.js';
import { apiChat, apiChatGuest, apiUploadDocument, apiUploadAudio, apiExportPDF } from './api.js';
import {
  showTypingIndicator, hideTypingIndicator, showHero, showExportBar,
  showAccessWall, scrollToBottom, setRecordingUI, updateSendBtn,
  showToast, renderHistoryList, escapeHtml
} from './ui.js';

// ── Marked.js configuration ───────────────────────────────────────
let markedReady = false;

function setupMarked() {
  if (markedReady || typeof marked === 'undefined') return;
  const renderer = new marked.Renderer();
  
  // PARCHE PARA LA VERSIÓN NUEVA DE MARKED.JS
  renderer.link = (href, title, text) => {
    // Si la librería nos manda el formato nuevo (Objeto)
    if (typeof href === 'object') {
        text = href.text;
        title = href.title || '';
        href = href.href;
    }
    return `<a href="${href}" target="_blank" rel="noopener noreferrer" title="${title}">${text}</a>`;
  };

  marked.setOptions({ renderer, breaks: true, gfm: true });
  markedReady = true;
}
function renderMarkdown(text) {
  setupMarked();
  if (typeof marked === 'undefined') return escapeHtml(text).replace(/\n/g, '<br>');
  const raw = marked.parse(text || '');
  return typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(raw) : raw;
}

// ── Message Rendering ─────────────────────────────────────────────
export function renderAllMessages() {
  const container = document.getElementById('messages-container');
  if (!container) return;

  const history = state.user
    ? (state.historial[state.currentSessionId] || [])
    : state.guestHistory;

  // ¡LA MAGIA ESTÁ ACÁ! Limpiamos el contenedor visual SIEMPRE,
  // antes de decidir si mostramos el inicio o cargamos mensajes.
  container.innerHTML = '';

  if (history.length === 0) {
    showHero(true);
    showExportBar(false);
    return;
  }

  showHero(false);

  // Filtramos mensajes de usuario duplicados visualmente (el bug de sincronización)
  const cleanHistory = history.filter((msg, index, arr) => {
    if (index === 0) return true;
    const prev = arr[index - 1];
    return !(msg.role === 'user' && prev.role === 'user' && msg.content === prev.content);
  });

  cleanHistory.forEach(msg => appendMessageToDOM(msg, container));

  showExportBar(true);
  scrollToBottom();
}

function appendMessageToDOM(msg, container = null) {
  if (!container) container = document.getElementById('messages-container');
  if (!container) return;

  const el = document.createElement('div');
  el.className = `message message--${msg.role === 'user' ? 'user' : 'ai'}`;

  if (msg.role === 'user') {
    el.innerHTML = buildUserBubble(msg.content);
  } else {
    el.innerHTML = buildAIBubble(msg.content);
  }

  container.appendChild(el);
}

function buildUserBubble(content) {
  let display = content;
  let fileChip = '';

  // Extract and hide the document block
  if (content.includes('--- DOCUMENTO ADJUNTO PARA ANALIZAR ---')) {
    display = content.split('--- DOCUMENTO ADJUNTO PARA ANALIZAR ---')[0].trim();
    fileChip = `<div class="file-chip">
      <span class="file-chip__icon">📎</span>
      <span class="file-chip__name">Documento analizado por la IA</span>
    </div>`;
  }

  return `<div class="message-bubble">${fileChip}<div>${escapeHtml(display).replace(/\n/g,'<br>')}</div></div>`;
}

function buildAIBubble(content) {
  return `<div class="message-bubble">
    <div class="message-avatar">IA</div>
    <div class="message-content">${renderMarkdown(content)}</div>
  </div>`;
}

// ── Send Message ──────────────────────────────────────────────────
export async function sendMessage() {
  if (state.isLoading) return;

  const textarea = document.getElementById('chat-textarea');
  let text = textarea ? textarea.value.trim() : '';

  // Compose the full message content
  let messageContent = '';
  const parts = [];

  if (state.pendingFile) {
    const { name } = state.pendingFile;
    parts.push(`📄 **Archivo adjunto:** ${name}`);
  }

  if (state.pendingAudio) {
    parts.push(`🎙️ **Mensaje de Voz:** ${state.pendingAudio}`);
  }

  if (text) parts.push(text);

  if (parts.length === 0) return;

  messageContent = parts.join('\n\n');

  // Append hidden document block
  if (state.pendingFile?.text) {
    messageContent += `\n\n--- DOCUMENTO ADJUNTO PARA ANALIZAR ---\n${state.pendingFile.text}`;
  }

  // Clear input
  if (textarea) { textarea.value = ''; textarea.style.height = 'auto'; }
  clearPendingFile();
  clearPendingAudio();
  updateSendBtn();

  // Ensure messages visible
  showHero(false);

  // Append user message immediately
  const userMsg = { role: 'user', content: messageContent };
  if (state.user) {
    const current = state.historial[state.currentSessionId] || [];
    current.push(userMsg);
    state.historial[state.currentSessionId] = current;
  } else {
    state.guestHistory.push(userMsg);
  }

  appendMessageToDOM(userMsg);
  showExportBar(true);
  showTypingIndicator();
  scrollToBottom();

  setState({ isLoading: true });
  updateSendBtn();

  try {
    let response;

    if (state.user) {
      // Authenticated send
      const history = state.historial[state.currentSessionId] || [];
      response = await apiChat(history, state.currentSessionId);

      const aiMsg = { role: 'assistant', content: response.respuesta };

      // Update historial from server response
      if (response.historial) {
        setState({ historial: response.historial });
        if (response.nuevo_titulo) {
          setState({ currentSessionId: response.nuevo_titulo });
        }
        renderHistoryList();
      } else {
        const current = state.historial[state.currentSessionId] || [];
        current.push(aiMsg);
        state.historial[state.currentSessionId] = current;
      }

      hideTypingIndicator();
      appendMessageToDOM({ role: 'assistant', content: response.respuesta });

    } else {
      // Guest send
      response = await apiChatGuest(state.guestHistory);
      const aiMsg = { role: 'assistant', content: response.respuesta };
      state.guestHistory.push(aiMsg);
      incrementGuestCount();

      hideTypingIndicator();
      appendMessageToDOM(aiMsg);

      // Update guest counter in sidebar
      import('./ui.js').then(({ renderSidebar }) => renderSidebar());

      // Check limit
      if (state.guestCount >= 5) {
        showAccessWall('guest-limit');
        // Bind register button
        setTimeout(() => {
          document.getElementById('wall-btn-register')?.addEventListener('click', () => {
            import('./ui.js').then(({ showModal }) => showModal('register'));
          });
        }, 50);
      }
    }

    showExportBar(true);
    scrollToBottom();

  } catch (err) {
    hideTypingIndicator();
    const errMsg = err.message || 'Error al conectar con el servidor.';

    if (err.message?.includes('402') || err.message?.includes('finalizado')) {
      showAccessWall('expired');
    } else {
      const errEl = document.createElement('div');
      errEl.className = 'message message--ai';
      errEl.innerHTML = `<div class="message-bubble">
        <div class="message-avatar">IA</div>
        <div class="message-content" style="color:var(--red-text)">
          Error: ${escapeHtml(errMsg)}
        </div>
      </div>`;
      document.getElementById('messages-container')?.appendChild(errEl);
    }
    scrollToBottom();
  } finally {
    setState({ isLoading: false });
    updateSendBtn();
  }
}

// ── File Upload ───────────────────────────────────────────────────
export async function handleFileSelect(file) {
  if (!file) return;

  const allowed = ['.pdf', '.txt'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast('Solo se permiten archivos PDF y TXT.', 'error');
    return;
  }

  showToast('Procesando documento...', 'info');

  try {
    const result = await apiUploadDocument(file);
    const sizeKb = (file.size / 1024).toFixed(1);

    setState({
      pendingFile: {
        name: file.name,
        text: result.texto,
        sizeKb,
      }
    });

    // Show preview card
    const preview = document.getElementById('file-preview');
    const nameEl = document.getElementById('preview-file-name');
    const metaEl = document.getElementById('preview-file-meta');
    if (preview) preview.classList.remove('hidden');
    if (nameEl) nameEl.textContent = file.name;
    if (metaEl) metaEl.textContent = `${sizeKb} KB · Listo para analizar ✓`;

    showToast('Documento cargado correctamente.', 'success');
    updateSendBtn();
  } catch (err) {
    showToast(err.message || 'Error al procesar el archivo.', 'error');
  }
}

export function clearPendingFile() {
  setState({ pendingFile: null });
  const preview = document.getElementById('file-preview');
  if (preview) preview.classList.add('hidden');
  // Reset hidden file input
  const inp = document.getElementById('hidden-file-input');
  if (inp) inp.value = '';
}

// ── Audio Recording ───────────────────────────────────────────────
let mediaRecorder = null;
let audioChunks = [];

export async function toggleRecording() {
  if (!state.isRecording) {
    await startRecording();
  } else {
    stopRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];

    // Prefer webm, fallback to ogg, then mp4
    const mimeType = ['audio/webm', 'audio/ogg', 'audio/mp4']
      .find(t => MediaRecorder.isTypeSupported(t)) || '';

    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(audioChunks, { type: mimeType || 'audio/webm' });
      await processAudioBlob(blob);
    };

    mediaRecorder.start();
    setState({ isRecording: true });
    setRecordingUI(true);
    showToast('Grabando... Hacé clic de nuevo para detener.', 'info');
  } catch (err) {
    showToast('No se pudo acceder al micrófono.', 'error');
    console.error(err);
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  setState({ isRecording: false });
  setRecordingUI(false);
}

async function processAudioBlob(blob) {
  showToast('Transcribiendo audio...', 'info');
  try {
    const result = await apiUploadAudio(blob);
    const transcription = result.transcripcion;

    setState({ pendingAudio: transcription });

    // Put transcription into textarea
    const ta = document.getElementById('chat-textarea');
    if (ta) {
      ta.value = transcription;
      ta.dispatchEvent(new Event('input'));
    }

    showToast('Audio transcripto correctamente.', 'success');
    updateSendBtn();
  } catch (err) {
    showToast(err.message || 'Error en la transcripción.', 'error');
  }
}

export function clearPendingAudio() {
  setState({ pendingAudio: null });
}

// ── PDF Export ────────────────────────────────────────────────────
export async function exportToPDF() {
  const isGuest = !state.user;
  const history = isGuest
    ? state.guestHistory
    : (state.historial[state.currentSessionId] || []);

  if (history.length === 0) {
    showToast('No hay conversación para exportar.', 'error');
    return;
  }

  const titulo = isGuest ? 'Chat Invitado' : (state.currentSessionId || 'Conversación');

  showToast('Generando PDF...', 'info');

  try {
    const blob = await apiExportPDF(history, titulo, isGuest);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Reporte_ChubutIA_${titulo.replace(/\s+/g,'_').slice(0,40)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('PDF descargado.', 'success');
  } catch (err) {
    showToast(err.message || 'Error al generar el PDF.', 'error');
  }
}

// ── Session Management ────────────────────────────────────────────
export function switchSession(sessionId) {
  if (!state.historial[sessionId]) return;
  setState({ currentSessionId: sessionId });
  showAccessWall(null);
  const inputArea = document.getElementById('input-area');
  if (inputArea) inputArea.style.display = '';
  renderAllMessages();
  import('./ui.js').then(({ renderHistoryList }) => renderHistoryList());
}
