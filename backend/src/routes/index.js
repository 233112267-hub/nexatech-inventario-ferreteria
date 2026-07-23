const express = require('express');
const router  = express.Router();

const { authMiddleware, roleMiddleware } = require('../middleware/auth');

const authCtrl      = require('../controllers/authController');
const usuariosCtrl  = require('../controllers/usuariosController');
const productosCtrl = require('../controllers/productosController');
const ventasCtrl    = require('../controllers/ventasController');
const { movimientos, alertas, categorias, dashboard } = require('../controllers/otrosControllers');

// ── AUTH ──────────────────────────────────────────────────────────────────────
/**
 * @swagger
 * /auth/login:
 *   post:
 *     tags: [Auth]
 *     summary: Iniciar sesión y obtener JWT
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [usuario, password]
 *             properties:
 *               usuario:  { type: string, example: "Aylin.H" }
 *               password: { type: string, example: "admin123" }
 *     responses:
 *       200: { description: "Login exitoso, retorna token JWT" }
 *       401: { description: "Credenciales incorrectas" }
 */
router.post('/auth/login', authCtrl.login);

/**
 * @swagger
 * /auth/me:
 *   get:
 *     tags: [Auth]
 *     summary: Obtener perfil del usuario autenticado
 *     security: [{ bearerAuth: [] }]
 *     responses:
 *       200: { description: "Datos del usuario" }
 *       401: { description: "Token inválido" }
 */
router.get('/auth/me', authMiddleware, authCtrl.me);

/**
 * @swagger
 * /auth/change-password:
 *   post:
 *     tags: [Auth]
 *     summary: Cambiar contraseña
 *     security: [{ bearerAuth: [] }]
 */
router.post('/auth/change-password', authMiddleware, authCtrl.changePassword);

// ── DASHBOARD ─────────────────────────────────────────────────────────────────
/**
 * @swagger
 * /dashboard/stats:
 *   get:
 *     tags: [Dashboard]
 *     summary: KPIs generales del sistema
 *     security: [{ bearerAuth: [] }]
 */
router.get('/dashboard/stats', authMiddleware, dashboard.stats);
router.get('/dashboard/ventas-semana', authMiddleware, dashboard.ventasSemana);

// ── USUARIOS ──────────────────────────────────────────────────────────────────
/**
 * @swagger
 * /usuarios:
 *   get:
 *     tags: [Usuarios]
 *     summary: Listar usuarios (paginado, filtros)
 *     security: [{ bearerAuth: [] }]
 *     parameters:
 *       - { in: query, name: search, schema: { type: string } }
 *       - { in: query, name: rol,    schema: { type: string, enum: [Administrador, Vendedor, Almacenista] } }
 *       - { in: query, name: estado, schema: { type: string, enum: [Activo, Inactivo] } }
 *       - { in: query, name: page,   schema: { type: integer, default: 1 } }
 *       - { in: query, name: limit,  schema: { type: integer, default: 10 } }
 */
router.get('/usuarios',    authMiddleware, roleMiddleware('Administrador'), usuariosCtrl.getAll);
router.get('/usuarios/vendedores', authMiddleware, roleMiddleware('Administrador','Vendedor'), usuariosCtrl.vendedores);
router.get('/usuarios/:id',authMiddleware, roleMiddleware('Administrador'), usuariosCtrl.getOne);
router.post('/usuarios',   authMiddleware, roleMiddleware('Administrador'), usuariosCtrl.create);
router.put('/usuarios/:id',authMiddleware, roleMiddleware('Administrador'), usuariosCtrl.update);
router.patch('/usuarios/:id',authMiddleware, roleMiddleware('Administrador'), usuariosCtrl.update);
router.delete('/usuarios/:id', authMiddleware, roleMiddleware('Administrador'), usuariosCtrl.remove);

// ── CATEGORÍAS ────────────────────────────────────────────────────────────────
/**
 * @swagger
 * /categorias:
 *   get:
 *     tags: [Categorias]
 *     summary: Listar todas las categorías con conteo de productos
 *     security: [{ bearerAuth: [] }]
 */
