const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { query } = require('../config/database');

/**
 * POST /api/auth/login
 * Body: { usuario, password }   (usuario = username o email)
 */
const login = async (req, res) => {
  const { usuario, password } = req.body;
  if (!usuario || !password) {
    return res.status(400).json({ ok: false, message: 'Usuario y contraseña son requeridos' });
  }

  try {
    const { rows } = await query(
      `SELECT u.id_usuario, u.nombre, u.username, u.email, u.password_hash, u.activo,
              r.id_rol, r.nombre AS rol
       FROM USUARIOS u
       JOIN ROLES r ON u.id_rol = r.id_rol
       WHERE (u.username = $1 OR u.email = $1) AND u.activo = TRUE`,
      [usuario]
    );
    const user = rows[0];
    if (!user) return res.status(401).json({ ok: false, message: 'Credenciales incorrectas' });

    const valid = await bcrypt.compare(password, user.password_hash);
    if (!valid) return res.status(401).json({ ok: false, message: 'Credenciales incorrectas' });

    const token = jwt.sign(
      { id: user.id_usuario, usuario: user.username, rol: user.rol },
      process.env.JWT_SECRET,
      { expiresIn: process.env.JWT_EXPIRES_IN || '8h' }
    );

    res.json({
      ok: true,
      message: 'Login exitoso',
      token,
      user: {
        id: user.id_usuario,
        nombre: user.nombre,
        usuario: user.username,
        correo: user.email,
        rol: user.rol,
      },
    });
  } catch (err) {
    res.status(500).json({ ok: false, message: 'Error interno', detail: err.message });
  }
};

/**
 * GET /api/auth/me  (requiere token)
 */
const me = async (req, res) => {
  try {
    const { rows } = await query(
      `SELECT u.id_usuario AS id, u.nombre, u.username AS usuario, u.email AS correo,
              r.nombre AS rol, u.activo, u.created_at
       FROM USUARIOS u JOIN ROLES r ON u.id_rol = r.id_rol
       WHERE u.id_usuario = $1`,
      [req.user.id]
    );
    const user = rows[0];
    if (!user) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });
    res.json({ ok: true, user });
  } catch (err) {
    res.status(500).json({ ok: false, message: 'Error interno', detail: err.message });
  }
};

/**
 * POST /api/auth/change-password  (requiere token)
 * Body: { currentPassword, newPassword }
 */
const changePassword = async (req, res) => {
  const { currentPassword, newPassword } = req.body;
  if (!currentPassword || !newPassword) {
    return res.status(400).json({ ok: false, message: 'Campos requeridos' });
  }
  if (newPassword.length < 6) {
    return res.status(400).json({ ok: false, message: 'La nueva contraseña debe tener mínimo 6 caracteres' });
  }

  try {
    const { rows } = await query('SELECT * FROM USUARIOS WHERE id_usuario = $1', [req.user.id]);
    const user = rows[0];
    if (!user) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });

    const valid = await bcrypt.compare(currentPassword, user.password_hash);
    if (!valid) return res.status(401).json({ ok: false, message: 'Contraseña actual incorrecta' });

    const hash = await bcrypt.hash(newPassword, 10);
    await query(
      `UPDATE USUARIOS SET password_hash = $1, updated_at = CURRENT_TIMESTAMP WHERE id_usuario = $2`,
      [hash, req.user.id]
    );
    res.json({ ok: true, message: 'Contraseña actualizada correctamente' });
  } catch (err) {
    res.status(500).json({ ok: false, message: 'Error al actualizar', detail: err.message });
  }
};

module.exports = { login, me, changePassword };
