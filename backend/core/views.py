from django.shortcuts import render

# Create your views here.
# core/views.py
import json
import bcrypt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Empleado, Cliente
from .jwt_utils import generar_jwt


@csrf_exempt
@require_POST
def login_view(request):
    """
    Login unificado. Espera: { "tipo": "empleado"|"cliente", "username": "...", "password": "..." }
    """
    data = json.loads(request.body)
    tipo = data.get("tipo")
    username = data.get("username")
    password = data.get("password")

    if tipo not in ("empleado", "cliente"):
        return JsonResponse({"error": "Tipo de usuario inválido"}, status=400)

    if not username or not password:
        return JsonResponse({"error": "Faltan credenciales"}, status=400)

    Modelo = Empleado if tipo == "empleado" else Cliente

    try:
        usuario = Modelo.objects.get(username=username)
    except Modelo.DoesNotExist:
        # Mensaje genérico: no reveles si el username existe o no
        return JsonResponse({"error": "Credenciales inválidas"}, status=401)

    if usuario.estatus != "activo":
        return JsonResponse({"error": "Cuenta inactiva, contacta al administrador"}, status=403)

    password_valido = bcrypt.checkpw(
        password.encode("utf-8"), usuario.password.encode("utf-8")
    )

    if not password_valido:
        return JsonResponse({"error": "Credenciales inválidas"}, status=401)

    payload = {
        "tipo": tipo,
        "username": usuario.username,
        "email": usuario.email,
    }

    if tipo == "empleado":
        payload["empcve"] = usuario.empcve
        payload["rol"] = usuario.rol  # 'Administrador', 'Vendedor', 'Almacenista'
    else:
        payload["clicve"] = usuario.clicve
        payload["membresia"] = usuario.membresia

    token = generar_jwt(payload)

    return JsonResponse({"token": token, "tipo": tipo, "rol": payload.get("rol")})