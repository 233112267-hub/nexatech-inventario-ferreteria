-- =====================================================================
-- SISTEMA FERRETERÍA - SCRIPT DE BASE DE DATOS (PostgreSQL / Neon)
-- Integrantes: Hernandez Espinosa Zaid Emanuel, Herrera Cruz Vielka Ailyn,
--              Lopez Lara Randy Noe, Gonzalez Lopez Jorge Saul
-- =====================================================================
-- Contenido:
--   1. Creación de tablas (con constraints de integridad)
--   2. Roles y permisos (Administrador, Vendedor, Almacenista)
--   3. Procedimientos almacenados
--   4. Triggers
--   5. Inserts de datos de prueba (20 registros variados por tabla clave)
--   6. Ejemplos de uso (comentados)
-- =====================================================================

-- =====================================================================
-- 1. CREACIÓN DE TABLAS
-- =====================================================================

CREATE TABLE surcusal (
    surcve       SERIAL PRIMARY KEY,
    estado       VARCHAR(50)  NOT NULL,
    municipio    VARCHAR(50)  NOT NULL,
    localidad    VARCHAR(50)  NOT NULL,
    referencia   VARCHAR(150),
    direccion    VARCHAR(200) NOT NULL
);

CREATE TABLE categoria (
    catcve       SERIAL PRIMARY KEY,
    nombre       VARCHAR(80)  NOT NULL,
    descripcion  VARCHAR(200),
    estatus      VARCHAR(20)  NOT NULL DEFAULT 'activo',
    fecha        DATE         NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE producto (
    procve                  SERIAL PRIMARY KEY,
    catcve                  INT NOT NULL REFERENCES categoria(catcve),
    descripcion             VARCHAR(255),
    estatus                 VARCHAR(20) NOT NULL DEFAULT 'activo',
    precio                  NUMERIC(10,2) NOT NULL CHECK (precio > 0),
    fecha                   DATE NOT NULL DEFAULT CURRENT_DATE,
    modelo                  VARCHAR(50),
    marca                   VARCHAR(50),
    informacion_adicional   VARCHAR(255),
    nombre                  VARCHAR(100) NOT NULL,
    color                   VARCHAR(30)
);

CREATE TABLE stock (
    stoccve       SERIAL PRIMARY KEY,
    procve        INT NOT NULL REFERENCES producto(procve),
    stock_actual  INT NOT NULL DEFAULT 0 CHECK (stock_actual >= 0),
    stock_minimo  INT NOT NULL DEFAULT 5 CHECK (stock_minimo >= 0),
    fecha         DATE NOT NULL DEFAULT CURRENT_DATE,
    estatus       VARCHAR(30) NOT NULL DEFAULT 'normal',
    descripcion   VARCHAR(150)
);

CREATE TABLE disponibilidad_producto (
    discve       SERIAL PRIMARY KEY,
    surcve       INT NOT NULL REFERENCES surcusal(surcve),
    procve       INT NOT NULL REFERENCES producto(procve),
    precio_local NUMERIC(10,2) NOT NULL CHECK (precio_local > 0),
    disponible   BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_alta   DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (surcve, procve)
);

CREATE TABLE empleado (
    empcve          SERIAL PRIMARY KEY,
    surcve          INT NOT NULL REFERENCES surcusal(surcve),
    stocve          INT REFERENCES stock(stoccve),
    nombre          VARCHAR(60) NOT NULL,
    apellidopaterno VARCHAR(60) NOT NULL,
    apellidomaterno VARCHAR(60),
    rol             VARCHAR(20) NOT NULL CHECK (rol IN ('Administrador','Vendedor')),
    descripcion     VARCHAR(150),
    estatus         VARCHAR(20) NOT NULL DEFAULT 'activo',
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(100) NOT NULL UNIQUE,
    password        VARCHAR(255) NOT NULL,
    fecha           DATE NOT NULL DEFAULT CURRENT_DATE,
    direccion       VARCHAR(200),
    codigopostal    VARCHAR(10),
    reset_token          VARCHAR(64),
    reset_token_expira   TIMESTAMP
);

CREATE TABLE cliente (
    clicve          SERIAL PRIMARY KEY,
    nombre          VARCHAR(60) NOT NULL,
    apellidopaterno VARCHAR(60) NOT NULL,
    apellidomaterno VARCHAR(60),
    telefono        VARCHAR(15),
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(100) NOT NULL UNIQUE,
    password        VARCHAR(255) NOT NULL,
    fecha           DATE NOT NULL DEFAULT CURRENT_DATE,
    direccion       VARCHAR(200),
    codigopostal    VARCHAR(10),
    membresia       VARCHAR(20) DEFAULT 'basica',
    estatus         VARCHAR(20) NOT NULL DEFAULT 'activo',
    reset_token          VARCHAR(64),
    reset_token_expira   TIMESTAMP
);

CREATE TABLE venta (
    vencve            SERIAL PRIMARY KEY,
    empcve            INT NOT NULL REFERENCES empleado(empcve),
    clicve            INT REFERENCES cliente(clicve),
    total             NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (total >= 0),
    subtotal          NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    descripcion       VARCHAR(150),
    estatus           VARCHAR(20) NOT NULL DEFAULT 'completada',
    metodo_pago       VARCHAR(20) NOT NULL DEFAULT 'efectivo',
    tipo_entrega      VARCHAR(20) NOT NULL DEFAULT 'mostrador' CHECK (tipo_entrega IN ('mostrador','domicilio')),
    direccion_entrega VARCHAR(200),
    codigo_postal     VARCHAR(10),
    fecha             DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE detalle_venta (
    detcve      SERIAL PRIMARY KEY,
    procve      INT NOT NULL REFERENCES producto(procve),
    vencve      INT NOT NULL REFERENCES venta(vencve),
    fecha       DATE NOT NULL DEFAULT CURRENT_DATE,
    cantidad    INT NOT NULL CHECK (cantidad > 0),
    precio      NUMERIC(10,2) NOT NULL CHECK (precio > 0),
    subtotal    NUMERIC(10,2) NOT NULL CHECK (subtotal >= 0),
    descuento   NUMERIC(10,2) DEFAULT 0,
    estatus     VARCHAR(20) NOT NULL DEFAULT 'activo',
    modalidad   VARCHAR(20) DEFAULT 'normal' CHECK (modalidad IN ('normal','2x1','3x1'))
);

CREATE INDEX idx_producto_categoria ON producto(catcve);
CREATE INDEX idx_venta_empleado ON venta(empcve);
CREATE INDEX idx_venta_cliente ON venta(clicve);
CREATE INDEX idx_detalle_venta_venta ON detalle_venta(vencve);
CREATE INDEX idx_detalle_venta_producto ON detalle_venta(procve);