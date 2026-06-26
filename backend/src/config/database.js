const { Pool } = require('pg');
require('dotenv').config();

// ── Conexión a PostgreSQL ───────────────────────────────────────────────────
// Si DATABASE_URL existe, se usa esa cadena de conexión.
// Si no, se arma con las variables PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD.
const pool = process.env.DATABASE_URL
  ? new Pool({ connectionString: process.env.DATABASE_URL })
  : new Pool({
      host: process.env.PGHOST || 'localhost',
      port: +(process.env.PGPORT || 5432),
      database: process.env.PGDATABASE || 'sistema_ventas',
      user: process.env.PGUSER || 'postgres',
      password: process.env.PGPASSWORD || 'postgres',
    });

pool.on('error', (err) => {
  console.error('❌ Error inesperado en el pool de PostgreSQL:', err.message);
});

/**
 * Verifica la conexión al arrancar la app.
 */
async function verificarConexion() {
  try {
    const client = await pool.connect();
    const r = await client.query('SELECT NOW()');
    client.release();
    console.log('✅ Conectado a PostgreSQL:', process.env.PGDATABASE || 'sistema_ventas', '-', r.rows[0].now);
  } catch (err) {
    console.error('❌ Error al conectar con PostgreSQL:', err.message);
    process.exit(1);
  }
}

/**
 * Helper de queries. Uso: const { rows } = await query('SELECT * FROM productos WHERE id_producto = $1', [id]);
 */
function query(text, params) {
  return pool.query(text, params);
}

module.exports = { pool, query, verificarConexion };
