const bcrypt = require('bcryptjs');
const { query } = require('../config/database');

const COLS = `u.id_usuario AS id, u.nombre, u.username AS usuario, u.email AS correo,
              r.nombre AS rol, u.activo,
              CASE WHEN u.activo THEN 'Activo' ELSE 'Inactivo' END AS estado,
              u.created_at, u.updated_at`;
const JOIN = `FROM USUARIOS u JOIN ROLES r ON u.id_rol = r.id_rol`;

/** GET /api/usuarios */
const getAll = async (req, res) => {
  try {
    const { search, rol, estado, page = 1, limit = 10 } = req.query;
    const offset = (page - 1) * limit;
    let where = [];
    let params = [];

    if (search) {
      params.push(`%${search}%`);
      where.push(`(u.nombre ILIKE $${params.length} OR u.username ILIKE $${params.length} OR u.email ILIKE $${params.length})`);
    }
    if (rol) { params.push(rol); where.push(`r.nombre = $${params.length}`); }
    if (estado) { params.push(estado === 'Activo'); where.push(`u.activo = $${params.length}`); }

    const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';

    const { rows: countRows } = await query(`SELECT COUNT(*)::int AS total ${JOIN} ${whereSQL}`, params);

    params.push(+limit, +offset);
    const { rows } = await query(
      `SELECT ${COLS} ${JOIN} ${whereSQL} ORDER BY u.id_usuario DESC LIMIT $${params.length - 1} OFFSET $${params.length}`,
      params
    );

    res.json({ ok: true, total: countRows[0].total, page: +page, limit: +limit, data: rows });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** GET /api/usuarios/:id */
const getOne = async (req, res) => {
  try {
    const { rows } = await query(`SELECT ${COLS} ${JOIN} WHERE u.id_usuario = $1`, [req.params.id]);
    if (!rows[0]) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });
    res.json({ ok: true, data: rows[0] });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** POST /api/usuarios */
const create = async (req, res) => {
  const { nombre, usuario, correo, password, rol = 'Vendedor', estado = 'Activo' } = req.body;
  if (!nombre || !usuario || !correo || !password) {
    return res.status(400).json({ ok: false, message: 'Campos requeridos: nombre, usuario, correo, password' });
  }

  try {
    const { rows: rolRows } = await query('SELECT id_rol FROM ROLES WHERE nombre = $1', [rol]);
    if (!rolRows[0]) return res.status(400).json({ ok: false, message: `Rol inválido: ${rol}` });

    const hash = await bcrypt.hash(password, 10);
    const { rows } = await query(
      `INSERT INTO USUARIOS (nombre, username, email, password_hash, id_rol, activo)
       VALUES ($1,$2,$3,$4,$5,$6) RETURNING id_usuario`,
      [nombre, usuario, correo, hash, rolRows[0].id_rol, estado === 'Activo']
    );
    res.status(201).json({ ok: true, message: 'Usuario creado', id: rows[0].id_usuario });
  } catch (err) {
    if (err.code === '23505') return res.status(409).json({ ok: false, message: 'El usuario o correo ya existe' });
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** PUT /api/usuarios/:id */
const update = async (req, res) => {
  const { nombre, usuario, correo, password, rol, estado } = req.body;
  const { id } = req.params;

  try {
    const { rows: existing } = await query('SELECT * FROM USUARIOS WHERE id_usuario = $1', [id]);
    const row = existing[0];
    if (!row) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });

    let id_rol = row.id_rol;
    if (rol) {
      const { rows: rolRows } = await query('SELECT id_rol FROM ROLES WHERE nombre = $1', [rol]);
      if (!rolRows[0]) return res.status(400).json({ ok: false, message: `Rol inválido: ${rol}` });
      id_rol = rolRows[0].id_rol;
    }

    const newHash = password ? await bcrypt.hash(password, 10) : row.password_hash;
    const activo = estado != null ? estado === 'Activo' : row.activo;

    await query(
      `UPDATE USUARIOS SET nombre=$1, username=$2, email=$3, password_hash=$4, id_rol=$5, activo=$6, updated_at=CURRENT_TIMESTAMP
       WHERE id_usuario=$7`,
      [nombre || row.nombre, usuario || row.username, correo || row.email, newHash, id_rol, activo, id]
    );
    res.json({ ok: true, message: 'Usuario actualizado' });
  } catch (err) {
    if (err.code === '23505') return res.status(409).json({ ok: false, message: 'El usuario o correo ya existe' });
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** DELETE /api/usuarios/:id */
const remove = async (req, res) => {
  if (+req.params.id === req.user.id) {
    return res.status(400).json({ ok: false, message: 'No puedes eliminar tu propia cuenta' });
  }
  try {
    const { rowCount } = await query('DELETE FROM USUARIOS WHERE id_usuario = $1', [req.params.id]);
    if (rowCount === 0) return res.status(404).json({ ok: false, message: 'Usuario no encontrado' });
    res.json({ ok: true, message: 'Usuario eliminado' });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

module.exports = { getAll, getOne, create, update, remove };
