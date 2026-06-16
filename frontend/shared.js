// ============================================================
// FERRETERÍA — shared.js  (incluir en todas las páginas)
// ============================================================

const API = 'http://localhost:3000/api';

// ── Auth guard ───────────────────────────────────────────────
function checkAuth() {
  const token = localStorage.getItem('token');
  if (!token) { window.location.href = 'login.html'; return null; }
  return token;
}

// ── Fetch autenticado ────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API + endpoint, {
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
