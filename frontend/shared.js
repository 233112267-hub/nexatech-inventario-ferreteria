// ============================================================
// FERRETERÍA — shared.js  (incluir en todas las páginas)
// ============================================================

const API = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://127.0.0.1:8000/api'
  : 'https://nexatech-inventario-ferreteria.onrender.com/api';

// ── Auth guard ───────────────────────────────────────────────
function checkAuth() {
  const token = localStorage.getItem('token');
  if (!token) { window.location.href = 'login.html'; return null; }
  enforceRoleAccess();
  applyNavRoleVisibility();
  startAlertPolling();
  initChatbotWidget();
  return token;
}

// ── Campanita de alertas: mismo número en TODAS las pantallas ──
// Antes cada página traía su propio número (o de plano nunca lo
// actualizaba, se quedaba en el "0" fijo del HTML). Centralizado aquí:
// se llama solo, una vez al cargar cualquier página (vía checkAuth) y
// luego cada 25s, así que aunque no sea un WebSocket real, el número
// se refresca solo sin que el usuario tenga que recargar la página.
let _alertPollInterval = null;
async function refreshAlertBadge() {
  const data = await apiFetch('/dashboard/stats');
  if (!data || !data.ok) return;
  const n = data.data.alertasPendientes ?? 0;
  const badge = document.getElementById('alertBadge');
  const dot = document.getElementById('alertDot');
  if (badge) badge.textContent = n;
  if (dot) dot.textContent = n;
}
function startAlertPolling() {
  refreshAlertBadge();
  if (_alertPollInterval) clearInterval(_alertPollInterval);
  _alertPollInterval = setInterval(refreshAlertBadge, 25000);
}

// ── Control de acceso por rol (páginas completas) ────────────
// Estas páginas son exclusivas de Administrador. Si el rol actual
// no es Administrador, se redirige antes de que la página cargue
// ningún dato (protección de UI; el backend sigue siendo la
// verdadera barrera, esto solo evita exponer la pantalla).
const PAGINAS_SOLO_ADMIN = ['usuarios.html', 'reportes.html', 'alertas.html'];

function enforceRoleAccess() {
  const rol = localStorage.getItem('rol');
  const pagina = window.location.pathname.split('/').pop();
  if (PAGINAS_SOLO_ADMIN.includes(pagina) && rol !== 'Administrador') {
    window.location.href = 'dashboard.html';
  }
}

// ── Ocultar enlaces/accesos rápidos a secciones restringidas ─
function applyNavRoleVisibility() {
  const rol = localStorage.getItem('rol');
  if (rol === 'Administrador') return; // ve todo el menú
  PAGINAS_SOLO_ADMIN.forEach(pagina => {
    document.querySelectorAll(`a[href="${pagina}"]`).forEach(el => el.style.display = 'none');
  });
}

// ── Fetch autenticado ────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('token');
  // Django exige que la URL termine en "/" y con POST/PUT/DELETE no puede
  // redirigir agregándolo (pierde el body). Normalizamos aquí una sola vez
  // para no tener que acordarnos del slash en cada llamada del frontend.
  const [path, query] = endpoint.split('?');
  const normalizedPath = path.endsWith('/') ? path : path + '/';
  const finalEndpoint = query ? `${normalizedPath}?${query}` : normalizedPath;
  try {
    const res = await fetch(API + finalEndpoint, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...(options.headers || {})
      }
    });
    if (res.status === 401) {
      localStorage.clear();
      window.location.href = 'login.html';
      return null;
    }
    return await res.json();
  } catch (e) {
    showToast('Error de conexión con el servidor', 'error');
    return null;
  }
}

// ── Cerrar sesión ────────────────────────────────────────────
function setupLogout() {
  const btn = document.querySelector('.btn-logout');
  if (btn) {
    btn.addEventListener('click', e => {
      e.preventDefault();
      localStorage.clear();
      window.location.href = 'login.html';
    });
  }
}

// ── Toast global ─────────────────────────────────────────────
function showToast(msg, type = 'success') {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.className = 'toast';
    document.body.appendChild(t);
  }
  t.textContent = (type === 'success' ? '✓ ' : '⚠ ') + msg;
  t.className = `toast ${type} show`;
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ── Modal helpers ────────────────────────────────────────────
function openModal(id) { document.getElementById(id).classList.add('show'); }
function closeModal(id) { document.getElementById(id).classList.remove('show'); }

// ── Nombre del usuario en sesión ─────────────────────────────
function renderUserInfo() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  document.querySelectorAll('.user-name-display').forEach(el => {
    el.textContent = user.nombre || user.usuario || 'Admin';
  });
  document.querySelectorAll('.user-role-display').forEach(el => {
    el.textContent = user.rol || 'Administrador';
  });
  document.querySelectorAll('.avatar').forEach(el => {
    const n = user.nombre || 'AD';
    el.textContent = n.split(' ').map(w => w[0]).slice(0,2).join('').toUpperCase();
  });
}

// ── Chatbot flotante (Gemini) ──────────────────────────────────
let _chatHistory = []; // [{rol:'user'|'model', texto:'...'}, ...]
let _chatIniciado = false;

