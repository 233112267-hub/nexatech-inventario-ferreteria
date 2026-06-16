const db = require('../config/database');

const COLS = `p.id, p.codigo, p.nombre, p.descripcion, p.precio, p.stock, p.stock_minimo, p.estado,
              p.created_at, p.updated_at, c.id as categoria_id, c.nombre as categoria`;

/** GET /api/productos */
const getAll = (req, res) => {
  const { search, categoria, estado, page = 1, limit = 10 } = req.query;
  const offset = (page - 1) * limit;
  let where = []; let params = [];

  if (search) {
    where.push(`(p.nombre LIKE ? OR p.codigo LIKE ?)`);
    const q = `%${search}%`; params.push(q, q);
  }
  if (categoria) { where.push(`c.nombre = ?`);  params.push(categoria); }
  if (estado)    { where.push(`p.estado = ?`);   params.push(estado); }

  const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';
  const join = `FROM productos p LEFT JOIN categorias c ON p.categoria_id = c.id`;

  db.get(`SELECT COUNT(*) as total ${join} ${whereSQL}`, params, (err, count) => {
    if (err) return res.status(500).json({ ok: false, message: err.message });
    db.all(
      `SELECT ${COLS} ${join} ${whereSQL} ORDER BY p.id DESC LIMIT ? OFFSET ?`,
      [...params, +limit, +offset],
      (err2, rows) => {
        if (err2) return res.status(500).json({ ok: false, message: err2.message });
        res.json({ ok: true, total: count.total, page: +page, limit: +limit, data: rows });
      }
    );
  });
};

/** GET /api/productos/:id */
const getOne = (req, res) => {
  db.get(
    `SELECT ${COLS} FROM productos p LEFT JOIN categorias c ON p.categoria_id = c.id WHERE p.id = ?`,
    [req.params.id],
    (err, row) => {
      if (err) return res.status(500).json({ ok: false, message: err.message });
      if (!row) return res.status(404).json({ ok: false, message: 'Producto no encontrado' });
      res.json({ ok: true, data: row });
    }
  );
};

/** POST /api/productos */
const create = (req, res) => {
  const { codigo, nombre, descripcion, categoria_id, precio, stock = 0, stock_minimo = 0, estado = 'Activo' } = req.body;
  if (!codigo || !nombre || precio == null) {
    return res.status(400).json({ ok: false, message: 'Campos requeridos: codigo, nombre, precio' });
  }
  db.run(
    `INSERT INTO productos(codigo,nombre,descripcion,categoria_id,precio,stock,stock_minimo,estado) VALUES(?,?,?,?,?,?,?,?)`,
    [codigo, nombre, descripcion, categoria_id, precio, stock, stock_minimo, estado],
    function (err) {
      if (err) {
        if (err.message.includes('UNIQUE')) return res.status(409).json({ ok: false, message: 'El código ya existe' });
        return res.status(500).json({ ok: false, message: err.message });
      }
      res.status(201).json({ ok: true, message: 'Producto creado', id: this.lastID });
    }
  );
};

/** PUT /api/productos/:id */
const update = (req, res) => {
  const { id } = req.params;
  const { codigo, nombre, descripcion, categoria_id, precio, stock, stock_minimo, estado } = req.body;

  db.get(`SELECT * FROM productos WHERE id = ?`, [id], (err, row) => {
    if (err) return res.status(500).json({ ok: false, message: err.message });
    if (!row) return res.status(404).json({ ok: false, message: 'Producto no encontrado' });

    db.run(
      `UPDATE productos SET codigo=?,nombre=?,descripcion=?,categoria_id=?,precio=?,stock=?,stock_minimo=?,estado=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`,
      [codigo??row.codigo, nombre??row.nombre, descripcion??row.descripcion,
       categoria_id??row.categoria_id, precio??row.precio, stock??row.stock,
       stock_minimo??row.stock_minimo, estado??row.estado, id],
      function (e) {
        if (e) return res.status(500).json({ ok: false, message: e.message });
        res.json({ ok: true, message: 'Producto actualizado' });
      }
    );
  });
};

/** DELETE /api/productos/:id */
const remove = (req, res) => {
  db.run(`DELETE FROM productos WHERE id = ?`, [req.params.id], function (err) {
    if (err) return res.status(500).json({ ok: false, message: err.message });
    if (this.changes === 0) return res.status(404).json({ ok: false, message: 'Producto no encontrado' });
    res.json({ ok: true, message: 'Producto eliminado' });
  });
};

/** GET /api/productos/stock-bajo  — productos con stock <= stock_minimo */
const stockBajo = (req, res) => {
  db.all(
    `SELECT ${COLS} FROM productos p LEFT JOIN categorias c ON p.categoria_id = c.id
     WHERE p.stock <= p.stock_minimo AND p.estado = 'Activo' ORDER BY p.stock ASC`,
    [],
    (err, rows) => {
      if (err) return res.status(500).json({ ok: false, message: err.message });
      res.json({ ok: true, total: rows.length, data: rows });
    }
  );
};

module.exports = { getAll, getOne, create, update, remove, stockBajo };
