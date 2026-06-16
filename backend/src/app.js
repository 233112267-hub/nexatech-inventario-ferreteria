require('dotenv').config();
const express       = require('express');
const cors          = require('cors');
const helmet        = require('helmet');
const morgan        = require('morgan');
const swaggerJsdoc  = require('swagger-jsdoc');
const swaggerUi     = require('swagger-ui-express');

// Initialize DB (creates tables + seed data)
require('./config/database');

const routes = require('./routes');

const app  = express();
const PORT = process.env.PORT || 3000;

// ── MIDDLEWARE ────────────────────────────────────────────────────────────────
app.use(helmet());
app.use(cors({
  origin: '*',          // In production restrict to your frontend URL
  methods: ['GET','POST','PUT','PATCH','DELETE','OPTIONS'],
  allowedHeaders: ['Content-Type','Authorization'],
}));
app.use(morgan(process.env.NODE_ENV === 'production' ? 'combined' : 'dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

// ── SWAGGER ───────────────────────────────────────────────────────────────────
const swaggerSpec = swaggerJsdoc({
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Ferretería API',
      version: '1.0.0',
      description: 'API REST — Sistema de Inventario y Ventas Ferretería\n\n' +
        '**Credenciales de prueba:**\n- Admin: `Aylin.H` / `admin123`\n- Vendedor: `Zaid.H` / `vend123`',
    },
    servers: [{ url: `http://localhost:${PORT}/api`, description: 'Servidor local' }],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
          description: 'Pega tu token obtenido de POST /auth/login',
        },
      },
    },
    security: [{ bearerAuth: [] }],
  },
  apis: ['./src/routes/*.js'],
});

app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec, {
  customSiteTitle: 'Ferretería API Docs',
  customCss: '.swagger-ui .topbar { background: #1a2340; }',
}));

// ── ROUTES ────────────────────────────────────────────────────────────────────
app.use('/api', routes);

// ── HEALTH CHECK ──────────────────────────────────────────────────────────────
app.get('/', (req, res) => {
  res.json({
    ok: true,
    message: 'Ferretería API corriendo 🔧',
    docs: `http://localhost:${PORT}/api-docs`,
    version: '1.0.0',
  });
});

// ── 404 ───────────────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({ ok: false, message: `Ruta no encontrada: ${req.method} ${req.path}` });
});

// ── ERROR HANDLER ─────────────────────────────────────────────────────────────
app.use((err, req, res, _next) => {
  console.error(err);
  res.status(500).json({ ok: false, message: 'Error interno del servidor' });
});

// ── START ─────────────────────────────────────────────────────────────────────
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`\n🔧 Ferretería API corriendo en http://localhost:${PORT}`);
    console.log(`📚 Documentación Swagger: http://localhost:${PORT}/api-docs\n`);
  });
}

module.exports = app; // for tests
