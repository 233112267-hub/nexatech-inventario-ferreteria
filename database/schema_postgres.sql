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


-- =====================================================================
-- 2. ROLES Y PERMISOS
-- =====================================================================
-- NOTA: cambia las contraseñas antes de usar esto en un entorno real.

DROP ROLE IF EXISTS administrador;
DROP ROLE IF EXISTS vendedor;


-- Solo quedan 2 roles de base de datos. El administrador absorbe el control de stock
CREATE ROLE administrador LOGIN PASSWORD 'Adm1n_Ferr2026!';
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO administrador;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO administrador;

CREATE ROLE vendedor LOGIN PASSWORD 'Vend_Ferr2026!';
GRANT SELECT ON producto, categoria, cliente, disponibilidad_producto, stock TO vendedor;
GRANT SELECT, INSERT, UPDATE ON venta, detalle_venta TO vendedor;
GRANT USAGE, SELECT ON venta_vencve_seq, detalle_venta_detcve_seq, cliente_clicve_seq TO vendedor;
GRANT INSERT ON cliente TO vendedor; -- puede dar de alta clientes nuevos en mostrador

-- Permiso de ejecución de procedimientos según rol (se otorgan después de crearlos, ver sección 3)


-- =====================================================================
-- 3. PROCEDIMIENTOS ALMACENADOS
-- =====================================================================

-- 3.1 Limpieza de descuentos: convierte descuento = 0 a NULL (mantenimiento manual/batch)
CREATE OR REPLACE PROCEDURE sp_limpiar_descuentos()
LANGUAGE plpgsql
AS $$
DECLARE
    v_filas INT;
BEGIN
    UPDATE detalle_venta
    SET descuento = NULL
    WHERE descuento = 0;

    GET DIAGNOSTICS v_filas = ROW_COUNT;
    RAISE NOTICE 'Limpieza completada: % registro(s) con descuento en 0 fueron actualizados a NULL', v_filas;
END;
$$;

