from django.shortcuts import render

# Create your views here.
# core/views.py
import json
import bcrypt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Empleado, Cliente
from .models import Empleado, Cliente, Producto, Categoria, Surcusal
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

from .models import Empleado, Cliente, Producto, Categoria
from .jwt_utils import generar_jwt, requiere_rol


@csrf_exempt
@require_POST
@requiere_rol("Administrador")
def crear_producto_view(request):
    """
    Solo Administrador. Espera:
    { "catcve": 1, "nombre": "...", "precio": 100.00, "descripcion": "...", 
      "modelo": "...", "marca": "...", "color": "...", "informacion_adicional": "..." }
    """
    data = json.loads(request.body)

    catcve = data.get("catcve")
    nombre = data.get("nombre")
    precio = data.get("precio")

    if not catcve or not nombre or precio is None:
        return JsonResponse({"error": "Faltan campos obligatorios: catcve, nombre, precio"}, status=400)

    try:
        categoria = Categoria.objects.get(catcve=catcve)
    except Categoria.DoesNotExist:
        return JsonResponse({"error": "La categoría indicada no existe"}, status=400)

    if float(precio) <= 0:
        return JsonResponse({"error": "El precio debe ser mayor a 0"}, status=400)

    producto = Producto.objects.create(
        catcve=categoria,
        nombre=nombre,
        precio=precio,
        descripcion=data.get("descripcion"),
        modelo=data.get("modelo"),
        marca=data.get("marca"),
        color=data.get("color"),
        informacion_adicional=data.get("informacion_adicional"),
    )

    return JsonResponse({
        "mensaje": "Producto creado correctamente",
        "producto": {
            "procve": producto.procve,
            "nombre": producto.nombre,
            "precio": str(producto.precio),
            "catcve": categoria.catcve,
        }
    }, status=201)

@csrf_exempt
@require_POST
@requiere_rol("Administrador")
def crear_empleado_view(request):
    """
    Solo Administrador. Espera:
    { "surcve": 1, "nombre": "...", "apellidopaterno": "...", "apellidomaterno": "...",
      "rol": "Vendedor", "username": "...", "email": "...", "password": "..." }
    """
    data = json.loads(request.body)

    surcve = data.get("surcve")
    nombre = data.get("nombre")
    apellidopaterno = data.get("apellidopaterno")
    rol = data.get("rol")
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all([surcve, nombre, apellidopaterno, rol, username, email, password]):
        return JsonResponse({"error": "Faltan campos obligatorios"}, status=400)

    if rol not in ("Administrador", "Vendedor"):
        return JsonResponse({"error": "Rol inválido. Use Administrador o Vendedor"}, status=400)

    try:
        sucursal = Surcusal.objects.get(surcve=surcve)
    except Surcusal.DoesNotExist:
        return JsonResponse({"error": "La sucursal indicada no existe"}, status=400)

    if Empleado.objects.filter(username=username).exists():
        return JsonResponse({"error": "El username ya está en uso"}, status=400)

    if Empleado.objects.filter(email=email).exists():
        return JsonResponse({"error": "El email ya está en uso"}, status=400)

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(10)).decode("utf-8")

    empleado = Empleado.objects.create(
        surcve=sucursal,
        nombre=nombre,
        apellidopaterno=apellidopaterno,
        apellidomaterno=data.get("apellidomaterno"),
        rol=rol,
        username=username,
        email=email,
        password=password_hash,
    )

    return JsonResponse({
        "mensaje": "Empleado creado correctamente",
        "empleado": {
            "empcve": empleado.empcve,
            "nombre": empleado.nombre,
            "username": empleado.username,
            "rol": empleado.rol,
        }
    }, status=201)