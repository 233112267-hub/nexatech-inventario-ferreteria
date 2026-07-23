const nodemailer = require('nodemailer');
const { query } = require('../config/database');

// ══════════════════════════════════════════════
//  SERVICIO DE CORREO (API EXTERNA vía SMTP)
//  Se usa para notificar alertas críticas de stock
//  a los administradores del sistema.
// ══════════════════════════════════════════════

let transporter = null;

/**
 * Crea (una sola vez) el transporter de Nodemailer usando
 * las credenciales definidas en el .env
 */
function getTransporter() {
  if (transporter) return transporter;

  if (!process.env.EMAIL_USER || !process.env.EMAIL_PASS) {
    console.warn('⚠️  EMAIL_USER / EMAIL_PASS no configurados en .env — las notificaciones por correo están deshabilitadas.');
    return null;
  }

  transporter = nodemailer.createTransport({
    service: 'gmail', // Puedes cambiar a otro proveedor SMTP si lo prefieres
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_PASS, // Contraseña de aplicación de Gmail, NO tu contraseña normal
    },
  });

  return transporter;
}

/**
 * Obtiene los correos de los usuarios con rol Administrador (activos)
 */
async function getCorreosAdministradores() {
  const { rows } = await query(
    `SELECT u.email
     FROM USUARIOS u
     JOIN ROLES r ON u.id_rol = r.id_rol
     WHERE r.nombre = 'Administrador' AND u.activo = TRUE`
  );
  return rows.map(r => r.email).filter(Boolean);
}

/**
 * Envía un correo de alerta de stock.
 * @param {Object} alerta - { tipo, nombre, descripcion, producto_nombre, producto_codigo }
 */
async function enviarAlertaStock(alerta) {
  const t = getTransporter();
  if (!t) return { ok: false, message: 'Servicio de correo no configurado' };

  try {
    const destinatarios = await getCorreosAdministradores();
    if (destinatarios.length === 0) {
      console.warn('⚠️  No hay administradores con correo registrado para notificar.');
      return { ok: false, message: 'No hay destinatarios' };
    }

    const esCritica = alerta.tipo === 'Critica';
    const colorBadge = esCritica ? '#dc2626' : '#f5a623';
    const bgBadge = esCritica ? '#fee2e2' : '#fef3c7';

    const descCorta = alerta.descripcion || '';

    const info = await t.sendMail({
      from: `"Sistema Ferretería" <${process.env.EMAIL_USER}>`,
      to: destinatarios.join(','),
      subject: `${esCritica ? '🔴' : '🟡'} [${alerta.tipo}] ${alerta.nombre} — Sistema Ferretería`,
      html: `
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 460px; margin: 0 auto; background:#f1f5f9; padding: 24px;">
          <div style="background:#1a2340; padding:20px 24px; border-radius:10px 10px 0 0; display:flex; align-items:center; gap:12px;">
            <div style="width:36px; height:36px; background:#f5a623; border-radius:8px; display:inline-flex; align-items:center; justify-content:center; font-size:18px;">⚙️</div>
            <div>
              <div style="color:#fff; font-weight:700; font-size:15px; letter-spacing:.3px;">FERRETERÍA</div>
              <div style="color:#9aa5c4; font-size:10px; letter-spacing:.5px;">INVENTARIO Y VENTAS</div>
            </div>
          </div>
          <div style="background:#fff; border:1px solid #e2e8f0; border-top:none; padding:22px 24px; border-radius:0 0 10px 10px;">
            <span style="display:inline-block; background:${bgBadge}; color:${colorBadge}; padding:3px 12px; border-radius:20px; font-size:11px; font-weight:700; letter-spacing:.3px;">
              ${alerta.tipo.toUpperCase()}
            </span>
            <h2 style="margin:10px 0 6px; color:#1e293b; font-size:18px;">${alerta.nombre}</h2>
            <p style="color:#475569; font-size:14px; margin:0 0 14px; line-height:1.4;">${descCorta}</p>
            ${alerta.producto_nombre ? `
            <div style="background:#f8fafc; border-radius:8px; padding:10px 14px; font-size:13px; color:#334155;">
              <strong>${alerta.producto_nombre}</strong>${alerta.producto_codigo ? ` · ${alerta.producto_codigo}` : ''}
            </div>` : ''}
            <p style="color:#94a3b8; font-size:11px; margin-top:18px; margin-bottom:0;">Panel de Alertas · Sistema Ferretería</p>
          </div>
        </div>
      `,
    });

    console.log('📧 Correo de alerta enviado:', info.messageId);
    return { ok: true, messageId: info.messageId, destinatarios };
  } catch (err) {
    console.error('❌ Error al enviar correo de alerta:', err.message);
    return { ok: false, message: err.message };
  }
}

module.exports = { enviarAlertaStock, getCorreosAdministradores };