# core/jwt_utils.py
import jwt
import datetime
from django.conf import settings

def generar_jwt(payload_extra: dict):
    """
    payload_extra debe incluir al menos: id, tipo ('empleado'/'cliente'), rol (si es empleado)
    """
    payload = {
        **payload_extra,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=settings.JWT_EXP_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decodificar_jwt(token: str):
    """
    Regresa el payload si es válido, o lanza jwt.ExpiredSignatureError / jwt.InvalidTokenError
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

from functools import wraps
from django.http import JsonResponse


def requiere_rol(*roles_permitidos):
    """
    Decorador para vistas. Valida el JWT del header Authorization: Bearer <token>
    y verifica que el usuario sea empleado con uno de los roles permitidos.
    Guarda el payload decodificado en request.usuario_jwt
    """
    def decorador(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            auth_header = request.headers.get("Authorization", "")

            if not auth_header.startswith("Bearer "):
                return JsonResponse({"error": "Token no proporcionado"}, status=401)

            token = auth_header.split(" ", 1)[1]

            try:
                payload = decodificar_jwt(token)
            except jwt.ExpiredSignatureError:
                return JsonResponse({"error": "Token expirado"}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({"error": "Token inválido"}, status=401)

            if payload.get("tipo") != "empleado" or payload.get("rol") not in roles_permitidos:
                return JsonResponse({"error": "No autorizado"}, status=403)

            request.usuario_jwt = payload
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorador