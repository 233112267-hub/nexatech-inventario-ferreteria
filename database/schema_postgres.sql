-- ============================================================
-- SISTEMA FERRETERÍA - ESQUEMA POSTGRESQL
-- Basado en el esquema original de Randy, ampliado con las
-- columnas/tabla que el backend necesita para mantener toda
-- la funcionalidad que ya tenía con la base provisional (SQLite).
-- ============================================================

-- Creación de la base de datos (Opcional)
-- CREATE DATABASE sistema_ventas;

-- ============================================================
-- 1. TABLA: ROLES
-- ============================================================
CREATE TABLE ROLES (
    id_rol SERIAL,
    nombre VARCHAR(50) NOT NULL,
    descripcion VARCHAR(255),
    CONSTRAINT PK_ROLES PRIMARY KEY (id_rol),
    CONSTRAINT UQ_ROLES_NOMBRE UNIQUE (nombre)
);

-- ============================================================
-- 2. TABLA: CATEGORIAS
-- ============================================================
CREATE TABLE CATEGORIAS (
    id_categoria SERIAL,
    nombre VARCHAR(100) NOT NULL,
    CONSTRAINT PK_CATEGORIAS PRIMARY KEY (id_categoria),
    CONSTRAINT UQ_CATEGORIAS_NOMBRE UNIQUE (nombre)
);

-- ============================================================
-- 3. TABLA: USUARIOS
-- (+ username, + updated_at -> requeridos por el backend/login)
-- ============================================================
CREATE TABLE USUARIOS (
    id_usuario SERIAL,
    id_rol INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT PK_USUARIOS PRIMARY KEY (id_usuario),
    CONSTRAINT UQ_USUARIOS_USERNAME UNIQUE (username),
    CONSTRAINT FK_USUARIOS_ROLES FOREIGN KEY (id_rol) REFERENCES ROLES(id_rol)
);

-- ============================================================
-- 4. TABLA: PRODUCTOS
-- (+ descripcion, + estado, + updated_at -> requeridos por el backend)
-- ============================================================
CREATE TABLE PRODUCTOS (
    id_producto SERIAL,
    id_categoria INT NOT NULL,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    descripcion VARCHAR(500),
    precio_compra NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    precio_venta NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    stock_actual INT NOT NULL DEFAULT 0,
    stock_minimo INT NOT NULL DEFAULT 0,
    estado VARCHAR(20) NOT NULL DEFAULT 'Activo'
           CHECK (estado IN ('Activo', 'Inactivo')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT PK_PRODUCTOS PRIMARY KEY (id_producto),
    CONSTRAINT FK_PRODUCTOS_CATEGORIAS FOREIGN KEY (id_categoria) REFERENCES CATEGORIAS(id_categoria)
);

-- ============================================================
-- 5. TABLA: MOVIMIENTOS_INVENTARIO
-- (+ referencia -> folio de venta o motivo del ajuste manual)
-- ============================================================
CREATE TABLE MOVIMIENTOS_INVENTARIO (
    id_movimiento SERIAL,
    id_producto INT NOT NULL,
    id_usuario INT NOT NULL,
    tipo_movimiento VARCHAR(20) NOT NULL, -- 'ENTRADA', 'SALIDA', 'AJUSTE'
    cantidad INT NOT NULL,
    stock_anterior INT NOT NULL,
    stock_nuevo INT NOT NULL,
    referencia VARCHAR(100),
    fecha_movimiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT PK_MOVIMIENTOS_INVENTARIO PRIMARY KEY (id_movimiento),
    CONSTRAINT FK_MOVIMIENTOS_PRODUCTOS FOREIGN KEY (id_producto) REFERENCES PRODUCTOS(id_producto),
    CONSTRAINT FK_MOVIMIENTOS_USUARIOS FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
);

-- ============================================================
-- 6. TABLA: VENTAS
-- (+ cliente, + descuento, + impuestos, + metodo_pago)
-- ============================================================
CREATE TABLE VENTAS (
    id_venta SERIAL,
    id_usuario INT NOT NULL,
    folio VARCHAR(50) NOT NULL UNIQUE,
    cliente VARCHAR(150),
    subtotal NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    descuento NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    impuestos NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    total NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    metodo_pago VARCHAR(20) NOT NULL DEFAULT 'Efectivo'
                CHECK (metodo_pago IN ('Efectivo', 'Tarjeta', 'Transferencia')),
    estado VARCHAR(20) NOT NULL DEFAULT 'Pagada'
           CHECK (estado IN ('Pagada', 'Pendiente', 'Cancelada')),
    fecha_venta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT PK_VENTAS PRIMARY KEY (id_venta),
    CONSTRAINT FK_VENTAS_USUARIOS FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
);

-- ============================================================
-- 7. TABLA: DETALLE_VENTAS
-- ============================================================
CREATE TABLE DETALLE_VENTAS (
    id_detalle SERIAL,
    id_venta INT NOT NULL,
    id_producto INT NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario NUMERIC(10, 2) NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    CONSTRAINT PK_DETALLE_VENTAS PRIMARY KEY (id_detalle),
    CONSTRAINT FK_DETALLE_VENTAS_VENTAS FOREIGN KEY (id_venta) REFERENCES VENTAS(id_venta) ON DELETE CASCADE,
    CONSTRAINT FK_DETALLE_VENTAS_PRODUCTOS FOREIGN KEY (id_producto) REFERENCES PRODUCTOS(id_producto)
);

-- ============================================================
-- 8. TABLA: ALERTAS (nueva, requerida por el módulo de Alertas)
-- ============================================================
CREATE TABLE ALERTAS (
    id_alerta SERIAL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('Critica', 'Advertencia', 'Informativa')),
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(500),
    id_producto INT,
    estado VARCHAR(20) NOT NULL DEFAULT 'Pendiente'
           CHECK (estado IN ('Pendiente', 'Resuelta')),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT PK_ALERTAS PRIMARY KEY (id_alerta),
    CONSTRAINT FK_ALERTAS_PRODUCTOS FOREIGN KEY (id_producto) REFERENCES PRODUCTOS(id_producto) ON DELETE CASCADE
);

-- ============================================================
-- ÍNDICES ÚTILES
-- ============================================================
CREATE INDEX IDX_PRODUCTOS_CATEGORIA ON PRODUCTOS(id_categoria);
CREATE INDEX IDX_VENTAS_USUARIO ON VENTAS(id_usuario);
CREATE INDEX IDX_DETALLE_VENTAS_VENTA ON DETALLE_VENTAS(id_venta);
CREATE INDEX IDX_MOVIMIENTOS_PRODUCTO ON MOVIMIENTOS_INVENTARIO(id_producto);
CREATE INDEX IDX_ALERTAS_PRODUCTO ON ALERTAS(id_producto);

-- ============================================================
-- DATOS INICIALES (seed) - Roles
-- ============================================================
INSERT INTO ROLES (nombre, descripcion) VALUES
    ('Administrador', 'Acceso total al sistema'),
    ('Vendedor', 'Puede registrar ventas y consultar inventario'),
    ('Almacenista', 'Gestiona productos, categorías y movimientos de inventario');

-- ============================================================
-- DATOS INICIALES (seed) - Categorías
-- ============================================================
INSERT INTO CATEGORIAS (nombre) VALUES
    ('Herramientas'), ('Ferretería'), ('Materiales'),
    ('Pintura'), ('Eléctricos'), ('Plomería'), ('Seguridad');

-- Nota: los usuarios y productos de prueba se insertan desde el script
-- seed.js de Node (usa bcrypt para los hashes de contraseña), no aquí.
