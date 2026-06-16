const db = require('../config/database');

// ══════════════════════════════════════════════
//  MOVIMIENTOS
// ══════════════════════════════════════════════

const movimientos = {
  /** GET /api/movimientos */
  getAll(req, res) {
    const { search, tipo, page = 1, limit = 10 } = req.query;
    const offset = (page - 1) * limit;
    let where = []; let params = [];

    if (search) {
      where.push(`(p.nombre LIKE ? OR p.codigo LIKE ? OR m.referencia LIKE ?)`);
      const q = `%${search}%`; params.push(q, q, q);
    }
    if (tipo) { where.push(`m.tipo = ?`); params.push(tipo); }

    const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';

    db.get(`SELECT COUNT(*) as total FROM movimientos m
            LEFT JOIN productos p ON m.producto_id = p.id ${whereSQL}`, params,
      (err, count) => {
        if (err) return res.status(500).json({ ok: false, message: err.message });
        db.all(
          `SELECT m.*, p.nombre as producto_nombre, p.codigo as producto_codigo,
                  u.nombre as usuario_nombre
           FROM movimientos m
           LEFT JOIN productos p ON m.producto_id = p.id
           LEFT JOIN usuarios  u ON m.usuario_id = u.id
           ${whereSQL} ORDER BY m.id DESC LIMIT ? OFFSET ?`,
          [...params, +limit, +offset],
          (err2, rows) => {
            if (err2) return res.status(500).json({ ok: false, message: err2.message });
            res.json({ ok: true, total: count.total, page: +page, limit: +limit, data: rows });
          }
        );
      }
    );
  },

  /** POST /api/movimientos  — manual entry/exit/adjustment */
  create(req, res) {
    const { tipo, producto_id, cantidad, referencia } = req.body;
    if (!tipo || !producto_id || !cantidad) {
      return res.status(400).json({ ok: false, message: 'tipo, producto_id y cantidad son requeridos' });
    }

    db.get(`SELECT stock FROM productos WHERE id = ?`, [producto_id], (err, prod) => {
      if (err || !prod) return res.status(404).json({ ok: false, message: 'Producto no encontrado' });

      const delta = tipo === 'Entrada' ? +Math.abs(cantidad) : -Math.abs(cantidad);
      const newStock = prod.stock + delta;
      if (newStock < 0) return res.status(400).json({ ok: false, message: 'Stock insuficiente' });

      db.run(`UPDATE productos SET stock=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`, [newStock, producto_id]);
      db.run(
        `INSERT INTO movimientos(tipo,producto_id,cantidad,stock_anterior,stock_actual,referencia,usuario_id)
         VALUES(?,?,?,?,?,?,?)`,
        [tipo, producto_id, delta, prod.stock, newStock, referencia||null, req.user.id],
        function (e) {
          if (e) return res.status(500).json({ ok: false, message: e.message });
          res.status(201).json({ ok: true, message: 'Movimiento registrado', id: this.lastID });
        }
      );
    });
  },
};

// ══════════════════════════════════════════════
//  ALERTAS
// ══════════════════════════════════════════════

const alertas = {
  /** GET /api/alertas */
  getAll(req, res) {
    const { tipo, estado, page = 1, limit = 10 } = req.query;
    const offset = (page - 1) * limit;
    let where = []; let params = [];

    if (tipo)   { where.push(`a.tipo = ?`);   params.push(tipo); }
    if (estado) { where.push(`a.estado = ?`); params.push(estado); }

    const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';

    db.get(`SELECT COUNT(*) as total FROM alertas a ${whereSQL}`, params, (err, count) => {
      if (err) return res.status(500).json({ ok: false, message: err.message });
      db.all(
        `SELECT a.*, p.nombre as producto_nombre, p.codigo as producto_codigo
         FROM alertas a LEFT JOIN productos p ON a.producto_id = p.id
         ${whereSQL} ORDER BY a.id DESC LIMIT ? OFFSET ?`,
        [...params, +limit, +offset],
        (err2, rows) => {
          if (err2) return res.status(500).json({ ok: false, message: err2.message });
          res.json({ ok: true, total: count.total, page: +page, limit: +limit, data: rows });
        }
      );
    });
  },

  /** PATCH /api/alertas/:id/resolver */
  resolver(req, res) {
    db.run(`UPDATE alertas SET estado='Resuelta' WHERE id=? AND estado='Pendiente'`,
      [req.params.id], function (err) {
        if (err) return res.status(500).json({ ok: false, message: err.message });
        if (this.changes === 0) return res.status(404).json({ ok: false, message: 'Alerta no encontrada o ya resuelta' });
        res.json({ ok: true, message: 'Alerta marcada como resuelta' });
      }
    );
  },
};