router.get('/categorias',       authMiddleware, categorias.getAll);
router.post('/categorias',      authMiddleware, roleMiddleware('Administrador','Almacenista'), categorias.create);
router.delete('/categorias/:id',authMiddleware, roleMiddleware('Administrador'), categorias.remove);

// ── PRODUCTOS ─────────────────────────────────────────────────────────────────
/**
 * @swagger
 * /productos:
 *   get:
 *     tags: [Productos]
 *     summary: Listar productos (paginado, filtros)
 *     security: [{ bearerAuth: [] }]
 *     parameters:
 *       - { in: query, name: search,    schema: { type: string } }
 *       - { in: query, name: categoria, schema: { type: string } }
 *       - { in: query, name: estado,    schema: { type: string, enum: [Activo, Inactivo] } }
 *       - { in: query, name: page,      schema: { type: integer, default: 1 } }
 *       - { in: query, name: limit,     schema: { type: integer, default: 10 } }
 */
router.get('/productos/stock-bajo', authMiddleware, productosCtrl.stockBajo);
router.get('/productos',            authMiddleware, productosCtrl.getAll);
router.get('/productos/:id',        authMiddleware, productosCtrl.getOne);
router.post('/productos',           authMiddleware, roleMiddleware('Administrador','Almacenista'), productosCtrl.create);
router.put('/productos/:id',        authMiddleware, roleMiddleware('Administrador','Almacenista'), productosCtrl.update);
router.patch('/productos/:id',      authMiddleware, roleMiddleware('Administrador','Almacenista'), productosCtrl.update);
router.delete('/productos/:id',     authMiddleware, roleMiddleware('Administrador'), productosCtrl.remove);

// ── VENTAS ────────────────────────────────────────────────────────────────────
/**
 * @swagger
 * /ventas:
 *   post:
 *     tags: [Ventas]
 *     summary: Registrar una nueva venta
 *     security: [{ bearerAuth: [] }]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [items]
 *             properties:
 *               cliente:     { type: string }
 *               metodo_pago: { type: string, enum: [Efectivo, Tarjeta, Transferencia] }
 *               descuento:   { type: number }
 *               items:
 *                 type: array
 *                 items:
 *                   type: object
 *                   properties:
 *                     producto_id: { type: integer }
 *                     cantidad:    { type: integer }
 */
router.get('/ventas',             authMiddleware, ventasCtrl.getAll);
router.get('/ventas/:id',         authMiddleware, ventasCtrl.getOne);
router.post('/ventas',            authMiddleware, roleMiddleware('Administrador','Vendedor'), ventasCtrl.create);
router.patch('/ventas/:id/cancelar', authMiddleware, roleMiddleware('Administrador'), ventasCtrl.cancelar);

// ── MOVIMIENTOS ───────────────────────────────────────────────────────────────
/**
 * @swagger
 * /movimientos:
 *   get:
 *     tags: [Movimientos]
 *     summary: Historial de movimientos de inventario
 *     security: [{ bearerAuth: [] }]
 */
router.get('/movimientos',  authMiddleware, movimientos.getAll);
router.post('/movimientos', authMiddleware, roleMiddleware('Administrador','Almacenista'), movimientos.create);

// ── ALERTAS ───────────────────────────────────────────────────────────────────
/**
 * @swagger
 * /alertas:
 *   get:
 *     tags: [Alertas]
 *     summary: Listar alertas del sistema
 *     security: [{ bearerAuth: [] }]
 */
router.get('/alertas',                  authMiddleware, alertas.getAll);
/**
 * @swagger
 * /alertas/{id}/notificar:
 *   post:
 *     tags: [Alertas]
 *     summary: Reenviar por correo la notificación de una alerta a los administradores
 *     security: [{ bearerAuth: [] }]
 *     parameters:
 *       - { in: path, name: id, required: true, schema: { type: integer } }
 */
router.post('/alertas/:id/notificar',   authMiddleware, alertas.notificar);
router.patch('/alertas/:id/resolver',   authMiddleware, alertas.resolver);

module.exports = router;