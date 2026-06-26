const { query } = require('../config/database');

const COLS = `p.id_producto AS id, p.codigo, p.nombre, p.descripcion,
              p.precio_venta AS precio, p.precio_compra,
              p.stock_actual AS stock, p.stock_minimo, p.estado,
              p.created_at, p.updated_at,
              c.id_categoria AS categoria_id, c.nombre AS categoria`;
const JOIN = `FROM PRODUCTOS p LEFT JOIN CATEGORIAS c ON p.id_categoria = c.id_categoria`;

/** GET /api/productos */
const getAll = async (req, res) => {
  try {
    const { search, categoria, estado, page = 1, limit = 10 } = req.query;
    const offset = (page - 1) * limit;
    let where = []; let params = [];

    if (search) {
      params.push(`%${search}%`);
      where.push(`(p.nombre ILIKE $${params.length} OR p.codigo ILIKE $${params.length})`);
    }
    if (categoria) { params.push(categoria); where.push(`c.nombre = $${params.length}`); }
    if (estado)    { params.push(estado);    where.push(`p.estado = $${params.length}`); }

    const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';

    const { rows: countRows } = await query(`SELECT COUNT(*)::int AS total ${JOIN} ${whereSQL}`, params);

    params.push(+limit, +offset);
    const { rows } = await query(
      `SELECT ${COLS} ${JOIN} ${whereSQL} ORDER BY p.id_producto DESC LIMIT $${params.length - 1} OFFSET $${params.length}`,
      params
    );

    res.json({ ok: true, total: countRows[0].total, page: +page, limit: +limit, data: rows });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** GET /api/productos/:id */
const getOne = async (req, res) => {
  try {
    const { rows } = await query(`SELECT ${COLS} ${JOIN} WHERE p.id_producto = $1`, [req.params.id]);
    if (!rows[0]) return res.status(404).json({ ok: false, message: 'Producto no encontrado' });
    res.json({ ok: true, data: rows[0] });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** POST /api/productos */
const create = async (req, res) => {
  const { codigo, nombre, descripcion, categoria_id, precio, stock = 0, stock_minimo = 0, estado = 'Activo', precio_compra = 0 } = req.body;
  if (!codigo || !nombre || precio == null) {
    return res.status(400).json({ ok: false, message: 'Campos requeridos: codigo, nombre, precio' });
  }
  try {
    const { rows } = await query(
      `INSERT INTO PRODUCTOS (codigo, nombre, descripcion, id_categoria, precio_compra, precio_venta, stock_actual, stock_minimo, estado)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id_producto`,
      [codigo, nombre, descripcion || null, categoria_id, precio_compra, precio, stock, stock_minimo, estado]
    );
    res.status(201).json({ ok: true, message: 'Producto creado', id: rows[0].id_producto });
  } catch (err) {
    if (err.code === '23505') return res.status(409).json({ ok: false, message: 'El código ya existe' });
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** PUT /api/productos/:id */
const update = async (req, res) => {
  const { id } = req.params;
  const { codigo, nombre, descripcion, categoria_id, precio, stock, stock_minimo, estado, precio_compra } = req.body;

  try {
    const { rows: existing } = await query('SELECT * FROM PRODUCTOS WHERE id_producto = $1', [id]);
    const row = existing[0];
    if (!row) return res.status(404).json({ ok: false, message: 'Producto no encontrado' });

    await query(
      `UPDATE PRODUCTOS SET codigo=$1, nombre=$2, descripcion=$3, id_categoria=$4, precio_compra=$5,
              precio_venta=$6, stock_actual=$7, stock_minimo=$8, estado=$9, updated_at=CURRENT_TIMESTAMP
       WHERE id_producto=$10`,
      [
        codigo ?? row.codigo,
        nombre ?? row.nombre,
        descripcion ?? row.descripcion,
        categoria_id ?? row.id_categoria,
        precio_compra ?? row.precio_compra,
        precio ?? row.precio_venta,
        stock ?? row.stock_actual,
        stock_minimo ?? row.stock_minimo,
        estado ?? row.estado,
        id,
      ]
    );
    res.json({ ok: true, message: 'Producto actualizado' });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** DELETE /api/productos/:id */
const remove = async (req, res) => {
  try {
    const { rowCount } = await query('DELETE FROM PRODUCTOS WHERE id_producto = $1', [req.params.id]);
    if (rowCount === 0) return res.status(404).json({ ok: false, message: 'Producto no encontrado' });
    res.json({ ok: true, message: 'Producto eliminado' });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** GET /api/productos/stock-bajo */
const stockBajo = async (req, res) => {
  try {
    const { rows } = await query(
      `SELECT ${COLS} ${JOIN}
       WHERE p.stock_actual <= p.stock_minimo AND p.estado = 'Activo'
       ORDER BY p.stock_actual ASC`
    );
    res.json({ ok: true, total: rows.length, data: rows });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

module.exports = { getAll, getOne, create, update, remove, stockBajo };
