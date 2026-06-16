const jwt = require('jsonwebtoken');

/**
 * Verifica que la petición incluya un JWT válido en el header Authorization.
 */
const authMiddleware = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ ok: false, message: 'Token no proporcionado' });
  }

  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded; // { id, usuario, rol }
    next();
  } catch (err) {
    return res.status(401).json({ ok: false, message: 'Token inválido o expirado' });
  }
};

/**
 * Restringe acceso a roles específicos.
 * Uso: roleMiddleware('Administrador')  o  roleMiddleware('Administrador','Almacenista')
 */
const roleMiddleware = (...roles) => (req, res, next) => {
  if (!req.user) return res.status(401).json({ ok: false, message: 'No autenticado' });
  if (!roles.includes(req.user.rol)) {
    return res.status(403).json({ ok: false, message: 'No tienes permisos para esta acción' });
  }
  next();
};

module.exports = { authMiddleware, roleMiddleware };
