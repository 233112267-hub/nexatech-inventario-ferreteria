const { query, pool } = require('../config/database');
const { enviarAlertaStock } = require('../services/emailService');

// ══════════════════════════════════════════════
//  MOVIMIENTOS
// ══════════════════════════════════════════════

const movimientos = {
  /** GET /api/movimientos */
  async getAll(req, res) {
    try {
      const { search, tipo, page = 1, limit = 10 } = req.query;
      const offset = (page - 1) * limit;
      let where = []; let params = [];

      if (search) {
        params.push(`%${search}%`);
        where.push(`(p.nombre ILIKE $${params.length} OR p.codigo ILIKE $${params.length} OR m.referencia ILIKE $${params.length})`);
      }
      if (tipo) { params.push(tipo); where.push(`m.tipo_movimiento = $${params.length}`); }

      const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';

      const { rows: countRows } = await query(
        `SELECT COUNT(*)::int AS total FROM MOVIMIENTOS_INVENTARIO m
         LEFT JOIN PRODUCTOS p ON m.id_producto = p.id_producto ${whereSQL}`,
        params
      );

      params.push(+limit, +offset);
      const { rows } = await query(
        `SELECT m.id_movimiento AS id, m.tipo_movimiento AS tipo, m.id_producto AS producto_id,
                p.nombre AS producto_nombre, p.codigo AS producto_codigo,
                m.cantidad, m.stock_anterior, m.stock_nuevo AS stock_actual, m.referencia,
                m.id_usuario AS usuario_id, u.nombre AS usuario_nombre, m.fecha_movimiento AS created_at
         FROM MOVIMIENTOS_INVENTARIO m
         LEFT JOIN PRODUCTOS p ON m.id_producto = p.id_producto
         LEFT JOIN USUARIOS  u ON m.id_usuario  = u.id_usuario
         ${whereSQL} ORDER BY m.id_movimiento DESC LIMIT $${params.length - 1} OFFSET $${params.length}`,
        params
      );

      res.json({ ok: true, total: countRows[0].total, page: +page, limit: +limit, data: rows });
    } catch (err) {
      res.status(500).json({ ok: false, message: err.message });
    }
  },

  /** POST /api/movimientos — entrada/salida/ajuste manual */
  async create(req, res) {
    const { tipo, producto_id, cantidad, referencia } = req.body;
    if (!tipo || !producto_id || !cantidad) {
      return res.status(400).json({ ok: false, message: 'tipo, producto_id y cantidad son requeridos' });
    }
    const tipoDB = tipo.toUpperCase();

    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      const { rows } = await client.query(
        'SELECT nombre, codigo, stock_actual, stock_minimo FROM PRODUCTOS WHERE id_producto = $1 FOR UPDATE',
        [producto_id]
      );
      const prod = rows[0];
      if (!prod) {
        await client.query('ROLLBACK');
        return res.status(404).json({ ok: false, message: 'Producto no encontrado' });
      }

      const delta = tipoDB === 'ENTRADA' ? Math.abs(cantidad) : -Math.abs(cantidad);
      const newStock = prod.stock_actual + delta;
      if (newStock < 0) {
        await client.query('ROLLBACK');
        return res.status(400).json({ ok: false, message: 'Stock insuficiente' });
      }

      await client.query(
        'UPDATE PRODUCTOS SET stock_actual = $1, updated_at = CURRENT_TIMESTAMP WHERE id_producto = $2',
        [newStock, producto_id]
      );

      const { rows: movRows } = await client.query(
        `INSERT INTO MOVIMIENTOS_INVENTARIO (id_producto, id_usuario, tipo_movimiento, cantidad, stock_anterior, stock_nuevo, referencia)
         VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id_movimiento`,
        [producto_id, req.user.id, tipoDB, delta, prod.stock_actual, newStock, referencia || null]
      );

      // Si el movimiento deja el stock en o por debajo del mínimo, generar alerta y notificar
      if (newStock <= prod.stock_minimo) {
        const tipoAlerta = newStock === 0 ? 'Critica' : 'Advertencia';
        const nombreAlerta = newStock === 0 ? 'Sin stock' : 'Stock bajo';
        const descripcionAlerta = newStock === 0
          ? `Sin unidades disponibles (mínimo: ${prod.stock_minimo}).`
          : `Quedan ${newStock} unidades (mínimo: ${prod.stock_minimo}).`;

        await client.query(
          `INSERT INTO ALERTAS (tipo, nombre, descripcion, id_producto) VALUES ($1,$2,$3,$4)`,
          [tipoAlerta, nombreAlerta, descripcionAlerta, producto_id]
        );

        if (tipoAlerta === 'Critica') {
          enviarAlertaStock({
            tipo: tipoAlerta,
            nombre: nombreAlerta,
            descripcion: descripcionAlerta,
            producto_nombre: prod.nombre,
            producto_codigo: prod.codigo,
          }).catch(err => console.error('Error enviando notificación de alerta:', err.message));
        }
      }

      await client.query('COMMIT');
      res.status(201).json({ ok: true, message: 'Movimiento registrado', id: movRows[0].id_movimiento });
    } catch (err) {
      await client.query('ROLLBACK');
      res.status(500).json({ ok: false, message: err.message });
    } finally {
      client.release();
    }
  },
};