// ══════════════════════════════════════════════
//  CATEGORÍAS
// ══════════════════════════════════════════════

const categorias = {
  getAll(req, res) {
    db.all(`SELECT c.*, COUNT(p.id) as total_productos
            FROM categorias c LEFT JOIN productos p ON p.categoria_id = c.id
            GROUP BY c.id ORDER BY c.nombre`, [],
      (err, rows) => {
        if (err) return res.status(500).json({ ok: false, message: err.message });
        res.json({ ok: true, data: rows });
      }
    );
  },
  create(req, res) {
    const { nombre } = req.body;
    if (!nombre) return res.status(400).json({ ok: false, message: 'nombre es requerido' });
    db.run(`INSERT INTO categorias(nombre) VALUES(?)`, [nombre], function (err) {
      if (err) {
        if (err.message.includes('UNIQUE')) return res.status(409).json({ ok: false, message: 'Categoría ya existe' });
        return res.status(500).json({ ok: false, message: err.message });
      }
      res.status(201).json({ ok: true, message: 'Categoría creada', id: this.lastID });
    });
  },
  remove(req, res) {
    db.run(`DELETE FROM categorias WHERE id=?`, [req.params.id], function (err) {
      if (err) return res.status(500).json({ ok: false, message: err.message });
      if (this.changes === 0) return res.status(404).json({ ok: false, message: 'Categoría no encontrada' });
      res.json({ ok: true, message: 'Categoría eliminada' });
    });
  },
};

// ══════════════════════════════════════════════
//  DASHBOARD
// ══════════════════════════════════════════════

const dashboard = {
  stats(req, res) {
    const queries = {
      totalProductos:      `SELECT COUNT(*) as v FROM productos WHERE estado='Activo'`,
      productosDisponibles:`SELECT COUNT(*) as v FROM productos WHERE stock > 0 AND estado='Activo'`,
      stockBajo:           `SELECT COUNT(*) as v FROM productos WHERE stock <= stock_minimo AND stock > 0 AND estado='Activo'`,
      agotados:            `SELECT COUNT(*) as v FROM productos WHERE stock = 0 AND estado='Activo'`,
      totalUsuarios:       `SELECT COUNT(*) as v FROM usuarios WHERE estado='Activo'`,
      alertasPendientes:   `SELECT COUNT(*) as v FROM alertas WHERE estado='Pendiente'`,
      ventasMes:           `SELECT COALESCE(SUM(total),0) as v FROM ventas WHERE strftime('%Y-%m',created_at)=strftime('%Y-%m','now') AND estado='Pagada'`,
      totalVentasMes:      `SELECT COUNT(*) as v FROM ventas WHERE strftime('%Y-%m',created_at)=strftime('%Y-%m','now')`,
    };

    const results = {};
    const keys = Object.keys(queries);
    let done = 0;

    keys.forEach(key => {
      db.get(queries[key], [], (err, row) => {
        results[key] = err ? 0 : row.v;
        if (++done === keys.length) {
          res.json({ ok: true, data: results });
        }
      });
    });
  },
};

module.exports = { movimientos, alertas, categorias, dashboard };
