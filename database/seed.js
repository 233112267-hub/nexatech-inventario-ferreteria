/**
 * Script de seed — inserta datos de prueba en PostgreSQL.
 * Requiere que el esquema (schema_postgres.sql) ya esté creado.
 *
 * Uso:  node src/config/seed.js
 */
const bcrypt = require('bcryptjs');
const { query, pool } = require('./database');

async function seed() {
  console.log('🌱 Insertando datos de prueba...');

  // ── Verificar si ya hay usuarios (evitar duplicados) ──
  const { rows: existentes } = await query('SELECT COUNT(*)::int AS total FROM USUARIOS');
  if (existentes[0].total > 0) {
    console.log('ℹ️  Ya existen usuarios en la base de datos. Seed cancelado.');
    await pool.end();
    return;
  }

  // ── Obtener IDs de roles ──
  const { rows: roles } = await query('SELECT id_rol, nombre FROM ROLES');
  const rolId = (nombre) => roles.find(r => r.nombre === nombre)?.id_rol;

  const hashAdmin = await bcrypt.hash('admin123', 10);
  const hashVend  = await bcrypt.hash('vend123', 10);

  const usuarios = [
    ['Aylin Herrera',  'Aylin.H',  'aylin@ferreteria.com',  hashAdmin, rolId('Administrador'), true],
    ['Zaid Hernández', 'Zaid.H',   'zaid@ferreteria.com',   hashVend,  rolId('Vendedor'),       true],
    ['Saul Gonzalez',  'Saul.G',   'saul@ferreteria.com',   hashVend,  rolId('Vendedor'),       true],
    ['Randy Lopez',    'Randy.L',  'randy@ferreteria.com',  hashVend,  rolId('Vendedor'),       true],
    ['Deyla Martinez', 'Deyla.M',  'deyla@ferreteria.com',  hashVend,  rolId('Vendedor'),       false],
  ];

  for (const u of usuarios) {
    await query(
      `INSERT INTO USUARIOS (nombre, username, email, password_hash, id_rol, activo)
       VALUES ($1,$2,$3,$4,$5,$6)`,
      u
    );
  }
  console.log(`✅ ${usuarios.length} usuarios insertados`);

  // ── Categorías ya vienen del schema_postgres.sql, las recuperamos ──
  const { rows: categorias } = await query('SELECT id_categoria, nombre FROM CATEGORIAS');
  const catId = (nombre) => categorias.find(c => c.nombre === nombre)?.id_categoria;

  const productos = [
    ['PROD-001', 'Taladro inalámbrico 20V', 'Taladro de alta potencia', catId('Herramientas'), 1400.00, 1850.00, 15, 5],
    ['PROD-002', 'Tornillo para madera 2"', 'Paquete 100 piezas',       catId('Ferretería'),   0.15,    0.25,    250, 10],
    ['PROD-003', 'Cemento gris 50 kg',      'Cemento estándar',         catId('Materiales'),   150.00,  195.00,  20, 20],
    ['PROD-004', 'Pintura blanca 1 galón',  'Pintura vinílica',         catId('Pintura'),      180.00,  240.00,  18, 10],
    ['PROD-005', 'Cable eléctrico 12 AWG',  'Cable por metro',          catId('Eléctricos'),   22.00,   32.00,   45, 15],
    ['PROD-006', 'Tubo PVC 1/2"',           'Tubo 3 metros',            catId('Plomería'),     12.00,   18.00,   0,  10],
    ['PROD-007', 'Guantes de trabajo',      'Talla estándar',           catId('Seguridad'),    30.00,   45.00,   30, 10],
    ['PROD-008', 'Cinta métrica 5m',        'Cinta de acero',           catId('Herramientas'), 60.00,   85.00,   12, 15],
  ];

  for (const p of productos) {
    await query(
      `INSERT INTO PRODUCTOS (codigo, nombre, descripcion, id_categoria, precio_compra, precio_venta, stock_actual, stock_minimo)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8)`,
      p
    );
  }
  console.log(`✅ ${productos.length} productos insertados`);

  // ── Alertas iniciales (igual que la versión SQLite) ──
  const { rows: prods } = await query('SELECT id_producto, codigo FROM PRODUCTOS');
  const prodId = (codigo) => prods.find(p => p.codigo === codigo)?.id_producto;

  await query(
    `INSERT INTO ALERTAS (tipo, nombre, descripcion, id_producto, estado) VALUES
     ('Critica', 'Stock crítico', 'El stock actual (20) está por debajo del mínimo (20).', $1, 'Pendiente'),
     ('Advertencia', 'Stock bajo', 'El stock actual (12) está por debajo del mínimo (15).', $2, 'Pendiente'),
     ('Critica', 'Sin stock', 'El producto no tiene unidades disponibles.', $3, 'Pendiente')`,
    [prodId('PROD-003'), prodId('PROD-008'), prodId('PROD-006')]
  );
  console.log('✅ Alertas iniciales insertadas');

  console.log('🌱 Seed completo.');
  await pool.end();
}

seed().catch((err) => {
  console.error('❌ Error en seed:', err);
  process.exit(1);
});