// ══════════════════════════════════════════════
//  ALERTAS
// ══════════════════════════════════════════════

const alertas = {
  /** GET /api/alertas */
  async getAll(req, res) {
    try {
      const { tipo, estado, page = 1, limit = 10 } = req.query;
      const offset = (page - 1) * limit;
      let where = []; let params = [];

      if (tipo)   { params.push(tipo);   where.push(`a.tipo = $${params.length}`); }
      if (estado) { params.push(estado); where.push(`a.estado = $${params.length}`); }

      const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';

      const { rows: countRows } = await query(`SELECT COUNT(*)::int AS total FROM ALERTAS a ${whereSQL}`, params);

      params.push(+limit, +offset);
      const { rows } = await query(
        `SELECT a.id_alerta AS id, a.tipo, a.nombre, a.descripcion, a.id_producto AS producto_id,
                p.nombre AS producto_nombre, p.codigo AS producto_codigo, a.estado, a.fecha_creacion AS created_at
         FROM ALERTAS a LEFT JOIN PRODUCTOS p ON a.id_producto = p.id_producto
         ${whereSQL} ORDER BY a.id_alerta DESC LIMIT $${params.length - 1} OFFSET $${params.length}`,
        params
      );

      res.json({ ok: true, total: countRows[0].total, page: +page, limit: +limit, data: rows });
    } catch (err) {
      res.status(500).json({ ok: false, message: err.message });
    }
  },

  /** POST /api/alertas/:id/notificar — reenviar el correo de una alerta puntual */
  async notificar(req, res) {
    try {
      const { rows } = await query(
        `SELECT a.tipo, a.nombre, a.descripcion, p.nombre AS producto_nombre, p.codigo AS producto_codigo
         FROM ALERTAS a LEFT JOIN PRODUCTOS p ON a.id_producto = p.id_producto
         WHERE a.id_alerta = $1`,
        [req.params.id]
      );
      if (!rows[0]) return res.status(404).json({ ok: false, message: 'Alerta no encontrada' });

      const resultado = await enviarAlertaStock(rows[0]);
      if (!resultado.ok) return res.status(502).json({ ok: false, message: resultado.message });

      res.json({ ok: true, message: 'Notificación enviada', destinatarios: resultado.destinatarios });
    } catch (err) {
      res.status(500).json({ ok: false, message: err.message });
    }
  },

  /** PATCH /api/alertas/:id/resolver */
  async resolver(req, res) {
    try {
      const { rowCount } = await query(
        `UPDATE ALERTAS SET estado = 'Resuelta' WHERE id_alerta = $1 AND estado = 'Pendiente'`,
        [req.params.id]
      );
      if (rowCount === 0) return res.status(404).json({ ok: false, message: 'Alerta no encontrada o ya resuelta' });
      res.json({ ok: true, message: 'Alerta marcada como resuelta' });
    } catch (err) {
      res.status(500).json({ ok: false, message: err.message });
    }
  },
};

// ══════════════════════════════════════════════
//  CATEGORÍAS
// ══════════════════════════════════════════════

