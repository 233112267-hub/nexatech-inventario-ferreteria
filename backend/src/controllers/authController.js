const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const db = require('../config/database');

/**
 * POST /api/auth/login
 * Body: { usuario, password }
 */
const login = (req, res) => {
  const { usuario, password } = req.body;
  if (!usuario || !password) {
    return res.status(400).json({ ok: false, message: 'Usuario y contraseña son requeridos' });
  }

  db.get(
    `SELECT * FROM usuarios WHERE (usuario = ? OR correo = ?) AND estado = 'Activo'`,
    [usuario, usuario],
    async (err, user) => {
      if (err) return res.status(500).json({ ok: false, message: 'Error interno' });
      if (!user) return res.status(401).json({ ok: false, message: 'Credenciales incorrectas' });

      const valid = await bcrypt.compare(password, user.password);
      if (!valid) return res.status(401).json({ ok: false, message: 'Credenciales incorrectas' });

      const token = jwt.sign(
        { id: user.id, usuario: user.usuario, rol: user.rol },
        process.env.JWT_SECRET,
        { expiresIn: process.env.JWT_EXPIRES_IN || '8h' }
      );

      res.json({
        ok: true,
        message: 'Login exitoso',
        token,
        user: {
          id: user.id,
          nombre: user.nombre,
          usuario: user.usuario,
          correo: user.correo,
          rol: user.rol,
        },
      });
    }
  );
};

/**
 * GET /api/auth/me  (requiere token)
 */
const me = (req, res) => {
  db.get(`SELECT id,nombre,usuario,correo,rol,estado,created_at FROM usuarios WHERE id = ?`,
    [req.user.id],
    (err, user) => {
      if (err || !user) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });
      res.json({ ok: true, user });
    }
  );
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

  db.get(`SELECT * FROM usuarios WHERE id = ?`, [req.user.id], async (err, user) => {
    if (err || !user) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });
    const valid = await bcrypt.compare(currentPassword, user.password);
    if (!valid) return res.status(401).json({ ok: false, message: 'Contraseña actual incorrecta' });

    const hash = await bcrypt.hash(newPassword, 10);
    db.run(`UPDATE usuarios SET password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
      [hash, req.user.id],
      (e) => {
        if (e) return res.status(500).json({ ok: false, message: 'Error al actualizar' });
        res.json({ ok: true, message: 'Contraseña actualizada correctamente' });
      }
    );
  });
};

module.exports = { login, me, changePassword };
