const bcrypt = require('bcryptjs');
const db = require('../config/database');

const COLS = `id, nombre, usuario, correo, rol, estado, created_at, updated_at`;

/** GET /api/usuarios */
const getAll = (req, res) => {
  const { search, rol, estado, page = 1, limit = 10 } = req.query;
  const offset = (page - 1) * limit;
  let where = [];
  let params = [];

  if (search) {
    where.push(`(nombre LIKE ? OR usuario LIKE ? OR correo LIKE ?)`);
    const q = `%${search}%`;
    params.push(q, q, q);
  }
  if (rol)    { where.push(`rol = ?`);    params.push(rol); }
  if (estado) { where.push(`estado = ?`); params.push(estado); }

  const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';

  db.get(`SELECT COUNT(*) as total FROM usuarios ${whereSQL}`, params, (err, count) => {
    if (err) return res.status(500).json({ ok: false, message: err.message });
    db.all(
      `SELECT ${COLS} FROM usuarios ${whereSQL} ORDER BY id DESC LIMIT ? OFFSET ?`,
      [...params, +limit, +offset],
      (err2, rows) => {
        if (err2) return res.status(500).json({ ok: false, message: err2.message });
        res.json({ ok: true, total: count.total, page: +page, limit: +limit, data: rows });
      }
    );
  });
};

/** GET /api/usuarios/:id */
const getOne = (req, res) => {
  db.get(`SELECT ${COLS} FROM usuarios WHERE id = ?`, [req.params.id], (err, row) => {
    if (err) return res.status(500).json({ ok: false, message: err.message });
    if (!row) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });
    res.json({ ok: true, data: row });
  });
};

/** POST /api/usuarios */
const create = async (req, res) => {
  const { nombre, usuario, correo, password, rol = 'Vendedor', estado = 'Activo' } = req.body;
  if (!nombre || !usuario || !correo || !password) {
    return res.status(400).json({ ok: false, message: 'Campos requeridos: nombre, usuario, correo, password' });
  }

  const hash = await bcrypt.hash(password, 10);
  db.run(
    `INSERT INTO usuarios(nombre,usuario,correo,password,rol,estado) VALUES(?,?,?,?,?,?)`,
    [nombre, usuario, correo, hash, rol, estado],
    function (err) {
      if (err) {
        if (err.message.includes('UNIQUE')) {
          return res.status(409).json({ ok: false, message: 'El usuario o correo ya existe' });
        }
        return res.status(500).json({ ok: false, message: err.message });
      }
      res.status(201).json({ ok: true, message: 'Usuario creado', id: this.lastID });
    }
  );
};

/** PUT /api/usuarios/:id */
const update = async (req, res) => {
  const { nombre, usuario, correo, password, rol, estado } = req.body;
  const { id } = req.params;

  db.get(`SELECT * FROM usuarios WHERE id = ?`, [id], async (err, row) => {
    if (err) return res.status(500).json({ ok: false, message: err.message });
    if (!row) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });

    const newHash = password ? await bcrypt.hash(password, 10) : row.password;
    db.run(
      `UPDATE usuarios SET nombre=?,usuario=?,correo=?,password=?,rol=?,estado=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`,
      [nombre||row.nombre, usuario||row.usuario, correo||row.correo, newHash, rol||row.rol, estado||row.estado, id],
      function (e) {
        if (e) {
          if (e.message.includes('UNIQUE')) return res.status(409).json({ ok: false, message: 'El usuario o correo ya existe' });
          return res.status(500).json({ ok: false, message: e.message });
        }
        res.json({ ok: true, message: 'Usuario actualizado' });
      }
    );
  });
};

/** DELETE /api/usuarios/:id */
const remove = (req, res) => {
  if (+req.params.id === req.user.id) {
    return res.status(400).json({ ok: false, message: 'No puedes eliminar tu propia cuenta' });
  }
  db.run(`DELETE FROM usuarios WHERE id = ?`, [req.params.id], function (err) {
    if (err) return res.status(500).json({ ok: false, message: err.message });
    if (this.changes === 0) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });
    res.json({ ok: true, message: 'Usuario eliminado' });
  });
};

module.exports = { getAll, getOne, create, update, remove };
