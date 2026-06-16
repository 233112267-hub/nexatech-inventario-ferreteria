const db = require('../config/database');

/** GET /api/ventas */
const getAll = (req, res) => {
  const { search, estado, page = 1, limit = 10 } = req.query;
  const offset = (page - 1) * limit;
  let where = []; let params = [];

  if (search) { where.push(`(v.folio LIKE ? OR v.cliente LIKE ?)`); const q=`%${search}%`; params.push(q,q); }
  if (estado)  { where.push(`v.estado = ?`); params.push(estado); }

  const whereSQL = where.length ? `WHERE ${where.join(' AND ')}` : '';

  db.get(`SELECT COUNT(*) as total FROM ventas v ${whereSQL}`, params, (err, count) => {
    if (err) return res.status(500).json({ ok: false, message: err.message });
    db.all(
      `SELECT v.*, u.nombre as vendedor_nombre FROM ventas v
       LEFT JOIN usuarios u ON v.vendedor_id = u.id
       ${whereSQL} ORDER BY v.id DESC LIMIT ? OFFSET ?`,
      [...params, +limit, +offset],
      (err2, rows) => {
        if (err2) return res.status(500).json({ ok: false, message: err2.message });
        res.json({ ok: true, total: count.total, page: +page, limit: +limit, data: rows });
      }
    );
  });
};

/** GET /api/ventas/:id */
const getOne = (req, res) => {
  db.get(
    `SELECT v.*, u.nombre as vendedor_nombre FROM ventas v LEFT JOIN usuarios u ON v.vendedor_id=u.id WHERE v.id=?`,
    [req.params.id],
    (err, venta) => {
      if (err) return res.status(500).json({ ok: false, message: err.message });
      if (!venta) return res.status(404).json({ ok: false, message: 'Venta no encontrada' });

      db.all(
        `SELECT vd.*, p.nombre as producto_nombre, p.codigo FROM venta_detalle vd
         JOIN productos p ON vd.producto_id = p.id WHERE vd.venta_id = ?`,
        [venta.id],
        (err2, detalle) => {
          if (err2) return res.status(500).json({ ok: false, message: err2.message });
          res.json({ ok: true, data: { ...venta, detalle } });
        }
      );
    }
  );
};

/** POST /api/ventas
 * Body: { cliente, vendedor_id, metodo_pago, descuento, items: [{producto_id, cantidad}] }
 */
