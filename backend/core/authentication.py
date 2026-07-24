import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from usuarios.models import Usuario


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Equivalente a src/middleware/auth.js (authMiddleware) del backend Express.
    Espera el header: Authorization: Bearer <token>
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None  # deja pasar; IsAuthenticated se encarga de rechazar si hace falta

        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token expirado')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Token inválido')

        try:
            usuario = Usuario.objects.select_related('id_rol').get(pk=payload['id'], activo=True)
        except Usuario.DoesNotExist:
            raise exceptions.AuthenticationFailed('Usuario no encontrado o inactivo')

        return (usuario, token)


def generar_token(usuario):
    import datetime
    payload = {
        'id': usuario.id_usuario,
        'username': usuario.username,
        'rol': usuario.rol_nombre,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=settings.JWT_EXPIRES_HOURS),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')

