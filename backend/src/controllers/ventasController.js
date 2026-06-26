const { query, pool } = require('../config/database');

/** GET /api/ventas */
const getAll = async (req, res) => {
  try {
    const { search, estado, page = 1, limit = 10 } = req.query;
    const offset = (page - 1) * limit;
    let where = []; let params = [];

    if (search) {
      params.push(`%${search}%`);
      where.push(`(v.folio ILIKE $${params.length} OR v.cliente ILIKE $${params.length})`);
    }
    if (estado) { params.push(estado); where.push(`v.estado = $${params.length}`); }

    const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';

    const { rows: countRows } = await query(`SELECT COUNT(*)::int AS total FROM VENTAS v ${whereSQL}`, params);

    params.push(+limit, +offset);
    const { rows } = await query(
      `SELECT v.id_venta AS id, v.folio, v.cliente, v.id_usuario AS vendedor_id, u.nombre AS vendedor_nombre,
              v.subtotal, v.descuento, v.impuestos, v.total, v.metodo_pago, v.estado, v.fecha_venta AS created_at
       FROM VENTAS v LEFT JOIN USUARIOS u ON v.id_usuario = u.id_usuario
       ${whereSQL} ORDER BY v.id_venta DESC LIMIT $${params.length - 1} OFFSET $${params.length}`,
      params
    );

    res.json({ ok: true, total: countRows[0].total, page: +page, limit: +limit, data: rows });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** GET /api/ventas/:id */
const getOne = async (req, res) => {
  try {
    const { rows: ventaRows } = await query(
      `SELECT v.id_venta AS id, v.folio, v.cliente, v.id_usuario AS vendedor_id, u.nombre AS vendedor_nombre,
              v.subtotal, v.descuento, v.impuestos, v.total, v.metodo_pago, v.estado, v.fecha_venta AS created_at
       FROM VENTAS v LEFT JOIN USUARIOS u ON v.id_usuario = u.id_usuario WHERE v.id_venta = $1`,
      [req.params.id]
    );
    const venta = ventaRows[0];
    if (!venta) return res.status(404).json({ ok: false, message: 'Venta no encontrada' });

    const { rows: detalle } = await query(
      `SELECT dv.id_detalle AS id, dv.id_producto AS producto_id, p.nombre AS producto_nombre, p.codigo,
              dv.cantidad, dv.precio_unitario AS precio_unit, dv.subtotal
       FROM DETALLE_VENTAS dv JOIN PRODUCTOS p ON dv.id_producto = p.id_producto
       WHERE dv.id_venta = $1`,
      [venta.id]
    );

    res.json({ ok: true, data: { ...venta, detalle } });
  } catch (err) {
    res.status(500).json({ ok: false, message: err.message });
  }
};

/** POST /api/ventas
 * Body: { cliente, vendedor_id, metodo_pago, descuento, items: [{producto_id, cantidad}] }
 */
const create = async (req, res) => {
  const { cliente, vendedor_id, metodo_pago = 'Efectivo', descuento = 0, items } = req.body;

  if (!items || !Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ ok: false, message: 'Se requiere al menos un producto en items' });
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // 1) Validar stock y traer datos de producto (con bloqueo de fila para evitar carreras)
    const productData = {};
    for (const item of items) {
      const { rows } = await client.query(
        `SELECT id_producto, nombre, precio_venta, stock_actual, stock_minimo
         FROM PRODUCTOS WHERE id_producto = $1 AND estado = 'Activo' FOR UPDATE`,
        [item.producto_id]
      );
      const prod = rows[0];
      if (!prod) throw new AppError(`Producto ID ${item.producto_id} no encontrado`);
      if (prod.stock_actual < item.cantidad) {
        throw new AppError(`Stock insuficiente para "${prod.nombre}" (disponible: ${prod.stock_actual})`);
      }
      productData[item.producto_id] = prod;
    }

    // 2) Calcular totales
    let subtotal = 0;
    items.forEach(item => {
      subtotal += parseFloat(productData[item.producto_id].precio_venta) * item.cantidad;
    });
    const descuentoAmt = discountAmount(subtotal, descuento);
    const impuestos = (subtotal - descuentoAmt) * 0.16;
    const total = subtotal - descuentoAmt + impuestos;
    const folio = `VTA-${Date.now().toString().slice(-6)}`;

    // 3) Insertar venta
    const { rows: ventaRows } = await client.query(
      `INSERT INTO VENTAS (id_usuario, folio, cliente, subtotal, descuento, impuestos, total, metodo_pago)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id_venta`,
      [vendedor_id || req.user.id, folio, cliente || null, subtotal, descuentoAmt, impuestos, total, metodo_pago]
    );
    const ventaId = ventaRows[0].id_venta;

    // 4) Detalle + actualizar stock + movimientos + alertas
    for (const item of items) {
      const prod = productData[item.producto_id];
      const lineSubtotal = parseFloat(prod.precio_venta) * item.cantidad;
      const newStock = prod.stock_actual - item.cantidad;

      await client.query(
        `INSERT INTO DETALLE_VENTAS (id_venta, id_producto, cantidad, precio_unitario, subtotal)
         VALUES ($1,$2,$3,$4,$5)`,
        [ventaId, item.producto_id, item.cantidad, prod.precio_venta, lineSubtotal]
      );

      await client.query(
        `UPDATE PRODUCTOS SET stock_actual = $1, updated_at = CURRENT_TIMESTAMP WHERE id_producto = $2`,
        [newStock, item.producto_id]
      );

      await client.query(
        `INSERT INTO MOVIMIENTOS_INVENTARIO (id_producto, id_usuario, tipo_movimiento, cantidad, stock_anterior, stock_nuevo, referencia)
         VALUES ($1,$2,'SALIDA',$3,$4,$5,$6)`,
        [item.producto_id, req.user.id, item.cantidad, prod.stock_actual, newStock, folio]
      );

      if (newStock <= prod.stock_minimo) {
        const tipo = newStock === 0 ? 'Critica' : 'Advertencia';
        const nombreAlerta = newStock === 0 ? 'Sin stock' : 'Stock bajo';
        await client.query(
          `INSERT INTO ALERTAS (tipo, nombre, descripcion, id_producto)
           VALUES ($1,$2,$3,$4)`,
          [tipo, nombreAlerta, `Stock actual (${newStock}) <= mínimo tras venta ${folio}.`, item.producto_id]
        );
      }
    }

    await client.query('COMMIT');
    res.status(201).json({ ok: true, message: 'Venta registrada', id: ventaId, folio, total });
  } catch (err) {
    await client.query('ROLLBACK');
    const status = err instanceof AppError ? 400 : 500;
    res.status(status).json({ ok: false, message: err.message });
  } finally {
    client.release();
  }
};