const categorias = {
  async getAll(req, res) {
    try {
      const { rows } = await query(
        `SELECT c.id_categoria AS id, c.nombre, COUNT(p.id_producto)::int AS total_productos
         FROM CATEGORIAS c LEFT JOIN PRODUCTOS p ON p.id_categoria = c.id_categoria
         GROUP BY c.id_categoria ORDER BY c.nombre`
      );
      res.json({ ok: true, data: rows });
    } catch (err) {
      res.status(500).json({ ok: false, message: err.message });
    }
  },
  async create(req, res) {
    const { nombre } = req.body;
    if (!nombre) return res.status(400).json({ ok: false, message: 'nombre es requerido' });
    try {
      const { rows } = await query('INSERT INTO CATEGORIAS (nombre) VALUES ($1) RETURNING id_categoria', [nombre]);
      res.status(201).json({ ok: true, message: 'Categoría creada', id: rows[0].id_categoria });
    } catch (err) {
      if (err.code === '23505') return res.status(409).json({ ok: false, message: 'Categoría ya existe' });
      res.status(500).json({ ok: false, message: err.message });
    }
  },
  async remove(req, res) {
    try {
      const { rowCount } = await query('DELETE FROM CATEGORIAS WHERE id_categoria = $1', [req.params.id]);
      if (rowCount === 0) return res.status(404).json({ ok: false, message: 'Categoría no encontrada' });
      res.json({ ok: true, message: 'Categoría eliminada' });
    } catch (err) {
      res.status(500).json({ ok: false, message: err.message });
    }
  },
};

// ══════════════════════════════════════════════
//  DASHBOARD
// ══════════════════════════════════════════════

const dashboard = {
  /** GET /api/dashboard/ventas-semana — total vendido por día, últimos 7 días */
  async ventasSemana(req, res) {
    try {
      const { rows } = await query(`
        SELECT to_char(d::date, 'DY') AS dia, to_char(d::date, 'YYYY-MM-DD') AS fecha,
               COALESCE(SUM(v.total), 0)::float AS total
        FROM generate_series(CURRENT_DATE - INTERVAL '6 days', CURRENT_DATE, INTERVAL '1 day') d
        LEFT JOIN VENTAS v ON v.fecha_venta::date = d::date AND v.estado = 'Pagada'
        GROUP BY d, dia
        ORDER BY d
      `);
      res.json({ ok: true, data: rows });
    } catch (err) {
      res.status(500).json({ ok: false, message: err.message });
    }
  },
  async stats(req, res) {
    try {
      const queries = {
        totalProductos:       `SELECT COUNT(*)::int AS v FROM PRODUCTOS WHERE estado='Activo'`,
        productosDisponibles: `SELECT COUNT(*)::int AS v FROM PRODUCTOS WHERE stock_actual > 0 AND estado='Activo'`,
        stockBajo:            `SELECT COUNT(*)::int AS v FROM PRODUCTOS WHERE stock_actual <= stock_minimo AND stock_actual > 0 AND estado='Activo'`,
        agotados:             `SELECT COUNT(*)::int AS v FROM PRODUCTOS WHERE stock_actual = 0 AND estado='Activo'`,
        totalUsuarios:        `SELECT COUNT(*)::int AS v FROM USUARIOS WHERE activo = TRUE`,
        alertasPendientes:    `SELECT COUNT(*)::int AS v FROM ALERTAS WHERE estado='Pendiente'`,
        ventasMes:            `SELECT COALESCE(SUM(total),0)::float AS v FROM VENTAS WHERE date_trunc('month', fecha_venta) = date_trunc('month', CURRENT_DATE) AND estado='Pagada'`,
        totalVentasMes:       `SELECT COUNT(*)::int AS v FROM VENTAS WHERE date_trunc('month', fecha_venta) = date_trunc('month', CURRENT_DATE)`,
      };

      const keys = Object.keys(queries);
      const results = {};
      const values = await Promise.all(keys.map(k => query(queries[k])));
      keys.forEach((k, i) => { results[k] = values[i].rows[0].v; });

      res.json({ ok: true, data: results });
    } catch (err) {
      res.status(500).json({ ok: false, message: err.message });
    }
  },
};

module.exports = { movimientos, alertas, categorias, dashboard };