const create = (req, res) => {
  const { cliente, vendedor_id, metodo_pago = 'Efectivo', descuento = 0, items } = req.body;

  if (!items || !Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ ok: false, message: 'Se requiere al menos un producto en items' });
  }

  // Validate stock for all items first
  let checked = 0;
  let errors = [];
  let productData = {};

  const checkStock = () => {
    items.forEach(item => {
      db.get(`SELECT id, nombre, precio, stock FROM productos WHERE id = ? AND estado = 'Activo'`,
        [item.producto_id],
        (err, prod) => {
          checked++;
          if (err || !prod) { errors.push(`Producto ID ${item.producto_id} no encontrado`); }
          else if (prod.stock < item.cantidad) {
            errors.push(`Stock insuficiente para "${prod.nombre}" (disponible: ${prod.stock})`);
          } else {
            productData[item.producto_id] = prod;
          }
          if (checked === items.length) finalizeSale();
        }
      );
    });
  };

  const finalizeSale = () => {
    if (errors.length) return res.status(400).json({ ok: false, message: errors.join('; ') });

    // Calculate totals
    let subtotal = 0;
    items.forEach(item => {
      subtotal += productData[item.producto_id].precio * item.cantidad;
    });
    const descuentoAmt = discountAmount(subtotal, descuento);
    const impuestos = (subtotal - descuentoAmt) * 0.16;
    const total = subtotal - descuentoAmt + impuestos;
    const folio = `VTA-${Date.now().toString().slice(-6)}`;

    db.run(
      `INSERT INTO ventas(folio,cliente,vendedor_id,subtotal,descuento,impuestos,total,metodo_pago) VALUES(?,?,?,?,?,?,?,?)`,
      [folio, cliente||null, vendedor_id||req.user.id, subtotal, descuentoAmt, impuestos, total, metodo_pago],
      function (err) {
        if (err) return res.status(500).json({ ok: false, message: err.message });
        const ventaId = this.lastID;

        // Insert detail lines + update stock
        items.forEach(item => {
          const prod = productData[item.producto_id];
          const lineSubtotal = prod.precio * item.cantidad;
          const newStock = prod.stock - item.cantidad;

          db.run(`INSERT INTO venta_detalle(venta_id,producto_id,cantidad,precio_unit,subtotal) VALUES(?,?,?,?,?)`,
            [ventaId, item.producto_id, item.cantidad, prod.precio, lineSubtotal]);

          db.run(`UPDATE productos SET stock=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`,
            [newStock, item.producto_id]);

          // Register movement
          db.run(`INSERT INTO movimientos(tipo,producto_id,cantidad,stock_anterior,stock_actual,referencia,usuario_id)
                  VALUES('Salida',?,?,?,?,?,?)`,
            [item.producto_id, -item.cantidad, prod.stock, newStock, folio, req.user.id]);

          // Auto-alert if stock falls below minimum
          if (newStock <= prod.stock_minimo) {
            const tipo = newStock === 0 ? 'Crítica' : 'Advertencia';
            const nombre = newStock === 0 ? 'Sin stock' : 'Stock bajo';
            db.run(`INSERT INTO alertas(tipo,nombre,descripcion,producto_id) VALUES(?,?,?,?)`,
              [tipo, nombre, `Stock actual (${newStock}) <= mínimo tras venta ${folio}.`, item.producto_id]);
          }
        });

        res.status(201).json({ ok: true, message: 'Venta registrada', id: ventaId, folio, total });
      }
    );
  };

  checkStock();
};

/** PATCH /api/ventas/:id/cancelar */
const cancelar = (req, res) => {
  db.get(`SELECT * FROM ventas WHERE id = ?`, [req.params.id], (err, venta) => {
    if (err) return res.status(500).json({ ok: false, message: err.message });
    if (!venta) return res.status(404).json({ ok: false, message: 'Venta no encontrada' });
    if (venta.estado === 'Cancelada') return res.status(400).json({ ok: false, message: 'Venta ya cancelada' });

    // Restore stock
    db.all(`SELECT * FROM venta_detalle WHERE venta_id = ?`, [venta.id], (err2, items) => {
      if (err2) return res.status(500).json({ ok: false, message: err2.message });
      items.forEach(item => {
        db.get(`SELECT stock FROM productos WHERE id = ?`, [item.producto_id], (e, prod) => {
          if (e || !prod) return;
          const restored = prod.stock + item.cantidad;
          db.run(`UPDATE productos SET stock=?,updated_at=CURRENT_TIMESTAMP WHERE id=?`, [restored, item.producto_id]);
          db.run(`INSERT INTO movimientos(tipo,producto_id,cantidad,stock_anterior,stock_actual,referencia,usuario_id)
                  VALUES('Entrada',?,?,?,?,?,?)`,
            [item.producto_id, item.cantidad, prod.stock, restored, `Cancelación ${venta.folio}`, req.user.id]);
        });
      });

      db.run(`UPDATE ventas SET estado='Cancelada' WHERE id=?`, [venta.id], (e) => {
        if (e) return res.status(500).json({ ok: false, message: e.message });
        res.json({ ok: true, message: 'Venta cancelada y stock restaurado' });
      });
    });
  });
};

function discountAmount(subtotal, discount) {
  if (!discount) return 0;
  return typeof discount === 'string' && discount.includes('%')
    ? subtotal * (parseFloat(discount) / 100)
    : Math.min(parseFloat(discount), subtotal);
}

module.exports = { getAll, getOne, create, cancelar };