/** PATCH /api/ventas/:id/cancelar */
const cancelar = async (req, res) => {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const { rows: ventaRows } = await client.query('SELECT * FROM VENTAS WHERE id_venta = $1 FOR UPDATE', [req.params.id]);
    const venta = ventaRows[0];
    if (!venta) throw new AppError('Venta no encontrada', 404);
    if (venta.estado === 'Cancelada') throw new AppError('Venta ya cancelada');

    const { rows: items } = await client.query('SELECT * FROM DETALLE_VENTAS WHERE id_venta = $1', [venta.id_venta]);

    for (const item of items) {
      const { rows: prodRows } = await client.query(
        'SELECT stock_actual FROM PRODUCTOS WHERE id_producto = $1 FOR UPDATE',
        [item.id_producto]
      );
      const prod = prodRows[0];
      if (!prod) continue;

      const restored = prod.stock_actual + item.cantidad;
      await client.query(
        'UPDATE PRODUCTOS SET stock_actual = $1, updated_at = CURRENT_TIMESTAMP WHERE id_producto = $2',
        [restored, item.id_producto]
      );
      await client.query(
        `INSERT INTO MOVIMIENTOS_INVENTARIO (id_producto, id_usuario, tipo_movimiento, cantidad, stock_anterior, stock_nuevo, referencia)
         VALUES ($1,$2,'ENTRADA',$3,$4,$5,$6)`,
        [item.id_producto, req.user.id, item.cantidad, prod.stock_actual, restored, `Cancelación ${venta.folio}`]
      );
    }

    await client.query(`UPDATE VENTAS SET estado = 'Cancelada' WHERE id_venta = $1`, [venta.id_venta]);

    await client.query('COMMIT');
    res.json({ ok: true, message: 'Venta cancelada y stock restaurado' });
  } catch (err) {
    await client.query('ROLLBACK');
    const status = err instanceof AppError ? err.status || 400 : 500;
    res.status(status).json({ ok: false, message: err.message });
  } finally {
    client.release();
  }
};

class AppError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.status = status;
  }
}

function discountAmount(subtotal, discount) {
  if (!discount) return 0;
  return typeof discount === 'string' && discount.includes('%')
    ? subtotal * (parseFloat(discount) / 100)
    : Math.min(parseFloat(discount), subtotal);
}

module.exports = { getAll, getOne, create, cancelar };
