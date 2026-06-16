const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const bcrypt = require('bcryptjs');
require('dotenv').config();

const DB_PATH = process.env.DB_PATH || './ferreteria.db';

const db = new sqlite3.Database(path.resolve(DB_PATH), (err) => {
  if (err) {
    console.error('❌ Error al conectar con la base de datos:', err.message);
    process.exit(1);
  }
  console.log('✅ Conectado a SQLite:', DB_PATH);
});

db.serialize(() => {
  db.run('PRAGMA foreign_keys = ON');

  // ── USUARIOS ─────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT    NOT NULL,
    usuario    TEXT    NOT NULL UNIQUE,
    correo     TEXT    NOT NULL UNIQUE,
    password   TEXT    NOT NULL,
    rol        TEXT    NOT NULL DEFAULT 'Vendedor'
                       CHECK(rol IN ('Administrador','Vendedor','Almacenista')),
    estado     TEXT    NOT NULL DEFAULT 'Activo'
                       CHECK(estado IN ('Activo','Inactivo')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  // ── CATEGORÍAS ────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS categorias (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT    NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  // ── PRODUCTOS ─────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS productos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo       TEXT    NOT NULL UNIQUE,
    nombre       TEXT    NOT NULL,
    descripcion  TEXT,
    categoria_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL,
    precio       REAL    NOT NULL DEFAULT 0,
    stock        INTEGER NOT NULL DEFAULT 0,
    stock_minimo INTEGER NOT NULL DEFAULT 0,
    estado       TEXT    NOT NULL DEFAULT 'Activo'
                         CHECK(estado IN ('Activo','Inactivo')),
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  // ── VENTAS ────────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS ventas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    folio          TEXT    NOT NULL UNIQUE,
    cliente        TEXT,
    vendedor_id    INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    subtotal       REAL    NOT NULL DEFAULT 0,
    descuento      REAL    NOT NULL DEFAULT 0,
    impuestos      REAL    NOT NULL DEFAULT 0,
    total          REAL    NOT NULL DEFAULT 0,
    metodo_pago    TEXT    NOT NULL DEFAULT 'Efectivo'
                           CHECK(metodo_pago IN ('Efectivo','Tarjeta','Transferencia')),
    estado         TEXT    NOT NULL DEFAULT 'Pagada'
                           CHECK(estado IN ('Pagada','Pendiente','Cancelada')),
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  // ── DETALLE VENTA ─────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS venta_detalle (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id    INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    cantidad    INTEGER NOT NULL,
    precio_unit REAL    NOT NULL,
    subtotal    REAL    NOT NULL
  )`);

  // ── MOVIMIENTOS ───────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS movimientos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo           TEXT    NOT NULL CHECK(tipo IN ('Entrada','Salida','Ajuste')),
    producto_id    INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    cantidad       INTEGER NOT NULL,
    stock_anterior INTEGER,
    stock_actual   INTEGER,
    referencia     TEXT,
    usuario_id     INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  // ── ALERTAS ───────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS alertas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo        TEXT    NOT NULL CHECK(tipo IN ('Crítica','Advertencia','Informativa')),
    nombre      TEXT    NOT NULL,
    descripcion TEXT,
    producto_id INTEGER REFERENCES productos(id) ON DELETE CASCADE,
    estado      TEXT    NOT NULL DEFAULT 'Pendiente'
                        CHECK(estado IN ('Pendiente','Resuelta','Informativa')),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  // ── SEED ─────────────────────────────────────────
  seedData();
});

async function seedData() {
  // Seed only if tables are empty
  db.get('SELECT COUNT(*) as cnt FROM usuarios', async (err, row) => {
    if (err || row.cnt > 0) return;

    const hash = await bcrypt.hash('admin123', 10);
    const hashVend = await bcrypt.hash('vend123', 10);

    // Users
    const users = [
      ['Aylin Herrera',  'Aylin.H',  'aylin@ferreteria.com',  hash,     'Administrador', 'Activo'],
      ['Zaid Hernández', 'Zaid.H',   'zaid@ferreteria.com',   hashVend, 'Vendedor',      'Activo'],
      ['Saul Gonzalez',  'Saul.G',   'saul@ferreteria.com',   hashVend, 'Vendedor',      'Activo'],
      ['Randy Lopez',    'Randy.L',  'randy@ferreteria.com',  hashVend, 'Vendedor',      'Activo'],
      ['Deyla Martinez', 'Deyla.M',  'deyla@ferreteria.com',  hashVend, 'Vendedor',      'Inactivo'],
    ];
    users.forEach(u => {
      db.run(`INSERT OR IGNORE INTO usuarios(nombre,usuario,correo,password,rol,estado) VALUES(?,?,?,?,?,?)`, u);
    });

    // Categories
    const cats = ['Herramientas','Ferretería','Materiales','Pintura','Eléctricos','Plomería','Seguridad'];
    cats.forEach(c => db.run(`INSERT OR IGNORE INTO categorias(nombre) VALUES(?)`, [c]));

    // Products (after short delay so categories exist)
    setTimeout(() => {
      const products = [
        ['PROD-001','Taladro inalámbrico 20V',  'Taladro de alta potencia', 1, 1850.00, 15, 5,  'Activo'],
        ['PROD-002','Tornillo para madera 2"',  'Paquete 100 piezas',       2, 0.25,    250,10, 'Activo'],
        ['PROD-003','Cemento gris 50 kg',       'Cemento estándar',         3, 195.00,  20, 20, 'Activo'],
        ['PROD-004','Pintura blanca 1 galón',   'Pintura vinílica',         4, 240.00,  18, 10, 'Activo'],
        ['PROD-005','Cable eléctrico 12 AWG',   'Cable por metro',          5, 32.00,   45, 15, 'Activo'],
        ['PROD-006','Tubo PVC 1/2"',            'Tubo 3 metros',            6, 18.00,   0,  10, 'Activo'],
        ['PROD-007','Guantes de trabajo',       'Talla estándar',           7, 45.00,   30, 10, 'Activo'],
        ['PROD-008','Cinta métrica 5m',         'Cinta de acero',           1, 85.00,   12, 15, 'Activo'],
      ];
      products.forEach(p => {
        db.run(`INSERT OR IGNORE INTO productos(codigo,nombre,descripcion,categoria_id,precio,stock,stock_minimo,estado) VALUES(?,?,?,?,?,?,?,?)`, p);
      });

      // Seed some alerts
      setTimeout(() => {
        db.run(`INSERT OR IGNORE INTO alertas(tipo,nombre,descripcion,producto_id,estado) VALUES('Crítica','Stock crítico','El stock actual (20) está por debajo del mínimo (20).',3,'Pendiente')`);
        db.run(`INSERT OR IGNORE INTO alertas(tipo,nombre,descripcion,producto_id,estado) VALUES('Advertencia','Stock bajo','El stock actual (12) está por debajo del mínimo (15).',8,'Pendiente')`);
        db.run(`INSERT OR IGNORE INTO alertas(tipo,nombre,descripcion,producto_id,estado) VALUES('Crítica','Sin stock','El producto no tiene unidades disponibles.',6,'Pendiente')`);
        console.log('✅ Datos iniciales insertados');
      }, 300);
    }, 300);
  });
}

module.exports = db;