-- 3.2 Aplicar descuento o promoción a una línea de detalle_venta
--     tipo: 'porcentaje' (requiere p_valor entre 0 y 100), '2x1', '3x1'
--     Si no se cumple el requisito de cantidad, NO se aplica ningún cambio.
CREATE OR REPLACE PROCEDURE sp_aplicar_descuento(
    p_detcve INT,
    p_tipo   VARCHAR,
    p_valor  NUMERIC DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_cantidad          INT;
    v_precio            NUMERIC(10,2);
    v_nuevo_subtotal    NUMERIC(10,2);
    v_descuento_monto   NUMERIC(10,2);
    v_unidades_pagadas  INT;
BEGIN
    SELECT cantidad, precio INTO v_cantidad, v_precio
    FROM detalle_venta WHERE detcve = p_detcve;

    IF NOT FOUND THEN
        RAISE NOTICE 'El detalle de venta % no existe', p_detcve;
        RETURN;
    END IF;

    IF p_tipo = 'porcentaje' THEN
        IF p_valor IS NULL OR p_valor <= 0 OR p_valor >= 100 THEN
            RAISE NOTICE 'Porcentaje inválido (%), no se aplica ningún descuento', p_valor;
            RETURN;
        END IF;
        v_descuento_monto := ROUND(v_precio * v_cantidad * (p_valor / 100), 2);
        v_nuevo_subtotal   := ROUND((v_precio * v_cantidad) - v_descuento_monto, 2);

        UPDATE detalle_venta
        SET subtotal = v_nuevo_subtotal, descuento = v_descuento_monto, modalidad = 'normal'
        WHERE detcve = p_detcve;
        RAISE NOTICE 'Descuento de %%% aplicado al detalle %. Nuevo subtotal: %', p_valor, p_detcve, v_nuevo_subtotal;

    ELSIF p_tipo = '2x1' THEN
        IF v_cantidad < 2 THEN
            RAISE NOTICE 'No se cumple el requisito de cantidad mínima (2) para la promoción 2x1. No se aplica cambio.';
            RETURN;
        END IF;
        v_unidades_pagadas := v_cantidad - FLOOR(v_cantidad::NUMERIC / 2)::INT;
        v_nuevo_subtotal   := ROUND(v_precio * v_unidades_pagadas, 2);
        v_descuento_monto  := ROUND((v_precio * v_cantidad) - v_nuevo_subtotal, 2);

        UPDATE detalle_venta
        SET subtotal = v_nuevo_subtotal, descuento = v_descuento_monto, modalidad = '2x1'
        WHERE detcve = p_detcve;
        RAISE NOTICE 'Promoción 2x1 aplicada al detalle %. Nuevo subtotal: %', p_detcve, v_nuevo_subtotal;

    ELSIF p_tipo = '3x1' THEN
        IF v_cantidad < 3 THEN
            RAISE NOTICE 'No se cumple el requisito de cantidad mínima (3) para la promoción 3x1. No se aplica cambio.';
            RETURN;
        END IF;
        v_unidades_pagadas := v_cantidad - (FLOOR(v_cantidad::NUMERIC / 3)::INT * 2);
        v_nuevo_subtotal   := ROUND(v_precio * v_unidades_pagadas, 2);
        v_descuento_monto  := ROUND((v_precio * v_cantidad) - v_nuevo_subtotal, 2);

        UPDATE detalle_venta
        SET subtotal = v_nuevo_subtotal, descuento = v_descuento_monto, modalidad = '3x1'
        WHERE detcve = p_detcve;
        RAISE NOTICE 'Promoción 3x1 aplicada al detalle %. Nuevo subtotal: %', p_detcve, v_nuevo_subtotal;

    ELSE
        RAISE NOTICE 'Tipo de descuento no reconocido: %. Use porcentaje, 2x1 o 3x1.', p_tipo;
    END IF;
END;
$$;

-- 3.3 Disminuir stock (venta / salida de producto). Marca alerta si queda bajo el mínimo.
CREATE OR REPLACE PROCEDURE sp_disminuir_stock(p_procve INT, p_cantidad INT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_actual  INT;
    v_minimo  INT;
    v_nuevo   INT;
BEGIN
    SELECT stock_actual, stock_minimo INTO v_actual, v_minimo
    FROM stock WHERE procve = p_procve;

    IF NOT FOUND THEN
        RAISE NOTICE 'No existe registro de stock para el producto %', p_procve;
        RETURN;
    END IF;

    IF v_actual < p_cantidad THEN
        RAISE EXCEPTION 'Stock insuficiente para el producto % (disponible: %, solicitado: %)', p_procve, v_actual, p_cantidad;
    END IF;

    v_nuevo := v_actual - p_cantidad;

    IF v_nuevo < v_minimo THEN
        UPDATE stock
        SET stock_actual = v_nuevo,
            estatus = 'alerta',
            descripcion = 'Stock bajo el mínimo, reabastecer pronto',
            fecha = CURRENT_DATE
        WHERE procve = p_procve;
    ELSE
        UPDATE stock
        SET stock_actual = v_nuevo,
            estatus = 'normal',
            descripcion = NULL,
            fecha = CURRENT_DATE
        WHERE procve = p_procve;
    END IF;
END;
$$;

-- 3.4 Abastecer stock (reabastecimiento). Quita la alerta si vuelve a estar por arriba del mínimo.
CREATE OR REPLACE PROCEDURE sp_abastecer_stock(p_procve INT, p_cantidad INT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_actual INT;
    v_minimo INT;
    v_nuevo  INT;
BEGIN
    SELECT stock_actual, stock_minimo INTO v_actual, v_minimo
    FROM stock WHERE procve = p_procve;

    IF NOT FOUND THEN
        RAISE NOTICE 'No existe registro de stock para el producto %', p_procve;
        RETURN;
    END IF;

    v_nuevo := v_actual + p_cantidad;

    IF v_nuevo >= v_minimo THEN
        UPDATE stock
        SET stock_actual = v_nuevo, estatus = 'normal', descripcion = NULL, fecha = CURRENT_DATE
        WHERE procve = p_procve;
    ELSE
        UPDATE stock
        SET stock_actual = v_nuevo,
            estatus = 'alerta',
            descripcion = 'Stock bajo el mínimo, reabastecer pronto',
            fecha = CURRENT_DATE
        WHERE procve = p_procve;
    END IF;
END;
$$;
-- 3.5 Generar token de recuperación de contraseña (empleado o cliente)
--     El token es de un solo uso y expira en 1 hora. p_tipo: 'empleado' o 'cliente'.
--     El backend debe enviar p_token por correo (API externa) al usuario, nunca mostrarlo en pantalla.
--     p_resultado devuelve: 'OK', 'TIPO_INVALIDO', 'USUARIO_NO_ENCONTRADO', 'NO_AUTORIZADO'
--     SECURITY DEFINER: corre con privilegios del dueño porque vendedor no tiene UPDATE
--     directo sobre empleado; el control de acceso real está en el IF de current_user.
CREATE OR REPLACE PROCEDURE sp_generar_token_reset(
    IN  p_tipo       VARCHAR,
    IN  p_email      VARCHAR,
    OUT p_token      VARCHAR,
    OUT p_resultado  VARCHAR
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_token VARCHAR(64);
BEGIN
    IF p_tipo NOT IN ('empleado', 'cliente') THEN
        p_token := NULL;
        p_resultado := 'TIPO_INVALIDO';
        RETURN;
    END IF;

    -- Vendedor solo puede generar tokens para clientes, nunca para empleados
    IF current_user = 'vendedor' AND p_tipo = 'empleado' THEN
        p_token := NULL;
        p_resultado := 'NO_AUTORIZADO';
        RETURN;
    END IF;

    v_token := md5(random()::text || clock_timestamp()::text);

    IF p_tipo = 'empleado' THEN
        UPDATE empleado
        SET reset_token = v_token, reset_token_expira = CURRENT_TIMESTAMP + INTERVAL '1 hour'
        WHERE email = p_email;
    ELSE
        UPDATE cliente
        SET reset_token = v_token, reset_token_expira = CURRENT_TIMESTAMP + INTERVAL '1 hour'
        WHERE email = p_email;
    END IF;

    IF NOT FOUND THEN
        p_token := NULL;
        p_resultado := 'USUARIO_NO_ENCONTRADO';
        RETURN;
    END IF;

    p_token := v_token;
    p_resultado := 'OK';
END;
$$;

-- 3.6 Restablecer contraseña usando el token generado
--     p_nueva_password debe llegar ya hasheada (bcrypt) desde el backend, nunca en texto plano.
--     p_resultado devuelve: 'OK', 'TIPO_INVALIDO', 'TOKEN_INVALIDO', 'TOKEN_EXPIRADO', 'NO_AUTORIZADO'
CREATE OR REPLACE PROCEDURE sp_restablecer_password(
    IN  p_tipo            VARCHAR,
    IN  p_token           VARCHAR,
    IN  p_nueva_password  VARCHAR,
    OUT p_resultado       VARCHAR
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_expira TIMESTAMP;
BEGIN
    IF p_tipo NOT IN ('empleado', 'cliente') THEN
        p_resultado := 'TIPO_INVALIDO';
        RETURN;
    END IF;

    IF current_user = 'vendedor' AND p_tipo = 'empleado' THEN
        p_resultado := 'NO_AUTORIZADO';
        RETURN;
    END IF;

    IF p_tipo = 'empleado' THEN
        SELECT reset_token_expira INTO v_expira FROM empleado WHERE reset_token = p_token;
    ELSE
        SELECT reset_token_expira INTO v_expira FROM cliente WHERE reset_token = p_token;
    END IF;

    IF NOT FOUND THEN
        p_resultado := 'TOKEN_INVALIDO';
        RETURN;
    END IF;

    IF v_expira < CURRENT_TIMESTAMP THEN
        p_resultado := 'TOKEN_EXPIRADO';
        RETURN;
    END IF;

    IF p_tipo = 'empleado' THEN
        UPDATE empleado
        SET password = p_nueva_password, reset_token = NULL, reset_token_expira = NULL
        WHERE reset_token = p_token;
    ELSE
        UPDATE cliente
        SET password = p_nueva_password, reset_token = NULL, reset_token_expira = NULL
        WHERE reset_token = p_token;
    END IF;

    p_resultado := 'OK';
END;
$$;
-- 3.7 Eliminar producto: soft delete (estatus = 'inactivo'), nunca borra la fila física.
--     Esto preserva la categoría, el stock, la disponibilidad y el historial de ventas intactos.
--     p_resultado devuelve: 'OK', 'PRODUCTO_NO_ENCONTRADO', 'YA_INACTIVO'
CREATE OR REPLACE PROCEDURE sp_eliminar_producto(
    IN  p_procve     INT,
    OUT p_resultado  VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_estatus_actual VARCHAR(20);
BEGIN
    SELECT estatus INTO v_estatus_actual
    FROM producto WHERE procve = p_procve;

    IF NOT FOUND THEN
        p_resultado := 'PRODUCTO_NO_ENCONTRADO';
        RETURN;
    END IF;

    IF v_estatus_actual = 'inactivo' THEN
        p_resultado := 'YA_INACTIVO';
        RETURN;
    END IF;

    UPDATE producto
    SET estatus = 'inactivo'
    WHERE procve = p_procve;

    -- También lo marcamos como no disponible en todas las sucursales
    UPDATE disponibilidad_producto
    SET disponible = FALSE
    WHERE procve = p_procve;

    p_resultado := 'OK';
END;
$$;
-- Permisos de ejecución por rol
GRANT EXECUTE ON PROCEDURE sp_aplicar_descuento(INT, VARCHAR, NUMERIC) TO vendedor, administrador;
GRANT EXECUTE ON PROCEDURE sp_disminuir_stock(INT, INT) TO administrador;
GRANT EXECUTE ON PROCEDURE sp_abastecer_stock(INT, INT) TO administrador;
GRANT EXECUTE ON PROCEDURE sp_limpiar_descuentos() TO administrador;
GRANT EXECUTE ON PROCEDURE sp_eliminar_producto(INT, VARCHAR) TO administrador;
-- Firmas actualizadas: ahora con OUT p_resultado
GRANT EXECUTE ON PROCEDURE sp_generar_token_reset(VARCHAR, VARCHAR, VARCHAR, VARCHAR) TO vendedor, administrador;
GRANT EXECUTE ON PROCEDURE sp_restablecer_password(VARCHAR, VARCHAR, VARCHAR, VARCHAR) TO vendedor, administrador;
-- vendedor puede ejecutarlos porque en mostrador puede necesitar ayudar a un cliente a recuperar su acceso;


-- =====================================================================
-- 4. TRIGGERS
-- =====================================================================

-- 4.1 Normaliza el descuento a NULL automáticamente cuando llega en 0
--     (complementa al sp_limpiar_descuentos, que sirve para limpiar datos ya existentes)
CREATE OR REPLACE FUNCTION trg_fn_normalizar_descuento()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.descuento = 0 THEN
        NEW.descuento := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_normalizar_descuento
BEFORE INSERT OR UPDATE ON detalle_venta
FOR EACH ROW EXECUTE FUNCTION trg_fn_normalizar_descuento();

-- 4.2 Al insertar una línea de venta, descuenta automáticamente el stock del producto
CREATE OR REPLACE FUNCTION trg_fn_detalle_venta_stock()
RETURNS TRIGGER AS $$
BEGIN
    CALL sp_disminuir_stock(NEW.procve, NEW.cantidad);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_detalle_venta_stock
AFTER INSERT ON detalle_venta
FOR EACH ROW EXECUTE FUNCTION trg_fn_detalle_venta_stock();

-- 4.3 Recalcula automáticamente el total/subtotal de VENTA cuando cambian sus líneas
CREATE OR REPLACE FUNCTION trg_fn_actualizar_total_venta()
RETURNS TRIGGER AS $$
DECLARE
    v_vencve INT;
    v_suma   NUMERIC(10,2);
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_vencve := OLD.vencve;
    ELSE
        v_vencve := NEW.vencve;
    END IF;

    SELECT COALESCE(SUM(subtotal), 0) INTO v_suma
    FROM detalle_venta WHERE vencve = v_vencve;

    UPDATE venta
    SET subtotal = v_suma, total = v_suma
    WHERE vencve = v_vencve;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_actualizar_total_venta
AFTER INSERT OR UPDATE OR DELETE ON detalle_venta
FOR EACH ROW EXECUTE FUNCTION trg_fn_actualizar_total_venta();


-- =====================================================================
-- 5. INSERTS DE DATOS DE PRUEBA
-- =====================================================================

-- 5.1 SURCUSAL (5 sucursales en Hidalgo)
INSERT INTO surcusal (estado, municipio, localidad, referencia, direccion) VALUES
('Hidalgo', 'Pachuca de Soto', 'Centro',        'Frente a la plaza principal',        'Av. Juárez 120, Centro'),
('Hidalgo', 'Tulancingo',      'Centro',        'Junto a la central de abastos',      'Blvd. Reforma 45'),
('Hidalgo', 'Tizayuca',        'Ampliación',    'A dos cuadras de la caseta',         'Carretera México-Pachuca km 34'),
('Hidalgo', 'Ixmiquilpan',     'Centro',        'Cerca del mercado municipal',         'Calle Hidalgo 210'),
('Hidalgo', 'Huejutla',        'San Miguelito',  'A un costado de la gasolinera',      'Av. Independencia 88');

-- 5.2 CATEGORIA (8 categorías)
INSERT INTO categoria (nombre, descripcion, estatus, fecha) VALUES
('Herramientas manuales', 'Martillos, desarmadores, llaves', 'activo', '2025-01-10'),
('Herramientas eléctricas', 'Taladros, rotomartillos, esmeriles', 'activo', '2025-01-10'),
('Plomería', 'Tubería, conexiones, llaves de paso', 'activo', '2025-01-15'),
('Electricidad', 'Cables, contactos, apagadores', 'activo', '2025-02-01'),
('Pintura', 'Pinturas, brochas, rodillos, solventes', 'activo', '2025-02-05'),
('Ferretería general', 'Tornillería, clavos, adhesivos', 'activo', '2025-02-10'),
('Jardinería', 'Mangueras, palas, tijeras de podar', 'activo', '2025-03-01'),
('Seguridad industrial', 'Guantes, cascos, lentes de protección', 'activo', '2025-03-05');

-- 5.3 PRODUCTO (20 productos variados, precios NOT NULL)
INSERT INTO producto (catcve, descripcion, estatus, precio, fecha, modelo, marca, informacion_adicional, nombre, color) VALUES
(1, 'Martillo de uña con mango de fibra de vidrio', 'activo', 185.00, '2025-01-12', 'MF-16', 'Truper', 'Cabeza forjada, 16 oz', 'Martillo de uña', 'Negro'),
(1, 'Juego de desarmadores de precisión', 'activo', 249.50, '2025-01-12', 'DP-06', 'Pretul', 'Incluye estuche de 6 piezas', 'Juego de desarmadores', 'Rojo'),
(1, 'Llave ajustable de 10 pulgadas', 'activo', 165.00, '2025-01-13', 'LA-10', 'Urrea', 'Acero al cromo vanadio', 'Llave perico', 'Plateado'),
(2, 'Taladro percutor de 1/2 pulgada', 'activo', 1250.00, '2025-01-20', 'TP-500', 'Bosch', 'Incluye maletín y dos brocas', 'Taladro percutor', 'Azul'),
(2, 'Esmeril angular de 4.5 pulgadas', 'activo', 890.00, '2025-01-20', 'EA-115', 'Makita', 'Potencia 720W', 'Esmeril angular', 'Verde'),
(2, 'Rotomartillo SDS Plus', 'activo', 2450.00, '2025-01-22', 'RM-800', 'DeWalt', 'Incluye 3 brocas SDS', 'Rotomartillo', 'Amarillo'),
(3, 'Tubo PVC hidráulico 1/2 pulgada, 6m', 'activo', 95.00, '2025-02-01', 'PVC-12', 'Rotoplas', 'Cédula 40', 'Tubo PVC', 'Blanco'),
(3, 'Llave de paso de bola 1/2 pulgada', 'activo', 68.00, '2025-02-01', 'LB-12', 'Foset', 'Cuerpo de bronce', 'Llave de paso', 'Dorado'),
(3, 'Codo PVC 90 grados 1/2 pulgada', 'activo', 8.50, '2025-02-02', 'CP-90', 'Rotoplas', 'Paquete con 10 piezas', 'Codo PVC', 'Blanco'),
(4, 'Rollo de cable THW calibre 12, 100m', 'activo', 1180.00, '2025-02-10', 'THW-12', 'Condumex', 'Color negro, uso rudo', 'Cable THW', 'Negro'),
(4, 'Apagador sencillo con placa', 'activo', 35.00, '2025-02-10', 'AS-01', 'Volteck', 'Incluye placa atornillable', 'Apagador sencillo', 'Blanco'),
(4, 'Contacto doble polarizado', 'activo', 42.00, '2025-02-11', 'CD-02', 'Volteck', 'Con tierra física', 'Contacto doble', 'Blanco'),
(5, 'Pintura vinílica interior 4 litros', 'activo', 385.00, '2025-02-15', 'PV-4L', 'Comex', 'Cubre hasta 36m2', 'Pintura vinílica', 'Blanco'),
(5, 'Brocha de cerdas naturales 3 pulgadas', 'activo', 55.00, '2025-02-16', 'BC-3', 'Ancla', 'Mango de madera', 'Brocha', 'Café'),
(5, 'Rodillo para pintura 9 pulgadas', 'activo', 62.00, '2025-02-16', 'RP-9', 'Ancla', 'Felpa de 9mm', 'Rodillo', 'Amarillo'),
(6, 'Caja de tornillos para madera 1 pulgada', 'activo', 45.00, '2025-03-01', 'TM-1', 'Truper', 'Caja con 500 piezas', 'Tornillos madera', 'Dorado'),
(6, 'Caja de clavos de 2 pulgadas', 'activo', 38.00, '2025-03-01', 'CL-2', 'Truper', 'Caja de 1kg', 'Clavos', 'Plateado'),
(6, 'Pegamento en resistol 850g', 'activo', 78.00, '2025-03-02', 'RS-850', 'Resistol', 'Uso industrial', 'Pegamento blanco', 'Blanco'),
(7, 'Manguera para jardín 15 metros', 'activo', 245.00, '2025-03-10', 'MJ-15', 'Truper', 'Con conectores incluidos', 'Manguera de jardín', 'Verde'),
(8, 'Guantes de carnaza para trabajo pesado', 'activo', 95.00, '2025-03-12', 'GC-01', 'Steelpro', 'Talla única, refuerzo en palma', 'Guantes de carnaza', 'Café');

-- 5.4 STOCK (uno por producto, con stock generoso para las ventas de prueba)
INSERT INTO stock (procve, stock_actual, stock_minimo, fecha, estatus, descripcion) VALUES
(1, 80, 10, '2025-07-01', 'normal', NULL),
(2, 60, 10, '2025-07-01', 'normal', NULL),
(3, 70, 10, '2025-07-01', 'normal', NULL),
(4, 25, 5,  '2025-07-01', 'normal', NULL),
(5, 30, 5,  '2025-07-01', 'normal', NULL),
(6, 15, 5,  '2025-07-01', 'normal', NULL),
(7, 150, 20, '2025-07-01', 'normal', NULL),
(8, 90, 15, '2025-07-01', 'normal', NULL),
(9, 300, 50, '2025-07-01', 'normal', NULL),
(10, 20, 5, '2025-07-01', 'normal', NULL),
(11, 200, 30, '2025-07-01', 'normal', NULL),
(12, 180, 30, '2025-07-01', 'normal', NULL),
(13, 40, 10, '2025-07-01', 'normal', NULL),
(14, 100, 20, '2025-07-01', 'normal', NULL),
(15, 90, 20, '2025-07-01', 'normal', NULL),
(16, 60, 15, '2025-07-01', 'normal', NULL),
(17, 55, 15, '2025-07-01', 'normal', NULL),
(18, 45, 10, '2025-07-01', 'normal', NULL),
(19, 35, 8,  '2025-07-01', 'normal', NULL),
(20, 70, 15, '2025-07-01', 'normal', NULL);

-- 5.5 DISPONIBILIDAD_PRODUCTO (distribuye los 20 productos entre las 5 sucursales)
INSERT INTO disponibilidad_producto (surcve, procve, precio_local, disponible, fecha_alta) VALUES
(1, 1, 185.00, TRUE, '2025-01-15'), (1, 2, 249.50, TRUE, '2025-01-15'), (1, 3, 165.00, TRUE, '2025-01-15'), (1, 4, 1250.00, TRUE, '2025-01-20'),
(2, 5, 890.00, TRUE, '2025-01-20'), (2, 6, 2450.00, TRUE, '2025-01-22'), (2, 7, 95.00, TRUE, '2025-02-03'), (2, 8, 68.00, TRUE, '2025-02-03'),
(3, 9, 8.50, TRUE, '2025-02-05'), (3, 10, 1180.00, TRUE, '2025-02-12'), (3, 11, 35.00, TRUE, '2025-02-12'), (3, 12, 42.00, TRUE, '2025-02-12'),
(4, 13, 385.00, TRUE, '2025-02-18'), (4, 14, 55.00, TRUE, '2025-02-18'), (4, 15, 62.00, TRUE, '2025-02-18'), (4, 16, 45.00, TRUE, '2025-03-02'),
(5, 17, 38.00, TRUE, '2025-03-02'), (5, 18, 78.00, TRUE, '2025-03-03'), (5, 19, 245.00, TRUE, '2025-03-11'), (5, 20, 95.00, TRUE, '2025-03-13');

-- 5.6 EMPLEADO (10 empleados: 3 administradores, 4 vendedores, 3 almacenistas)
INSERT INTO empleado (surcve, stocve, nombre, apellidopaterno, apellidomaterno, rol, descripcion, estatus, username, email, password, fecha, direccion, codigopostal) VALUES
(1, NULL, 'Vielka Ailyn', 'Herrera', 'Cruz', 'Administrador', 'Encargada general sucursal Centro', 'activo', 'vherrera', 'vherrera@ferreteria.com', '$2b$10$Kf3.hashAdm001aaaaaaaaa', '2025-01-05', 'Calle Morelos 12', '42000'),
(2, NULL, 'Zaid Emanuel', 'Hernandez', 'Espinosa', 'Administrador', 'Encargado sucursal Tulancingo', 'activo', 'zhernandez', 'zhernandez@ferreteria.com', '$2b$10$Kf3.hashAdm002bbbbbbbbb', '2025-01-05', 'Av. Reforma 55', '43600'),
(3, NULL, 'Randy Noe', 'Lopez', 'Lara', 'Administrador', 'Encargado sucursal Tizayuca', 'activo', 'rlopez', 'rlopez@ferreteria.com', '$2b$10$Kf3.hashAdm003ccccccccc', '2025-01-06', 'Priv. Hidalgo 8', '43800'),
(1, NULL, 'Jorge Saul', 'Gonzalez', 'Lopez', 'Vendedor', 'Ventas mostrador turno matutino', 'activo', 'jgonzalez', 'jgonzalez@ferreteria.com', '$2b$10$Kf3.hashVen001ddddddddd', '2025-01-10', 'Calle Allende 3', '42010'),
(1, NULL, 'Marisol', 'Ramirez', 'Ortiz', 'Vendedor', 'Ventas mostrador turno vespertino', 'activo', 'mramirez', 'mramirez@ferreteria.com', '$2b$10$Kf3.hashVen002eeeeeeeee', '2025-02-01', 'Calle Zaragoza 40', '42020'),
(2, NULL, 'Carlos', 'Mendoza', 'Ruiz', 'Vendedor', 'Ventas mostrador y atención telefónica', 'activo', 'cmendoza', 'cmendoza@ferreteria.com', '$2b$10$Kf3.hashVen003fffffffff', '2025-02-05', 'Blvd. Norte 90', '43610'),
(4, NULL, 'Fernanda', 'Torres', 'Diaz', 'Vendedor', 'Ventas mostrador sucursal Ixmiquilpan', 'activo', 'ftorres', 'ftorres@ferreteria.com', '$2b$10$Kf3.hashVen004ggggggggg', '2025-02-08', 'Calle Juárez 15', '42300'),
(1, 4,  'Alberto', 'Vazquez', 'Nava', 'Almacenista', 'Control de inventario sucursal Centro', 'activo', 'avazquez', 'avazquez@ferreteria.com', '$2b$10$Kf3.hashAlm001hhhhhhhhh', '2025-01-12', 'Calle Guerrero 20', '42030'),
(2, 10, 'Patricia', 'Salinas', 'Cruz', 'Almacenista', 'Control de inventario sucursal Tulancingo', 'activo', 'psalinas', 'psalinas@ferreteria.com', '$2b$10$Kf3.hashAlm002iiiiiiiii', '2025-02-14', 'Av. Hidalgo 62', '43620'),
(5, 19, 'Ricardo', 'Cervantes', 'Bautista', 'Almacenista', 'Control de inventario sucursal Huejutla', 'activo', 'rcervantes', 'rcervantes@ferreteria.com', '$2b$10$Kf3.hashAlm003jjjjjjjjj', '2025-03-15', 'Calle Morelos 5', '43000');

-- 5.7 CLIENTE (20 clientes variados, con cuenta de acceso propia)
INSERT INTO cliente (nombre, apellidopaterno, apellidomaterno, telefono, username, email, password, fecha, direccion, codigopostal, membresia, estatus) VALUES
('Luis',      'Garcia',   'Hernandez', '7711234501', 'lgarcia01',   'lgarcia01@correo.com',   '$2b$10$Cli.hash01aaaaaaaaaaaaa', '2025-01-08', 'Calle Pino Suarez 10', '42000', 'basica',  'activo'),
('Ana',       'Martinez', 'Lopez',     '7711234502', 'amartinez02', 'amartinez02@correo.com', '$2b$10$Cli.hash02bbbbbbbbbbbbb', '2025-01-10', 'Av. Colon 22',        '42010', 'premium', 'activo'),
('Jose',      'Rodriguez','Sanchez',   '7711234503', 'jrodriguez03','jrodriguez03@correo.com','$2b$10$Cli.hash03ccccccccccccc', '2025-01-14', 'Calle Matamoros 5',   '42020', 'basica',  'activo'),
('Guadalupe', 'Perez',    'Ramirez',   '7711234504', 'gperez04',    'gperez04@correo.com',    '$2b$10$Cli.hash04ddddddddddddd', '2025-01-18', 'Priv. Zaragoza 8',    '42030', 'basica',  'activo'),
('Miguel',    'Sanchez',  'Torres',    '7711234505', 'msanchez05',  'msanchez05@correo.com',  '$2b$10$Cli.hash05eeeeeeeeeeeee', '2025-01-22', 'Calle Aldama 15',     '42040', 'premium', 'activo'),
('Rosa',      'Flores',   'Diaz',      '7711234506', 'rflores06',   'rflores06@correo.com',   '$2b$10$Cli.hash06fffffffffffff', '2025-01-25', 'Av. Revolucion 33',   '42050', 'basica',  'activo'),
('Juan',      'Gomez',    'Vazquez',   '7711234507', 'jgomez07',    'jgomez07@correo.com',    '$2b$10$Cli.hash07ggggggggggggg', '2025-02-01', 'Calle Cuauhtemoc 44', '42060', 'basica',  'activo'),
('Leticia',   'Diaz',     'Nava',      '7711234508', 'ldiaz08',     'ldiaz08@correo.com',     '$2b$10$Cli.hash08hhhhhhhhhhhhh', '2025-02-04', 'Calle Ninos Heroes 9','42070', 'basica',  'activo'),
('Francisco', 'Cruz',     'Ortega',    '7711234509', 'fcruz09',     'fcruz09@correo.com',     '$2b$10$Cli.hash09iiiiiiiiiiiii', '2025-02-09', 'Av. Insurgentes 100', '42080', 'premium', 'activo'),
('Maria',     'Reyes',    'Salinas',   '7711234510', 'mreyes10',    'mreyes10@correo.com',    '$2b$10$Cli.hash10jjjjjjjjjjjjj', '2025-02-12', 'Calle Iturbide 61',   '42090', 'basica',  'activo'),
('Alejandro', 'Morales',  'Castillo',  '7711234511', 'amorales11',  'amorales11@correo.com',  '$2b$10$Cli.hash11kkkkkkkkkkkkk', '2025-02-15', 'Calle Xicotencatl 7', '43600', 'basica',  'activo'),
('Sofia',     'Jimenez',  'Bautista',  '7711234512', 'sjimenez12',  'sjimenez12@correo.com',  '$2b$10$Cli.hash12lllllllllllll', '2025-02-19', 'Av. Peraltas 34',     '43610', 'premium', 'activo'),
('Ricardo',   'Ortiz',    'Guerrero',  '7711234513', 'rortiz13',    'rortiz13@correo.com',    '$2b$10$Cli.hash13mmmmmmmmmmmmm', '2025-02-23', 'Calle Melchor Ocampo 2','43620','basica', 'activo'),
('Elena',     'Ruiz',     'Mendoza',   '7711234514', 'eruiz14',     'eruiz14@correo.com',     '$2b$10$Cli.hash14nnnnnnnnnnnnn', '2025-03-02', 'Priv. Constitucion 18','43800','basica', 'activo'),
('Daniel',    'Chavez',   'Rivera',    '7711234515', 'dchavez15',   'dchavez15@correo.com',   '$2b$10$Cli.hash15ooooooooooooo', '2025-03-06', 'Calle Emiliano Zapata 27','43810','basica','activo'),
('Karla',     'Vega',     'Fuentes',   '7711234516', 'kvega16',     'kvega16@correo.com',     '$2b$10$Cli.hash16ppppppppppppp', '2025-03-11', 'Av. Miguel Hidalgo 51','42300','premium','activo'),
('Oscar',     'Castro',   'Aguilar',   '7711234517', 'ocastro17',   'ocastro17@correo.com',   '$2b$10$Cli.hash17qqqqqqqqqqqqq', '2025-03-14', 'Calle Guerrero 9',     '42310', 'basica',  'activo'),
('Paola',     'Navarro',  'Delgado',   '7711234518', 'pnavarro18',  'pnavarro18@correo.com',  '$2b$10$Cli.hash18rrrrrrrrrrrrr', '2025-03-18', 'Calle 5 de Mayo 60',   '43000', 'basica',  'activo'),
('Hector',    'Silva',    'Campos',    '7711234519', 'hsilva19',    'hsilva19@correo.com',    '$2b$10$Cli.hash19sssssssssssss', '2025-03-21', 'Av. Juarez 88',        '43010', 'premium', 'activo'),
('Andrea',    'Rios',     'Paredes',   '7711234520', 'arios20',     'arios20@correo.com',     '$2b$10$Cli.hash20ttttttttttttt', '2025-03-25', 'Calle Progreso 14',    '43020', 'basica',  'activo');

-- 5.8 VENTA (20 ventas; total/subtotal en 0 porque los recalcula el trigger al insertar detalle_venta)
INSERT INTO venta (empcve, clicve, total, subtotal, descripcion, estatus, metodo_pago, tipo_entrega, direccion_entrega, codigo_postal, fecha) VALUES
(4, 1,  0, 0, 'Compra de mostrador', 'completada', 'efectivo',      'mostrador', NULL, NULL, '2025-06-01'),
(4, 2,  0, 0, 'Compra con tarjeta',  'completada', 'tarjeta',       'mostrador', NULL, NULL, '2025-06-01'),
(5, 3,  0, 0, 'Pedido a domicilio',  'completada', 'transferencia', 'domicilio', 'Calle Matamoros 5', '42020', '2025-06-02'),
(5, 4,  0, 0, 'Compra de mostrador', 'completada', 'efectivo',      'mostrador', NULL, NULL, '2025-06-02'),
(4, 5,  0, 0, 'Compra con tarjeta',  'completada', 'tarjeta',       'mostrador', NULL, NULL, '2025-06-03'),
(6, 6,  0, 0, 'Pedido a domicilio',  'completada', 'efectivo',      'domicilio', 'Av. Revolucion 33', '42050', '2025-06-04'),
(6, 7,  0, 0, 'Compra de mostrador', 'completada', 'efectivo',      'mostrador', NULL, NULL, '2025-06-05'),
(7, 8,  0, 0, 'Compra con tarjeta',  'completada', 'tarjeta',       'mostrador', NULL, NULL, '2025-06-06'),
(4, 9,  0, 0, 'Pedido a domicilio',  'completada', 'transferencia', 'domicilio', 'Av. Insurgentes 100', '42080', '2025-06-07'),
(5, 10, 0, 0, 'Compra de mostrador', 'completada', 'efectivo',      'mostrador', NULL, NULL, '2025-06-08'),
(6, 11, 0, 0, 'Compra con tarjeta',  'completada', 'tarjeta',       'mostrador', NULL, NULL, '2025-06-09'),
(6, 12, 0, 0, 'Pedido a domicilio',  'completada', 'efectivo',      'domicilio', 'Av. Peraltas 34', '43610', '2025-06-10'),
(7, 13, 0, 0, 'Compra de mostrador', 'completada', 'efectivo',      'mostrador', NULL, NULL, '2025-06-11'),
(4, 14, 0, 0, 'Compra con tarjeta',  'completada', 'tarjeta',       'mostrador', NULL, NULL, '2025-06-12'),
(5, 15, 0, 0, 'Pedido a domicilio',  'completada', 'transferencia', 'domicilio', 'Calle Emiliano Zapata 27', '43810', '2025-06-13'),
(6, 16, 0, 0, 'Compra de mostrador', 'completada', 'efectivo',      'mostrador', NULL, NULL, '2025-06-14'),
(7, 17, 0, 0, 'Compra con tarjeta',  'completada', 'tarjeta',       'mostrador', NULL, NULL, '2025-06-15'),
(4, 18, 0, 0, 'Compra de mostrador', 'completada', 'efectivo',      'mostrador', NULL, NULL, '2025-06-16'),
(5, 19, 0, 0, 'Pedido a domicilio',  'completada', 'efectivo',      'domicilio', 'Av. Juarez 88', '43010', '2025-06-17'),
(6, 20, 0, 0, 'Compra con tarjeta',  'completada', 'tarjeta',       'mostrador', NULL, NULL, '2025-06-18');

-- 5.9 DETALLE_VENTA (20 líneas; cada INSERT dispara los triggers de stock y de total_venta)
--     Descuentos variados: algunos en 0 (se normalizan a NULL por el trigger), otros con valor.
INSERT INTO detalle_venta (procve, vencve, fecha, cantidad, precio, subtotal, descuento, estatus, modalidad) VALUES
(1,  1,  '2025-06-01', 2, 185.00,  370.00,   0,     'activo', 'normal'),
(3,  2,  '2025-06-01', 1, 165.00,  165.00,   0,     'activo', 'normal'),
(7,  3,  '2025-06-02', 6, 95.00,   570.00,   0,     'activo', 'normal'),
(9,  4,  '2025-06-02', 10, 8.50,   85.00,    0,     'activo', 'normal'),
(14, 5,  '2025-06-03', 2, 55.00,   110.00,   0,     'activo', 'normal'),
(20, 6,  '2025-06-04', 1, 95.00,   95.00,    0,     'activo', 'normal'),
(11, 7,  '2025-06-05', 3, 35.00,   105.00,   10.50, 'activo', 'normal'),
(4,  8,  '2025-06-06', 1, 1250.00, 1250.00,  0,     'activo', 'normal'),
(19, 9,  '2025-06-07', 1, 245.00,  245.00,   0,     'activo', 'normal'),
(17, 10, '2025-06-08', 4, 38.00,   152.00,   0,     'activo', 'normal'),
(5,  11, '2025-06-09', 1, 890.00,  890.00,   0,     'activo', 'normal'),
(13, 12, '2025-06-10', 1, 385.00,  385.00,   19.25, 'activo', 'normal'),
(2,  13, '2025-06-11', 1, 249.50,  249.50,   0,     'activo', 'normal'),
(16, 14, '2025-06-12', 5, 45.00,   225.00,   0,     'activo', 'normal'),
(6,  15, '2025-06-13', 1, 2450.00, 2450.00,  0,     'activo', 'normal'),
(18, 16, '2025-06-14', 2, 78.00,   156.00,   0,     'activo', 'normal'),
(8,  17, '2025-06-15', 2, 68.00,   136.00,   0,     'activo', 'normal'),
(12, 18, '2025-06-16', 3, 42.00,   126.00,   0,     'activo', 'normal'),
(10, 19, '2025-06-17', 1, 1180.00, 1180.00,  0,     'activo', 'normal'),
(15, 20, '2025-06-18', 2, 62.00,   124.00,   0,     'activo', 'normal');


-- =====================================================================
-- 6. EJEMPLOS DE USO (comentado, para pruebas manuales)
-- =====================================================================

-- Limpieza batch de descuentos en 0 (por si hay datos migrados de otra fuente):
-- CALL sp_limpiar_descuentos();

-- Aplicar 15% de descuento al detalle de venta con id 3:
-- CALL sp_aplicar_descuento(3, 'porcentaje', 15);

-- Intentar aplicar 2x1 a un detalle con cantidad = 1 (NO debe aplicarse ningún cambio):
-- CALL sp_aplicar_descuento(2, '2x1', NULL);

-- Aplicar 2x1 a un detalle con cantidad >= 2 (sí se aplica):
-- CALL sp_aplicar_descuento(3, '2x1', NULL);

-- Reabastecer un producto que está en alerta de stock bajo:
-- CALL sp_abastecer_stock(6, 20);

-- Ver los productos con alerta de stock bajo:
-- SELECT p.nombre, s.stock_actual, s.stock_minimo, s.estatus, s.descripcion
-- FROM stock s JOIN producto p ON p.procve = s.procve
-- WHERE s.estatus = 'alerta';

-- Flujo de recuperación de contraseña (2 pasos):
-- Paso 1: el usuario pide "olvidé mi contraseña" con su correo. El backend genera el token:
-- CALL sp_generar_token_reset('cliente', 'lgarcia01@correo.com', NULL);
-- (el backend recibe p_token en el parámetro OUT y lo envía por correo con Nodemailer, nunca lo muestra en pantalla)

-- Paso 2: el usuario da clic en el link del correo y captura su nueva contraseña.
-- El backend ya debió hashear la nueva contraseña con bcrypt antes de este CALL:
-- CALL sp_restablecer_password('cliente', 'token_recibido_por_correo', '$2b$10$nuevoHashBcrypt...');

-- Si el token ya expiró (más de 1 hora) o no existe, el procedimiento avisa y no cambia nada.

CREATE ROLE app_django LOGIN PASSWORD 'Dj4ng0_Ferr_App2026!';
-- Necesita los mismos privilegios de lectura/escritura que usa la app en conjunto
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_django;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_django;

-- Ejecutar todos los procedimientos (la validación de rol ahora vive en Django, no en current_user)
GRANT EXECUTE ON PROCEDURE sp_generar_token_reset(VARCHAR, VARCHAR, VARCHAR, VARCHAR) TO app_django;
GRANT EXECUTE ON PROCEDURE sp_restablecer_password(VARCHAR, VARCHAR, VARCHAR, VARCHAR) TO app_django;
GRANT EXECUTE ON PROCEDURE sp_aplicar_descuento(INT, VARCHAR, NUMERIC) TO app_django;
GRANT EXECUTE ON PROCEDURE sp_disminuir_stock(INT, INT) TO app_django;
GRANT EXECUTE ON PROCEDURE sp_abastecer_stock(INT, INT) TO app_django;
GRANT EXECUTE ON PROCEDURE sp_limpiar_descuentos() TO app_django;
GRANT EXECUTE ON PROCEDURE sp_eliminar_producto(INT, VARCHAR) TO app_django;
