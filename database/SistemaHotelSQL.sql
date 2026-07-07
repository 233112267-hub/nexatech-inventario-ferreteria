--  Sistema Hotelero - Base de Datos MySQL
CREATE DATABASE IF NOT EXISTS sistema_hotelero;
USE sistema_hotelero;

--  USUARIO
CREATE TABLE Usuario (
    id_usuario  INT             NOT NULL AUTO_INCREMENT,
    nombre      VARCHAR(100)    NOT NULL,
    password    VARCHAR(255)    NOT NULL,
    rol         VARCHAR(50)     NOT NULL,
    PRIMARY KEY (id_usuario)
);

--  CUSTOMER
CREATE TABLE Customer (
    id_cliente  INT             NOT NULL AUTO_INCREMENT,
    nombre      VARCHAR(100)    NOT NULL,
    direccion   VARCHAR(255)    NOT NULL,
    telefono    VARCHAR(20)     NOT NULL,
    id_usuario  INT             NOT NULL,
    PRIMARY KEY (id_cliente),
    FOREIGN KEY (id_usuario) REFERENCES Usuario (id_usuario)
);

--  ROOM
CREATE TABLE Room (
    roomNo      INT             NOT NULL AUTO_INCREMENT,
    bedType     VARCHAR(50)     NOT NULL,
    roomType    VARCHAR(50)     NOT NULL,
    price       DECIMAL(10, 2)  NOT NULL,
    status      VARCHAR(30)     NOT NULL,
    PRIMARY KEY (roomNo)
);

--  RESTAURANT
CREATE TABLE Restaurant (
    id_dish     INT             NOT NULL AUTO_INCREMENT,
    dishName    VARCHAR(150)    NOT NULL,
    dishType    VARCHAR(80)     NOT NULL,
    dishPrice   DECIMAL(10, 2)  NOT NULL,
    PRIMARY KEY (id_dish)
);

--  DETALLEROOM  (transaccional - reservas)
CREATE TABLE DetalleRoom (
    id_reserva      INT             NOT NULL AUTO_INCREMENT,
    id_cliente      INT             NOT NULL,
    roomNo          INT             NOT NULL,
    fecha_entrada   DATE            NOT NULL,
    fecha_salida    DATE            NOT NULL,
    precio          DECIMAL(10, 2)  NOT NULL,
    PRIMARY KEY (id_reserva),
    FOREIGN KEY (id_cliente) REFERENCES Customer (id_cliente),
    FOREIGN KEY (roomNo)     REFERENCES Room (roomNo)
);

--  INSERT - USUARIO
INSERT INTO Usuario (nombre, password, rol) VALUES
    ('Carlos Mendoza',    'e10adc3949ba59abbe56e057f20f883e', 'admin'),
    ('Laura Sánchez',     'e10adc3949ba59abbe56e057f20f883e', 'recepcionista'),
    ('Miguel Torres',     '25d55ad283aa400af464c76d713c07ad', 'recepcionista'),
    ('Ana Ramírez',       '25d55ad283aa400af464c76d713c07ad', 'recepcionista'),
    ('Pedro Castillo',    'e10adc3949ba59abbe56e057f20f883e', 'admin'),
    ('Sofía Herrera',     '827ccb0eea8a706c4c34a16891f84e7b', 'recepcionista'),
    ('Javier Morales',    '827ccb0eea8a706c4c34a16891f84e7b', 'recepcionista'),
    ('Valentina Cruz',    'e10adc3949ba59abbe56e057f20f883e', 'admin'),
    ('Roberto Jiménez',   '25d55ad283aa400af464c76d713c07ad', 'recepcionista'),
    ('Daniela Flores',    '827ccb0eea8a706c4c34a16891f84e7b', 'recepcionista');

--  INSERT - CUSTOMER
INSERT INTO Customer (nombre, direccion, telefono, id_usuario) VALUES
    ('John Smith',        'Av. Reforma 145, CDMX',          '5512345678', 1),
    ('Marie Dupont',      'Calle 5 de Mayo 22, Puebla',     '2221987654', 2),
    ('Hiroshi Tanaka',    'Blvd. Kukulcán Km 12, Cancún',   '9981234567', 3),
    ('Emily Johnson',     'Paseo Montejo 300, Mérida',      '9991234567', 4),
    ('Carlos Vega',       'Insurgentes Sur 500, CDMX',      '5598765432', 5),
    ('Fatima Al-Rashid',  'Av. Universidad 200, Monterrey', '8181234567', 6),
    ('Lucas Oliveira',    'Calle Hidalgo 88, Guadalajara',  '3312345678', 7),
    ('Chloe Martin',      'Av. Juárez 10, Querétaro',       '4421234567', 8),
    ('David Kim',         'Blvd. Torres 77, Tijuana',       '6641234567', 9),
    ('Isabella Rossi',    'Av. Costera 55, Acapulco',       '7441234567', 10);

--  INSERT - ROOM
INSERT INTO Room (bedType, roomType, price, status) VALUES
    ('King',    'Suite',         2500.00, 'disponible'),
    ('Queen',   'Doble',          950.00, 'disponible'),
    ('Twin',    'Estándar',       700.00, 'ocupada'),
    ('King',    'Suite Júnior',  1800.00, 'disponible'),
    ('Queen',   'Estándar',       750.00, 'mantenimiento'),
    ('King',    'Suite Penthouse',4500.00,'disponible'),
    ('Twin',    'Doble',          900.00, 'ocupada'),
    ('Queen',   'Suite Júnior',  1750.00, 'disponible'),
    ('King',    'Estándar',       800.00, 'ocupada'),
    ('Twin',    'Estándar',       680.00, 'disponible');

--  INSERT - RESTAURANT

INSERT INTO Restaurant (dishName, dishType, dishPrice) VALUES
    ('Caldo Tlalpeño',        'Sopa',       85.00),
    ('Filete de Res a la Parrilla', 'Plato fuerte', 250.00),
    ('Enchiladas Verdes',     'Plato fuerte', 130.00),
    ('Ensalada César',        'Entrada',      95.00),
    ('Tilapia al Limón',      'Plato fuerte', 180.00),
    ('Pasta Alfredo',         'Plato fuerte', 160.00),
    ('Flan Napolitano',       'Postre',        70.00),
    ('Jugo de Naranja Natural','Bebida',        55.00),
    ('Quesadillas de Flor',   'Entrada',       110.00),
    ('Brownie con Helado',    'Postre',         90.00);

--  INSERT - DETALLEROOM

INSERT INTO DetalleRoom (id_cliente, roomNo, fecha_entrada, fecha_salida, precio) VALUES
    (1,  1, '2025-07-01', '2025-07-05',  10000.00),
    (2,  2, '2025-07-03', '2025-07-06',   2850.00),
    (3,  3, '2025-07-05', '2025-07-08',   2100.00),
    (4,  4, '2025-07-10', '2025-07-14',   7200.00),
    (5,  6, '2025-07-12', '2025-07-13',   4500.00),
    (6,  8, '2025-07-15', '2025-07-18',   5250.00),
    (7, 10, '2025-07-20', '2025-07-22',   1360.00),
    (8,  2, '2025-07-22', '2025-07-25',   2850.00),
    (9,  9, '2025-07-25', '2025-07-27',   1600.00),
    (10, 4, '2025-07-28', '2025-07-30',   3600.00);