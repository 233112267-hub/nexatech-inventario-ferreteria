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