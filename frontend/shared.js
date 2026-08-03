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