function initChatbotWidget() {
  if (document.getElementById('chatbotBubble')) return; // ya inyectado

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const rol = localStorage.getItem('rol') || user.rol || 'Vendedor';

  const bubble = document.createElement('button');
  bubble.id = 'chatbotBubble';
  bubble.className = 'chatbot-bubble';
  bubble.setAttribute('aria-label', 'Abrir asistente');
  bubble.innerHTML = `
    <span class="chatbot-dot"></span>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
    </svg>`;

  const panel = document.createElement('div');
  panel.id = 'chatbotPanel';
  panel.className = 'chatbot-panel';
  panel.innerHTML = `
    <div class="chatbot-header">
      <div class="chatbot-header-info">
        <strong>Asistente NexaFerretería</strong>
        <span class="chatbot-role-badge">${rol}</span>
      </div>
      <button class="chatbot-close" aria-label="Cerrar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <div class="chatbot-messages" id="chatbotMessages"></div>
    <div class="chatbot-input-row">
      <input type="text" id="chatbotInput" placeholder="Escribe tu pregunta..." maxlength="500" />
      <button id="chatbotSend" aria-label="Enviar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </div>`;

  document.body.appendChild(bubble);
  document.body.appendChild(panel);

  bubble.addEventListener('click', toggleChatbot);
  panel.querySelector('.chatbot-close').addEventListener('click', toggleChatbot);
  panel.querySelector('#chatbotSend').addEventListener('click', sendChatbotMessage);
  panel.querySelector('#chatbotInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') sendChatbotMessage();
  });
}

function toggleChatbot() {
  const panel = document.getElementById('chatbotPanel');
  panel.classList.toggle('open');
  if (panel.classList.contains('open')) {
    document.getElementById('chatbotInput').focus();
    if (!_chatIniciado) {
      _chatIniciado = true;
      const rol = localStorage.getItem('rol') || 'Vendedor';
      addChatMessage(
        rol === 'Administrador'
          ? '¡Hola! Estás conectado como Administrador. Puedo ayudarte con inventario, ventas, reportes o usuarios. ¿Qué necesitas?'
          : '¡Hola! Estás conectado como Vendedor. Puedo ayudarte a consultar stock, ventas y movimientos. ¿Qué necesitas?',
        'bot'
      );
    }
  }
}

function addChatMessage(texto, tipo) {
  const cont = document.getElementById('chatbotMessages');
  const div = document.createElement('div');
  div.className = `chatbot-msg ${tipo}`;
  div.textContent = texto;
  cont.appendChild(div);
  cont.scrollTop = cont.scrollHeight;
  return div;
}

async function sendChatbotMessage() {
  const input = document.getElementById('chatbotInput');
  const btn = document.getElementById('chatbotSend');
  const mensaje = input.value.trim();
  if (!mensaje) return;

  addChatMessage(mensaje, 'user');
  input.value = '';
  input.disabled = true;
  btn.disabled = true;

  const typingEl = addChatMessage('Escribiendo...', 'bot typing');

  const data = await apiFetch('/chatbot', {
    method: 'POST',
    body: JSON.stringify({ mensaje, historial: _chatHistory })
  });

  typingEl.remove();
  input.disabled = false;
  btn.disabled = false;
  input.focus();

  if (!data || !data.ok && !data.respuesta) {
    addChatMessage('No pude conectar con el asistente. Intenta de nuevo.', 'bot');
    return;
  }

  const respuesta = data.respuesta || 'No obtuve respuesta, intenta de nuevo.';
  addChatMessage(respuesta, 'bot');

  _chatHistory.push({ rol: 'user', texto: mensaje });
  _chatHistory.push({ rol: 'model', texto: respuesta });
  if (_chatHistory.length > 12) _chatHistory = _chatHistory.slice(-12); // limita contexto
}

// ── Paginación helper ─────────────────────────────────────────
function renderPagination(containerId, infId, currentPage, total, perPage, onPageChange) {
  const totalPages = Math.ceil(total / perPage);
  const info = document.getElementById(infId);
  const container = document.getElementById(containerId);
  if (info) {
    const start = (currentPage - 1) * perPage + 1;
    const end = Math.min(currentPage * perPage, total);
    info.textContent = `Mostrando ${start}–${end} de ${total}`;
  }
  if (!container) return;
  let html = `<button class="page-btn" onclick="(${onPageChange})(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg></button>`;
  for (let i = 1; i <= totalPages; i++) {
    if (totalPages <= 5 || Math.abs(i - currentPage) <= 1 || i === 1 || i === totalPages) {
      html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="(${onPageChange})(${i})">${i}</button>`;
    } else if (i === 2 || i === totalPages - 1) {
      html += `<button class="page-btn" disabled>…</button>`;
    }
  }
  html += `<button class="page-btn" onclick="(${onPageChange})(${currentPage + 1})" ${currentPage === totalPages || totalPages === 0 ? 'disabled' : ''}>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg></button>`;
  container.innerHTML = html;
}