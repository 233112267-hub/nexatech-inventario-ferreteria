from django.shortcuts import render

# Create your views here.
# core/views.py
import json
import bcrypt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, DatabaseError, connection
from django.utils import timezone
from .models import Empleado, Cliente
from .models import Empleado, Cliente, Producto, Categoria, Surcusal, Venta, DetalleVenta
from .models import Empleado, Cliente, Producto, Categoria, Surcusal
from .jwt_utils import generar_jwt
#vista de modelo
from django.db.models import Sum, Count, Q, F
from datetime import date, timedelta
from .models import Stock, Alerta, Movimiento

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
        payload["rol"] = usuario.rol  # 'Administrador' o 'Vendedor'
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

@require_GET
@requiere_rol("Administrador", "Vendedor")
def listar_productos_view(request):
    productos = Producto.objects.filter(estatus="activo").select_related("catcve")

    data = [
        {
            "procve": p.procve,
            "nombre": p.nombre,
            "precio": str(p.precio),
            "descripcion": p.descripcion,
            "modelo": p.modelo,
            "marca": p.marca,
            "color": p.color,
            "categoria": p.catcve.nombre,
        }
        for p in productos
    ]

    return JsonResponse({"productos": data}, status=200)

@require_GET
@requiere_rol("Administrador")
def listar_empleados_view(request):
    empleados = Empleado.objects.filter(estatus="activo").select_related("surcve")

    data = [
        {
            "empcve": e.empcve,
            "nombre": e.nombre,
            "apellidopaterno": e.apellidopaterno,
            "apellidomaterno": e.apellidomaterno,
            "rol": e.rol,
            "username": e.username,
            "email": e.email,
            "sucursal": e.surcve.direccion,
        }
        for e in empleados
    ]

    return JsonResponse({"empleados": data}, status=200)
@csrf_exempt
@require_http_methods(["PUT", "PATCH", "DELETE"])
@requiere_rol("Administrador")
def actualizar_producto_view(request, procve):
    try:
        producto = Producto.objects.get(procve=procve)
    except Producto.DoesNotExist:
        return JsonResponse({"error": "Producto no encontrado"}, status=404)

    if request.method == "DELETE":
        if producto.estatus == "inactivo":
            return JsonResponse({"error": "El producto ya está inactivo"}, status=400)
        producto.estatus = "inactivo"
        producto.save()
        return JsonResponse({
            "mensaje": "Producto eliminado correctamente",
            "producto": {"procve": producto.procve, "nombre": producto.nombre, "estatus": producto.estatus}
        }, status=200)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    campos_permitidos = [
        "nombre", "precio", "descripcion", "modelo",
        "marca", "color", "informacion_adicional", "catcve", "estatus"
    ]

    if request.method == "PUT":
        # PUT: se espera que manden TODOS los campos obligatorios
        faltantes = [c for c in ("catcve", "nombre", "precio") if data.get(c) is None]
        if faltantes:
            return JsonResponse(
                {"error": f"PUT requiere todos los campos obligatorios. Faltan: {', '.join(faltantes)}"},
                status=400
            )

    # Validar catcve si viene incluido (en PUT siempre, en PATCH si el usuario lo manda)
    if "catcve" in data:
        try:
            categoria = Categoria.objects.get(catcve=data["catcve"])
            producto.catcve = categoria
        except Categoria.DoesNotExist:
            return JsonResponse({"error": "La categoría indicada no existe"}, status=400)

    # Validar precio si viene incluido
    if "precio" in data:
        try:
            precio = float(data["precio"])
        except (TypeError, ValueError):
            return JsonResponse({"error": "El precio debe ser un número válido"}, status=400)
        if precio <= 0:
            return JsonResponse({"error": "El precio debe ser mayor a 0"}, status=400)
        producto.precio = precio

    # Resto de los campos: se actualizan solo si vienen en el body
    for campo in campos_permitidos:
        if campo in data and campo not in ("catcve", "precio"):
            setattr(producto, campo, data[campo])

    producto.save()

    return JsonResponse({
        "mensaje": "Producto actualizado correctamente",
        "producto": {
            "procve": producto.procve,
            "nombre": producto.nombre,
            "precio": str(producto.precio),
            "catcve": producto.catcve.catcve,
            "estatus": producto.estatus,
        }
    }, status=200)

@csrf_exempt
@require_http_methods(["PUT", "PATCH", "DELETE"])
@requiere_rol("Administrador")
def actualizar_empleado_view(request, empcve):
    try:
        empleado = Empleado.objects.get(empcve=empcve)
    except Empleado.DoesNotExist:
        return JsonResponse({"error": "Empleado no encontrado"}, status=404)

    if request.method == "DELETE":
        if empleado.estatus == "inactivo":
            return JsonResponse({"error": "El empleado ya está inactivo"}, status=400)
        empleado.estatus = "inactivo"
        empleado.save()
        return JsonResponse({
            "mensaje": "Empleado eliminado correctamente",
            "empleado": {"empcve": empleado.empcve, "nombre": empleado.nombre, "estatus": empleado.estatus}
        }, status=200)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    campos_permitidos = [
        "nombre", "apellidopaterno", "apellidomaterno",
        "rol", "surcve", "estatus"
    ]

    if request.method == "PUT":
        faltantes = [c for c in ("nombre", "apellidopaterno", "rol", "surcve") if not data.get(c)]
        if faltantes:
            return JsonResponse(
                {"error": f"PUT requiere todos los campos obligatorios. Faltan: {', '.join(faltantes)}"},
                status=400
            )

    # Validar sucursal si viene incluida
    if "surcve" in data:
        try:
            sucursal = Surcusal.objects.get(surcve=data["surcve"])
            empleado.surcve = sucursal
        except Surcusal.DoesNotExist:
            return JsonResponse({"error": "La sucursal indicada no existe"}, status=400)

    # Validar rol si viene incluido
    if "rol" in data:
        if data["rol"] not in ("Administrador", "Vendedor"):
            return JsonResponse({"error": "Rol inválido. Use Administrador o Vendedor"}, status=400)
        empleado.rol = data["rol"]

    # Validar username si viene incluido (evitar duplicados con otro empleado)
    if "username" in data:
        if Empleado.objects.exclude(empcve=empcve).filter(username=data["username"]).exists():
            return JsonResponse({"error": "El username ya está en uso"}, status=400)
        empleado.username = data["username"]

    # Validar email si viene incluido (evitar duplicados con otro empleado)
    if "email" in data:
        if Empleado.objects.exclude(empcve=empcve).filter(email=data["email"]).exists():
            return JsonResponse({"error": "El email ya está en uso"}, status=400)
        empleado.email = data["email"]

    # Password: solo si lo mandan, se hashea antes de guardar
    if "password" in data and data["password"]:
        empleado.password = bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt(10)).decode("utf-8")

    # Resto de los campos simples
    for campo in campos_permitidos:
        if campo in data and campo not in ("surcve", "rol"):
            setattr(empleado, campo, data[campo])

    empleado.save()

    return JsonResponse({
        "mensaje": "Empleado actualizado correctamente",
        "empleado": {
            "empcve": empleado.empcve,
            "nombre": empleado.nombre,
            "username": empleado.username,
            "rol": empleado.rol,
            "estatus": empleado.estatus,
        }
    }, status=200)

@csrf_exempt
@require_http_methods(["PUT", "PATCH", "DELETE"])
@requiere_rol("Administrador")
def actualizar_cliente_view(request, clicve):
    try:
        cliente = Cliente.objects.get(clicve=clicve)
    except Cliente.DoesNotExist:
        return JsonResponse({"error": "Cliente no encontrado"}, status=404)

    if request.method == "DELETE":
        if cliente.estatus == "inactivo":
            return JsonResponse({"error": "El cliente ya está inactivo"}, status=400)
        cliente.estatus = "inactivo"
        cliente.save()
        return JsonResponse({
            "mensaje": "Cliente eliminado correctamente",
            "cliente": {"clicve": cliente.clicve, "nombre": cliente.nombre, "estatus": cliente.estatus}
        }, status=200)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    campos_permitidos = [
        "nombre", "apellidopaterno", "apellidomaterno",
        "telefono", "membresia", "estatus"
    ]

    if request.method == "PUT":
        faltantes = [c for c in ("nombre", "apellidopaterno", "username", "email") if not data.get(c)]
        if faltantes:
            return JsonResponse(
                {"error": f"PUT requiere todos los campos obligatorios. Faltan: {', '.join(faltantes)}"},
                status=400
            )

    # Validar membresía si viene incluida
    if "membresia" in data:
        if data["membresia"] not in ("basica", "premium"):
            return JsonResponse({"error": "Membresía inválida. Use basica o premium"}, status=400)

    # Validar username si viene incluido (evitar duplicados con otro cliente)
    if "username" in data:
        if Cliente.objects.exclude(clicve=clicve).filter(username=data["username"]).exists():
            return JsonResponse({"error": "El username ya está en uso"}, status=400)
        cliente.username = data["username"]

    # Validar email si viene incluido (evitar duplicados con otro cliente)
    if "email" in data:
        if Cliente.objects.exclude(clicve=clicve).filter(email=data["email"]).exists():
            return JsonResponse({"error": "El email ya está en uso"}, status=400)
        cliente.email = data["email"]

    # Password: solo si lo mandan, se hashea antes de guardar
    if "password" in data and data["password"]:
        cliente.password = bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt(10)).decode("utf-8")

    # Resto de los campos simples
    for campo in campos_permitidos:
        if campo in data:
            setattr(cliente, campo, data[campo])

    cliente.save()

    return JsonResponse({
        "mensaje": "Cliente actualizado correctamente",
        "cliente": {
            "clicve": cliente.clicve,
            "nombre": cliente.nombre,
            "username": cliente.username,
            "membresia": cliente.membresia,
            "estatus": cliente.estatus,
        }
    }, status=200)

@require_GET
@requiere_rol("Administrador")
def listar_clientes_view(request):
    clientes = Cliente.objects.filter(estatus="activo")

    data = [
        {
            "clicve": cliente.clicve,
            "nombre": cliente.nombre,
            "apellidopaterno": cliente.apellidopaterno,
            "apellidomaterno": cliente.apellidomaterno,
            "telefono": cliente.telefono,
            "username": cliente.username,
            "email": cliente.email,
            "membresia": cliente.membresia,
            "estatus": cliente.estatus,
        }
        for cliente in clientes
    ]

    return JsonResponse({"clientes": data}, status=200)

@csrf_exempt
@require_POST
@requiere_rol("Administrador")
def crear_cliente_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    nombre = data.get("nombre")
    apellidopaterno = data.get("apellidopaterno")
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all([nombre, apellidopaterno, username, email, password]):
        return JsonResponse({"error": "Faltan campos obligatorios"}, status=400)

    membresia = data.get("membresia", "basica")
    if membresia not in ("basica", "premium"):
        return JsonResponse({"error": "Membresía inválida. Use basica o premium"}, status=400)

    if Cliente.objects.filter(username=username).exists():
        return JsonResponse({"error": "El username ya está en uso"}, status=400)

    if Cliente.objects.filter(email=email).exists():
        return JsonResponse({"error": "El email ya está en uso"}, status=400)

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(10)).decode("utf-8")

    cliente = Cliente.objects.create(
        nombre=nombre,
        apellidopaterno=apellidopaterno,
        apellidomaterno=data.get("apellidomaterno"),
        telefono=data.get("telefono"),
        username=username,
        email=email,
        password=password_hash,
        membresia=membresia,
    )

    return JsonResponse({
        "mensaje": "Cliente creado correctamente",
        "cliente": {
            "clicve": cliente.clicve,
            "nombre": cliente.nombre,
            "username": cliente.username,
            "membresia": cliente.membresia,
        }
    }, status=201)

@csrf_exempt
@require_POST
@requiere_rol("Administrador")
def crear_categoria_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    nombre = data.get("nombre")
    if not nombre:
        return JsonResponse({"error": "El nombre es obligatorio"}, status=400)

    if Categoria.objects.filter(nombre__iexact=nombre).exists():
        return JsonResponse({"error": "Ya existe una categoría con ese nombre"}, status=400)

    categoria = Categoria.objects.create(
        nombre=nombre,
        descripcion=data.get("descripcion"),
    )

    return JsonResponse({
        "mensaje": "Categoría creada correctamente",
        "categoria": {"catcve": categoria.catcve, "nombre": categoria.nombre}
    }, status=201)


@require_GET
@requiere_rol("Administrador", "Vendedor")
def listar_categorias_view(request):
    categorias = Categoria.objects.filter(estatus="activo")

    data = [
        {"catcve": c.catcve, "nombre": c.nombre, "descripcion": c.descripcion}
        for c in categorias
    ]

    return JsonResponse({"categorias": data}, status=200)


@csrf_exempt
@require_http_methods(["PUT", "PATCH", "DELETE"])
@requiere_rol("Administrador")
def actualizar_categoria_view(request, catcve):
    try:
        categoria = Categoria.objects.get(catcve=catcve)
    except Categoria.DoesNotExist:
        return JsonResponse({"error": "Categoría no encontrada"}, status=404)

    if request.method == "DELETE":
        if categoria.estatus == "inactivo":
            return JsonResponse({"error": "La categoría ya está inactiva"}, status=400)
        categoria.estatus = "inactivo"
        categoria.save()
        return JsonResponse({
            "mensaje": "Categoría eliminada correctamente (los productos existentes no se ven afectados)",
            "categoria": {"catcve": categoria.catcve, "nombre": categoria.nombre, "estatus": categoria.estatus}
        }, status=200)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    if request.method == "PUT" and not data.get("nombre"):
        return JsonResponse({"error": "PUT requiere el campo nombre"}, status=400)

    if "nombre" in data:
        if Categoria.objects.exclude(catcve=catcve).filter(nombre__iexact=data["nombre"]).exists():
            return JsonResponse({"error": "Ya existe otra categoría con ese nombre"}, status=400)
        categoria.nombre = data["nombre"]

    if "descripcion" in data:
        categoria.descripcion = data["descripcion"]

    categoria.save()

    return JsonResponse({
        "mensaje": "Categoría actualizada correctamente",
        "categoria": {"catcve": categoria.catcve, "nombre": categoria.nombre}
    }, status=200)

@csrf_exempt
@require_POST
@requiere_rol("Administrador", "Vendedor")
def crear_venta_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    # El vendedor de la venta SIEMPRE es quien tiene la sesión (JWT), nunca
    # un empcve que mande el cliente en el body: si se confiara en eso,
    # cualquiera con las dev tools o Postman podría registrar una venta a
    # nombre de otro empleado (o de un Administrador) con solo cambiar un
    # número en el request. Cualquier "empcve" que venga en el body se ignora.
    empcve = request.usuario_jwt.get("empcve")
    clicve = data.get("clicve")  # opcional, venta puede ser sin cliente registrado
    items = data.get("items")    # lista de {"procve": X, "cantidad": Y}

    if not empcve or not items or not isinstance(items, list) or len(items) == 0:
        return JsonResponse({"ok": False, "message": "Faltan campos obligatorios: items (lista no vacía)"}, status=400)

    try:
        empleado = Empleado.objects.get(empcve=empcve)
    except Empleado.DoesNotExist:
        return JsonResponse({"ok": False, "message": "El empleado indicado no existe"}, status=400)

    cliente = None
    if clicve:
        try:
            cliente = Cliente.objects.get(clicve=clicve)
        except Cliente.DoesNotExist:
            return JsonResponse({"ok": False, "message": "El cliente indicado no existe"}, status=400)

    tipo_entrega = data.get("tipo_entrega", "mostrador")
    if tipo_entrega not in ("mostrador", "domicilio"):
        return JsonResponse({"ok": False, "message": "tipo_entrega inválido. Use mostrador o domicilio"}, status=400)

    if tipo_entrega == "domicilio" and not data.get("direccion_entrega"):
        return JsonResponse({"ok": False, "message": "domicilio requiere direccion_entrega"}, status=400)

    # Validar cada item antes de tocar la base de datos
    productos_validados = []
    for item in items:
        procve = item.get("procve")
        cantidad = item.get("cantidad")

        if not procve or not cantidad or cantidad <= 0:
            return JsonResponse({"ok": False, "message": "Cada item requiere procve y cantidad > 0"}, status=400)

        try:
            producto = Producto.objects.get(procve=procve, estatus="activo")
        except Producto.DoesNotExist:
            return JsonResponse({"ok": False, "message": f"El producto {procve} no existe o está inactivo"}, status=400)

        productos_validados.append((producto, cantidad))

    try:
        with transaction.atomic():
            venta = Venta.objects.create(
                empcve=empleado,
                clicve=cliente,
                descripcion=data.get("descripcion"),
                metodo_pago=data.get("metodo_pago", "efectivo"),
                tipo_entrega=tipo_entrega,
                direccion_entrega=data.get("direccion_entrega"),
                codigo_postal=data.get("codigo_postal"),
            )

            for producto, cantidad in productos_validados:
                subtotal_linea = producto.precio * cantidad
                # Este INSERT dispara los triggers de PostgreSQL:
                # 1) trg_detalle_venta_stock -> CALL sp_disminuir_stock (puede lanzar excepción)
                # 2) trg_actualizar_total_venta -> recalcula venta.total y venta.subtotal
                DetalleVenta.objects.create(
                    procve=producto,
                    vencve=venta,
                    cantidad=cantidad,
                    precio=producto.precio,
                    subtotal=subtotal_linea,
                )

    except DatabaseError as e:
        # Aquí llega el RAISE EXCEPTION de sp_disminuir_stock cuando el stock es insuficiente
        mensaje = str(e).split("\n")[0]  # primera línea, evita el traceback completo de SQL
        return JsonResponse({"ok": False, "message": f"No se pudo completar la venta: {mensaje}"}, status=400)

    # El trigger trg_stock_movimiento ya registró el stock_anterior/actual
    # real de cada producto vendido; aquí solo completamos qué venta y
    # qué empleado lo causó (el trigger no lo sabe, solo ve el UPDATE).
    for producto, _cantidad in productos_validados:
        mov = Movimiento.objects.filter(procve=producto).order_by("-movcve").first()
        if mov and mov.referencia is None:
            mov.referencia = f"Venta V-{venta.vencve:04d}"
            mov.empcve = empleado
            mov.save()

    venta.refresh_from_db()

    detalles = DetalleVenta.objects.filter(vencve=venta)
    detalles_data = [
        {
            "detcve": d.detcve,
            "producto": d.procve.nombre,
            "cantidad": d.cantidad,
            "precio": str(d.precio),
            "subtotal": str(d.subtotal),
        }
        for d in detalles
    ]

    return JsonResponse({
        "ok": True,
        "mensaje": "Venta creada correctamente",
        "folio": f"V-{venta.vencve:04d}",
        "venta": {
            "vencve": venta.vencve,
            "total": str(venta.total),
            "subtotal": str(venta.subtotal),
            "empleado": empleado.nombre,
            "cliente": cliente.nombre if cliente else None,
            "detalles": detalles_data,
        }
    }, status=201)

@require_GET
@requiere_rol("Administrador", "Vendedor")
def listar_ventas_view(request):
    ventas = Venta.objects.filter(estatus="completada").select_related("empcve", "clicve")

    data = [
        {
            "vencve": v.vencve,
            "total": str(v.total),
            "subtotal": str(v.subtotal),
            "empleado": v.empcve.nombre,
            "cliente": v.clicve.nombre if v.clicve else None,
            "metodo_pago": v.metodo_pago,
            "tipo_entrega": v.tipo_entrega,
            "fecha": v.fecha,
        }
        for v in ventas
    ]

    return JsonResponse({"ventas": data}, status=200)

import random
import string
from datetime import timedelta
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def _buscar_usuario_por_email(email):
    """Busca en empleado y luego en cliente. Regresa (usuario, tipo) o (None, None)."""
    try:
        return Empleado.objects.get(email=email), "empleado"
    except Empleado.DoesNotExist:
        pass
    try:
        return Cliente.objects.get(email=email), "cliente"
    except Cliente.DoesNotExist:
        return None, None


@csrf_exempt
@require_POST
def forgot_password_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    correo = data.get("correo", "").strip()
    if not correo:
        return JsonResponse({"ok": False, "message": "El correo es obligatorio"}, status=400)

    usuario, tipo = _buscar_usuario_por_email(correo)

    # Por seguridad, no revelamos si el correo existe o no.
    # Siempre respondemos "ok" aunque no exista, pero solo mandamos
    # el correo real si sí encontramos al usuario.
    if usuario:
        codigo = "".join(random.choices(string.digits, k=6))
        usuario.reset_token = codigo
        usuario.reset_token_expira = datetime.utcnow() + timedelta(minutes=10)
        usuario.save()

        html_content = render_to_string("emails/codigo_recuperacion.html", {
            "nombre": usuario.nombre,
            "codigo": codigo,
        })
        texto_plano = strip_tags(html_content)

        send_mail(
            subject="Código de recuperación — Ferretería",
            message=texto_plano,
            from_email=None,  # usa DEFAULT_FROM_EMAIL
            recipient_list=[correo],
            html_message=html_content,
            fail_silently=False,
        )

    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def verify_code_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    correo = data.get("correo", "").strip()
    codigo = data.get("codigo", "").strip()

    usuario, tipo = _buscar_usuario_por_email(correo)

    if not usuario or usuario.reset_token != codigo:
        return JsonResponse({"ok": False, "message": "Código incorrecto o expirado."})

    if usuario.reset_token_expira < datetime.utcnow():
        return JsonResponse({"ok": False, "message": "El código ha expirado."})

    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def reset_password_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    correo = data.get("correo", "").strip()
    codigo = data.get("codigo", "").strip()
    nueva_password = data.get("nueva_password", "")

    if len(nueva_password) < 6:
        return JsonResponse({"ok": False, "message": "La contraseña debe tener al menos 6 caracteres"})

    usuario, tipo = _buscar_usuario_por_email(correo)

    if not usuario or usuario.reset_token != codigo:
        return JsonResponse({"ok": False, "message": "Código inválido."})

    if usuario.reset_token_expira < datetime.utcnow():
        return JsonResponse({"ok": False, "message": "El código ha expirado, solicita uno nuevo."})

    usuario.password = bcrypt.hashpw(nueva_password.encode("utf-8"), bcrypt.gensalt(10)).decode("utf-8")
    usuario.reset_token = None
    usuario.reset_token_expira = None
    usuario.save()

    return JsonResponse({"ok": True})

# ── Helpers de alertas de stock (usados por dashboard, inventario, ──
# productos y alertas.html) ──────────────────────────────────────
def _evaluar_alerta_tipo(stock_actual, stock_minimo):
    """
    Regla única para decidir si un nivel de stock amerita alerta:
      - Agotado (stock_actual == 0) => SIEMPRE 'Crítica', sin importar
        cuál sea el stock_minimo (antes, si stock_minimo también era 0,
        "0 < 0" daba False y el producto agotado no generaba alerta).
      - Bajo mínimo (0 < stock_actual < stock_minimo) => 'Advertencia'.
      - Cualquier otro caso => None (no amerita alerta).
    """
    if stock_actual == 0:
        return "Crítica"
    if stock_actual < stock_minimo:
        return "Advertencia"
    return None


def _sincronizar_alertas():
    """
    Recorre el stock de todos los productos y deja la tabla Alerta al
    corriente:
      - Si un producto amerita alerta (agotado o bajo mínimo) y no tiene
        ya una alerta abierta (Pendiente/Notificada) de ese mismo tipo,
        crea una nueva alerta Pendiente.
      - Si un producto tenía una alerta abierta de OTRO tipo (ej. pasó de
        Advertencia a Crítica al venderse más), cierra la vieja como
        Resuelta y abre una nueva del tipo correcto.
      - Si un producto ya no amerita alerta (se reabasteció por fuera del
        flujo normal, por ejemplo editando el stock a mano) y le había
        quedado una alerta abierta, la cierra sola como Resuelta.
    No duplica notificaciones: solo crea/cierra registros, nunca reenvía
    el correo (eso solo pasa cuando alguien aprieta "Notificar").
    """
    for s in Stock.objects.select_related("procve"):
        tipo_actual = _evaluar_alerta_tipo(s.stock_actual, s.stock_minimo)
        abiertas = Alerta.objects.filter(procve=s.procve, estado__in=["Pendiente", "Notificada"])

        if tipo_actual is None:
            if abiertas.exists():
                abiertas.update(estado="Resuelta", fecha_resolucion=timezone.now())
            continue

        if abiertas.filter(tipo=tipo_actual).exists():
            continue  # ya hay una alerta abierta correcta para este producto

        abiertas.exclude(tipo=tipo_actual).update(estado="Resuelta", fecha_resolucion=timezone.now())
        Alerta.objects.create(
            procve=s.procve,
            tipo=tipo_actual,
            estado="Pendiente",
            descripcion=f"Quedan {s.stock_actual} unidades (mínimo {s.stock_minimo})",
        )

#stock bajo, ventas del mes, total de productos, total de usuarios
#/dashboard/stats  las 4 tarjetas de arriba:
@require_GET
@requiere_rol("Administrador", "Vendedor")
def dashboard_stats_view(request):
    _sincronizar_alertas()

    total_productos = Producto.objects.filter(estatus="activo").count()

    hoy = date.today()
    ventas_mes = Venta.objects.filter(estatus="completada", fecha__year=hoy.year, fecha__month=hoy.month)
    ventas_mes_total = ventas_mes.aggregate(suma=Sum("total"))["suma"] or 0
    ventas_mes_count = ventas_mes.count()

    stock_bajo = Stock.objects.filter(stock_actual__gt=0, stock_actual__lt=F("stock_minimo")).count()
    agotados = Stock.objects.filter(stock_actual=0).count()
    productos_disponibles = Stock.objects.filter(stock_actual__gt=0).count()
    # Mismo número que va a ver el usuario en la campanita en TODAS las
    # pantallas y en la tabla de alertas.html: alertas abiertas (Pendiente
    # o Notificada) en la tabla real, no un recálculo aparte.
    alertas_abiertas = Alerta.objects.filter(estado__in=["Pendiente", "Notificada"]).count()

    total_usuarios = Empleado.objects.filter(estatus="activo").count()

    return JsonResponse({
        "ok": True,
        "data": {
            "totalProductos": total_productos,
            "productosDisponibles": productos_disponibles,
            "ventasMes": float(ventas_mes_total),
            "totalVentasMes": ventas_mes_count,
            "alertasPendientes": alertas_abiertas,
            "stockBajo": stock_bajo,
            "agotados": agotados,
            "totalUsuarios": total_usuarios,
        }
    })
#/dashboard/ventas-semana la gráfica:
@require_GET
@requiere_rol("Administrador", "Vendedor")
def ventas_semana_view(request):
    hoy = date.today()
    dias = [hoy - timedelta(days=i) for i in range(6, -1, -1)]
    nombres_dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    data = []
    for dia in dias:
        total = Venta.objects.filter(fecha=dia, estatus="completada").aggregate(s=Sum("total"))["s"] or 0
        data.append({"dia": nombres_dias[dia.weekday()], "total": float(total)})

    return JsonResponse({"ok": True, "data": data})

#/productos/stock-bajo — la barra de stock bajo:
@require_GET
@requiere_rol("Administrador", "Vendedor")
def stock_bajo_view(request):
    stocks = (
        Stock.objects.filter(Q(stock_actual=0) | Q(stock_actual__lt=F("stock_minimo")))
        .select_related("procve")
        .order_by("stock_actual")
    )

    data = [
        {"nombre": s.procve.nombre, "stock": s.stock_actual, "stock_minimo": s.stock_minimo}
        for s in stocks
    ]
    return JsonResponse({"ok": True, "data": data})

#/ventas con ?limit= — tabla de ventas recientes:
@require_GET
@requiere_rol("Administrador", "Vendedor")
def ventas_recientes_view(request):
    limit = int(request.GET.get("limit", 10))
    ventas = Venta.objects.select_related("clicve").order_by("-vencve")[:limit]

    data = [
        {
            "folio": f"V-{v.vencve:04d}",
            "cliente": v.clicve.nombre if v.clicve else "Mostrador",
            "total": float(v.total),
            "estado": "Pagada" if v.estatus == "completada" else v.estatus.capitalize(),
        }
        for v in ventas
    ]
    return JsonResponse({"ok": True, "data": data})

#/alertas con ?page=&limit=&tipo=&estado=&search= — lista de alertas.
# A diferencia de antes, esto SÍ lee y escribe la tabla Alerta real (antes
# se recalculaba al vuelo desde Stock y nunca se guardaba nada, por lo que
# nunca había un "id" para poder notificar o resolver una alerta, ni un
# historial real de Resueltas).
@require_GET
@requiere_rol("Administrador", "Vendedor")
def alertas_view(request):
    _sincronizar_alertas()

    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))
    tipo = request.GET.get("tipo", "").strip()
    estado = request.GET.get("estado", "").strip()
    search = request.GET.get("search", "").strip()

    qs = Alerta.objects.select_related("procve")
    if tipo:
        qs = qs.filter(tipo=tipo)
    if estado:
        qs = qs.filter(estado=estado)
    if search:
        qs = qs.filter(procve__nombre__icontains=search)

    qs = qs.order_by("-fecha_creacion")
    total = qs.count()
    start = (page - 1) * limit
    alertas = qs[start:start + limit]

    data = [
        {
            "id": a.alertcve,
            "created_at": a.fecha_creacion,
            "tipo": a.tipo,
            "nombre": "Sin stock" if a.tipo == "Crítica" else "Stock bajo",
            "producto_nombre": a.procve.nombre if a.procve else None,
            "descripcion": a.descripcion,
            "estado": a.estado,
        }
        for a in alertas
    ]
    return JsonResponse({"ok": True, "data": data, "total": total})


# /alertas/<id>/notificar — envía el correo de aviso (API externa: Gmail SMTP
# ya configurado en settings.py) y pasa la alerta a estado 'Notificada'.
# Si ya fue notificada o resuelta, NO reenvía (evita duplicar avisos).
@csrf_exempt
@require_POST
@requiere_rol("Administrador")
def alerta_notificar_view(request, alertcve):
    try:
        alerta = Alerta.objects.select_related("procve").get(alertcve=alertcve)
    except Alerta.DoesNotExist:
        return JsonResponse({"ok": False, "message": "Alerta no encontrada"}, status=404)

    if alerta.estado != "Pendiente":
        return JsonResponse({
            "ok": True,
            "message": f"Esta alerta ya está en estado '{alerta.estado}'; no se reenvía la notificación."
        })

    destinatarios = list(
        Empleado.objects.filter(rol="Administrador", estatus="activo").values_list("email", flat=True)
    )
    if not destinatarios:
        return JsonResponse({"ok": False, "message": "No hay administradores activos con correo registrado"}, status=400)

    asunto = f"[Ferretería] Alerta de stock — {alerta.procve.nombre}"
    cuerpo = (
        f"Producto: {alerta.procve.nombre}\n"
        f"Tipo de alerta: {alerta.tipo}\n"
        f"Detalle: {alerta.descripcion}\n"
    )

    try:
        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=None,  # usa DEFAULT_FROM_EMAIL
            recipient_list=destinatarios,
            fail_silently=False,
        )
    except Exception as e:
        return JsonResponse({"ok": False, "message": f"No se pudo enviar el correo: {e}"}, status=502)

    alerta.estado = "Notificada"
    alerta.fecha_notificacion = timezone.now()
    alerta.save()

    return JsonResponse({"ok": True, "message": "Notificación enviada correctamente"})


# /alertas/<id>/resolver — reabastece el producto (sp_abastecer_stock, ya
# existente en la BD) y pasa la alerta a 'Resuelta'. Si no se manda
# "cantidad" en el body, reabastece justo lo necesario para salir del
# mínimo de stock.
@csrf_exempt
@require_http_methods(["PATCH"])
@requiere_rol("Administrador")
def alerta_resolver_view(request, alertcve):
    try:
        alerta = Alerta.objects.select_related("procve").get(alertcve=alertcve)
    except Alerta.DoesNotExist:
        return JsonResponse({"ok": False, "message": "Alerta no encontrada"}, status=404)

    if alerta.estado == "Resuelta":
        return JsonResponse({"ok": True, "message": "Esta alerta ya estaba resuelta"})

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    try:
        stock = Stock.objects.get(procve=alerta.procve)
    except Stock.DoesNotExist:
        return JsonResponse({"ok": False, "message": "No existe registro de stock para este producto"}, status=400)

    cantidad = body.get("cantidad")
    if cantidad is None:
        cantidad = max(stock.stock_minimo - stock.stock_actual, 1)
    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "message": "cantidad debe ser un entero mayor a 0"}, status=400)

    with connection.cursor() as cursor:
        cursor.execute("CALL sp_abastecer_stock(%s, %s)", [alerta.procve_id, cantidad])

    # Igual que en ventas: el trigger ya guardó el antes/después real,
    # solo completamos de dónde vino este movimiento.
    mov = Movimiento.objects.filter(procve_id=alerta.procve_id).order_by("-movcve").first()
    if mov and mov.referencia is None:
        mov.referencia = f"Reabastecimiento (Alerta #{alerta.alertcve} resuelta)"
        mov.empcve_id = request.usuario_jwt.get("empcve")
        mov.save()

    alerta.estado = "Resuelta"
    alerta.fecha_resolucion = timezone.now()
    alerta.save()

    stock.refresh_from_db()

    return JsonResponse({
        "ok": True,
        "message": "Alerta resuelta y stock reabastecido",
        "cantidad_reabastecida": cantidad,
        "stock_actual": stock.stock_actual,
    })

# /categorias con conteo — para la dona de "Productos por categoría":
@csrf_exempt
@require_http_methods(["GET", "POST"])
@requiere_rol("Administrador", "Vendedor")
def categorias_con_conteo_view(request):
    if request.method == "GET":
        categorias = Categoria.objects.filter(estatus="activo").annotate(
            total_productos=Count("producto", filter=Q(producto__estatus="activo"))
        )
        data = [
            {"id": c.catcve, "nombre": c.nombre, "total_productos": c.total_productos}
            for c in categorias
        ]
        return JsonResponse({"ok": True, "data": data})

    # POST — solo Administrador
    if request.usuario_jwt.get("rol") != "Administrador":
        return JsonResponse({"ok": False, "message": "No tienes permiso para crear categorías"}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    nombre = data.get("nombre", "").strip()
    if not nombre:
        return JsonResponse({"ok": False, "message": "El nombre es obligatorio"}, status=400)
    if Categoria.objects.filter(nombre__iexact=nombre).exists():
        return JsonResponse({"ok": False, "message": "Ya existe una categoría con ese nombre"}, status=400)

    categoria = Categoria.objects.create(nombre=nombre)
    return JsonResponse({"ok": True, "data": {"id": categoria.catcve, "nombre": categoria.nombre}})

# /productos/mas-vendidos/ — lista de productos más vendidos:
@require_GET
@requiere_rol("Administrador", "Vendedor")
def productos_mas_vendidos_view(request):
    limit = int(request.GET.get("limit", 6))

    top = (
        DetalleVenta.objects
        .filter(estatus="activo")
        .values("procve__nombre")
        .annotate(total_vendido=Sum("cantidad"))
        .order_by("-total_vendido")[:limit]
    )

    data = [
        {"nombre": item["procve__nombre"], "total_vendido": item["total_vendido"]}
        for item in top
    ]

    return JsonResponse({"ok": True, "data": data})
#/usuarios con ?page=1&limit=8&search=&rol=&estado= — tabla de usuarios:
@csrf_exempt
@require_http_methods(["GET", "POST"])
@requiere_rol("Administrador")
def usuarios_view(request):
    if request.method == "GET":
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 8))
        search = request.GET.get("search", "").strip()
        rol = request.GET.get("rol", "").strip()
        estado = request.GET.get("estado", "").strip()

        qs = Empleado.objects.select_related("surcve")

        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(apellidopaterno__icontains=search) |
                Q(apellidomaterno__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search)
            )
        if rol:
            qs = qs.filter(rol=rol)
        if estado:
            qs = qs.filter(estatus=estado.lower())

        total = qs.count()
        start = (page - 1) * limit
        empleados = qs.order_by("empcve")[start:start + limit]

        data = [
            {
                "id": e.empcve,
                "nombre": f"{e.nombre} {e.apellidopaterno}".strip(),
                # Campos individuales para que el modal de edición no tenga
                # que volver a adivinar dónde corta el nombre completo.
                "nombre_solo": e.nombre,
                "apellidopaterno": e.apellidopaterno,
                "apellidomaterno": e.apellidomaterno,
                "usuario": e.username,
                "correo": e.email,
                "rol": e.rol,
                "estado": e.estatus.capitalize(),
                "descripcion": e.descripcion,
                "direccion": e.direccion,
                "codigopostal": e.codigopostal,
                "surcursal_id": e.surcve_id,
                "surcursal": f"{e.surcve.municipio} — {e.surcve.localidad}" if e.surcve else None,
            }
            for e in empleados
        ]
        return JsonResponse({"ok": True, "data": data, "total": total})

    # POST: crear usuario
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    nombre = data.get("nombre", "").strip()
    apellidopaterno = data.get("apellidopaterno", "").strip()
    apellidomaterno = data.get("apellidomaterno", "").strip()
    usuario = data.get("usuario", "").strip()
    correo = data.get("correo", "").strip()
    password = data.get("password", "")
    rol = data.get("rol", "Vendedor")
    estado = data.get("estado", "Activo")
    descripcion = data.get("descripcion", "").strip()
    direccion = data.get("direccion", "").strip()
    codigopostal = data.get("codigopostal", "").strip()
    surcursal_id = data.get("surcursal_id") or 1

    if not all([nombre, apellidopaterno, usuario, correo, password]):
        return JsonResponse({"ok": False, "message": "Nombre, apellido paterno, usuario, correo y contraseña son obligatorios"}, status=400)

    if rol not in ("Administrador", "Vendedor"):
        return JsonResponse({"ok": False, "message": "Rol inválido"}, status=400)

    if Empleado.objects.filter(username=usuario).exists():
        return JsonResponse({"ok": False, "message": "El usuario ya está en uso"}, status=400)
    if Empleado.objects.filter(email=correo).exists():
        return JsonResponse({"ok": False, "message": "El correo ya está en uso"}, status=400)

    try:
        sucursal = Surcusal.objects.get(surcve=surcursal_id)
    except Surcusal.DoesNotExist:
        return JsonResponse({"ok": False, "message": "La sucursal indicada no existe"}, status=400)

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(10)).decode("utf-8")

    try:
        empleado = Empleado.objects.create(
            surcve=sucursal,
            nombre=nombre,
            apellidopaterno=apellidopaterno,
            apellidomaterno=apellidomaterno or None,
            rol=rol,
            descripcion=descripcion or None,
            direccion=direccion or None,
            codigopostal=codigopostal or None,
            username=usuario,
            email=correo,
            password=password_hash,
            estatus=estado.lower(),
        )
    except DatabaseError as e:
        # Ej: violación de un CHECK/constraint de la BD (usuario/correo duplicado, etc.)
        mensaje = str(e).split("\n")[0]
        return JsonResponse({"ok": False, "message": f"No se pudo crear el usuario: {mensaje}"}, status=400)

    return JsonResponse({"ok": True, "data": {"id": empleado.empcve}})


@csrf_exempt
@require_http_methods(["PUT", "DELETE"])
@requiere_rol("Administrador")
def usuario_detail_view(request, empcve):
    try:
        empleado = Empleado.objects.get(empcve=empcve)
    except Empleado.DoesNotExist:
        return JsonResponse({"ok": False, "message": "Usuario no encontrado"}, status=404)

    if request.method == "DELETE":
        empleado.estatus = "inactivo"
        empleado.save()
        return JsonResponse({"ok": True})

    # PUT: actualizar
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    if data.get("nombre"):
        empleado.nombre = data["nombre"].strip()
    if data.get("apellidopaterno"):
        empleado.apellidopaterno = data["apellidopaterno"].strip()
    if "apellidomaterno" in data:
        empleado.apellidomaterno = data["apellidomaterno"].strip() or None
    if "descripcion" in data:
        empleado.descripcion = data["descripcion"].strip() or None
    if "direccion" in data:
        empleado.direccion = data["direccion"].strip() or None
    if "codigopostal" in data:
        empleado.codigopostal = data["codigopostal"].strip() or None
    if data.get("surcursal_id"):
        try:
            empleado.surcve = Surcusal.objects.get(surcve=data["surcursal_id"])
        except Surcusal.DoesNotExist:
            return JsonResponse({"ok": False, "message": "La sucursal indicada no existe"}, status=400)

    if data.get("usuario"):
        nuevo_usuario = data["usuario"].strip()
        if Empleado.objects.exclude(empcve=empcve).filter(username=nuevo_usuario).exists():
            return JsonResponse({"ok": False, "message": "El usuario ya está en uso"}, status=400)
        empleado.username = nuevo_usuario

    if data.get("correo"):
        nuevo_correo = data["correo"].strip()
        if Empleado.objects.exclude(empcve=empcve).filter(email=nuevo_correo).exists():
            return JsonResponse({"ok": False, "message": "El correo ya está en uso"}, status=400)
        empleado.email = nuevo_correo

    if data.get("rol"):
        if data["rol"] not in ("Administrador", "Vendedor"):
            return JsonResponse({"ok": False, "message": "Rol inválido"}, status=400)
        empleado.rol = data["rol"]

    if data.get("estado"):
        empleado.estatus = data["estado"].lower()

    if data.get("password"):
        empleado.password = bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt(10)).decode("utf-8")

    try:
        empleado.save()
    except DatabaseError as e:
        mensaje = str(e).split("\n")[0]
        return JsonResponse({"ok": False, "message": f"No se pudo actualizar el usuario: {mensaje}"}, status=400)

    return JsonResponse({"ok": True})

#/sucursales/ — para el selector de sucursal en el modal de usuarios:
@require_GET
@requiere_rol("Administrador")
def sucursales_view(request):
    sucursales = Surcusal.objects.all().order_by("surcve")
    data = [
        {"id": s.surcve, "nombre": f"{s.municipio} — {s.localidad}"}
        for s in sucursales
    ]
    return JsonResponse({"ok": True, "data": data})

#/productos con ?page=1&limit=8&search=&categoria=&estado= — tabla de productos:
@csrf_exempt
@require_http_methods(["GET", "POST"])
@requiere_rol("Administrador", "Vendedor")
def productos_ui_view(request):
    if request.method == "GET":
        # GET: cualquiera de los 3 roles puede ver el listado
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 8))
        search = request.GET.get("search", "").strip()
        categoria = request.GET.get("categoria", "").strip()
        estado = request.GET.get("estado", "").strip()

        qs = Producto.objects.select_related("catcve")

        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(modelo__icontains=search))
        if categoria:
            qs = qs.filter(catcve__nombre=categoria)
        if estado:
            qs = qs.filter(estatus=estado.lower())

        total = qs.count()
        start = (page - 1) * limit
        productos = qs.order_by("procve")[start:start + limit]

        stocks = {s.procve_id: s for s in Stock.objects.filter(procve__in=productos)}

        data = []
        for p in productos:
            s = stocks.get(p.procve)
            data.append({
                "id": p.procve,
                "codigo": p.modelo or f"PROD-{p.procve:04d}",
                "nombre": p.nombre,
                "categoria": p.catcve.nombre if p.catcve else None,
                "categoria_id": p.catcve_id,
                "precio": float(p.precio),
                "stock": s.stock_actual if s else 0,
                "stock_minimo": s.stock_minimo if s else 0,
                "estado": p.estatus.capitalize(),
                "descripcion": p.descripcion,
            })
        return JsonResponse({"ok": True, "data": data, "total": total})

    # POST: crear producto — SOLO Administrador
    if request.usuario_jwt.get("rol") != "Administrador":
        return JsonResponse({"ok": False, "message": "No tienes permiso para crear productos"}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)
    nombre = data.get("nombre", "").strip()
    codigo = data.get("codigo", "").strip()
    categoria_id = data.get("categoria_id")
    precio = data.get("precio")
    stock_inicial = data.get("stock", 0)
    stock_minimo = data.get("stock_minimo", 5)
    estado = data.get("estado", "Activo")
    descripcion = data.get("descripcion", "")

    if not nombre or not codigo or not categoria_id or precio is None:
        return JsonResponse({"ok": False, "message": "Nombre, código, categoría y precio son obligatorios"}, status=400)

    try:
        precio = float(precio)
        if precio <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "message": "El precio debe ser un número mayor a 0"}, status=400)

    try:
        stock_inicial = int(stock_inicial)
        stock_minimo = int(stock_minimo)
        if stock_inicial < 0 or stock_minimo < 0:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "message": "Stock inicial y stock mínimo deben ser un número positivo (0 o más)"}, status=400)

    try:
        categoria = Categoria.objects.get(catcve=categoria_id)
    except Categoria.DoesNotExist:
        return JsonResponse({"ok": False, "message": "La categoría indicada no existe"}, status=400)

    if Producto.objects.filter(modelo__iexact=codigo).exists():
        return JsonResponse({"ok": False, "message": f"Ya existe un producto con el código '{codigo}'"}, status=400)

    # Atómico: si por lo que sea falla la creación del Stock, el Producto
    # tampoco se queda a medias creado (eso es justo lo que dejaba
    # productos "fantasma" sin stock, invisibles para Alertas/Dashboard).
    with transaction.atomic():
        producto = Producto.objects.create(
            catcve=categoria,
            nombre=nombre,
            modelo=codigo,
            precio=precio,
            descripcion=descripcion,
            estatus=estado.lower(),
        )

        Stock.objects.create(
            procve=producto,
            stock_actual=stock_inicial,
            stock_minimo=stock_minimo,
            estatus="alerta" if _evaluar_alerta_tipo(stock_inicial, stock_minimo) else "normal",
        )

    return JsonResponse({"ok": True, "data": {"id": producto.procve}})
#
@csrf_exempt
@require_http_methods(["PUT", "DELETE"])
@requiere_rol("Administrador", "Vendedor")
def producto_ui_detail_view(request, procve):
    # Solo Administrador puede editar o eliminar
    if request.usuario_jwt.get("rol") != "Administrador":
        return JsonResponse({"ok": False, "message": "No tienes permiso para modificar productos"}, status=403)

    try:
        producto = Producto.objects.get(procve=procve)
    except Producto.DoesNotExist:
        return JsonResponse({"ok": False, "message": "Producto no encontrado"}, status=404)

    if request.method == "DELETE":
        producto.estatus = "inactivo"
        producto.save()
        return JsonResponse({"ok": True})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "JSON inválido"}, status=400)

    if data.get("nombre"):
        producto.nombre = data["nombre"]
    if data.get("codigo"):
        nuevo_codigo = data["codigo"]
        if Producto.objects.exclude(procve=procve).filter(modelo__iexact=nuevo_codigo).exists():
            return JsonResponse({"ok": False, "message": f"Ya existe un producto con el código '{nuevo_codigo}'"}, status=400)
        producto.modelo = nuevo_codigo
    if data.get("categoria_id"):
        try:
            producto.catcve = Categoria.objects.get(catcve=data["categoria_id"])
        except Categoria.DoesNotExist:
            return JsonResponse({"ok": False, "message": "La categoría indicada no existe"}, status=400)
    if data.get("precio") is not None:
        try:
            precio = float(data["precio"])
            if precio <= 0:
                raise ValueError
            producto.precio = precio
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "message": "El precio debe ser un número mayor a 0"}, status=400)
    if "descripcion" in data:
        producto.descripcion = data["descripcion"]
    if data.get("estado"):
        producto.estatus = data["estado"].lower()

    producto.save()

    if "stock" in data or "stock_minimo" in data:
        try:
            nuevo_stock = int(data["stock"]) if "stock" in data else None
            nuevo_minimo = int(data["stock_minimo"]) if "stock_minimo" in data else None
            if (nuevo_stock is not None and nuevo_stock < 0) or (nuevo_minimo is not None and nuevo_minimo < 0):
                raise ValueError
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "message": "Stock actual y stock mínimo deben ser un número positivo (0 o más)"}, status=400)

        # .filter().first() en vez de get_or_create: si por datos viejos
        # llegara a haber más de un registro de Stock para este producto,
        # get_or_create truena con MultipleObjectsReturned. Tomamos el más
        # reciente y de perdida no se cae la edición del producto.
        stock = Stock.objects.filter(procve=producto).order_by("-stoccve").first()
        if stock is None:
            stock = Stock.objects.create(procve=producto, stock_actual=0, stock_minimo=5)
        if nuevo_stock is not None:
            stock.stock_actual = nuevo_stock
        if nuevo_minimo is not None:
            stock.stock_minimo = nuevo_minimo
        stock.estatus = "alerta" if _evaluar_alerta_tipo(stock.stock_actual, stock.stock_minimo) else "normal"
        stock.save()

        # Si el guardado sí cambió stock_actual, el trigger ya generó su
        # movimiento; solo le ponemos de dónde vino.
        mov = Movimiento.objects.filter(procve=producto).order_by("-movcve").first()
        if mov and mov.referencia is None:
            mov.referencia = "Ajuste manual desde Productos"
            mov.empcve_id = request.usuario_jwt.get("empcve")
            mov.save()

    return JsonResponse({"ok": True})

# ── Reportes (reportes.html) ──────────────────────────────────
# Endpoint dedicado y EXCLUSIVO de Administrador. No reutiliza
# /productos, /ventas ni /dashboard/stats a propósito: esos endpoints
# permiten Vendedor porque los necesita para productos.html/ventas.html,
# y reutilizarlos aquí habría dejado un hueco (un Vendedor podría pedir
# "reportes" llamando esas rutas compartidas directamente). Este endpoint
# corre la misma consulta pero detrás de su propio candado de rol.
@require_GET
@requiere_rol("Administrador")
def reportes_view(request):
    """
    GET /api/reportes/?tipo=inventario|ventas|stock-bajo|movimientos|resumen
    Por defecto (sin ?tipo o tipo=resumen) regresa las 3 tarjetas resumen.
    """
    tipo = request.GET.get("tipo", "resumen").strip().lower()
    limit = int(request.GET.get("limit", 200))

    if tipo == "inventario":
        productos = Producto.objects.filter(estatus="activo").select_related("catcve").order_by("procve")[:limit]
        stocks = {s.procve_id: s for s in Stock.objects.filter(procve__in=productos)}
        data = [
            {
                "id": p.procve,
                "codigo": p.modelo or f"PROD-{p.procve:04d}",
                "nombre": p.nombre,
                "categoria": p.catcve.nombre if p.catcve else None,
                "precio": float(p.precio),
                "stock": stocks[p.procve].stock_actual if p.procve in stocks else 0,
                "stock_minimo": stocks[p.procve].stock_minimo if p.procve in stocks else 0,
            }
            for p in productos
        ]
        return JsonResponse({"ok": True, "tipo": tipo, "data": data, "total": len(data)})

    if tipo == "ventas":
        ventas = Venta.objects.filter(estatus="completada").select_related("empcve", "clicve").order_by("-vencve")[:limit]
        data = [
            {
                "vencve": v.vencve,
                "total": float(v.total),
                "empleado": v.empcve.nombre,
                "cliente": v.clicve.nombre if v.clicve else None,
                "metodo_pago": v.metodo_pago,
                "tipo_entrega": v.tipo_entrega,
                "fecha": v.fecha,
            }
            for v in ventas
        ]
        return JsonResponse({"ok": True, "tipo": tipo, "data": data, "total": len(data)})

    if tipo == "stock-bajo":
        stocks = (
            Stock.objects.filter(Q(stock_actual=0) | Q(stock_actual__lt=F("stock_minimo")))
            .select_related("procve").order_by("stock_actual")[:limit]
        )
        data = [
            {"nombre": s.procve.nombre, "stock": s.stock_actual, "stock_minimo": s.stock_minimo}
            for s in stocks
        ]
        return JsonResponse({"ok": True, "tipo": tipo, "data": data, "total": len(data)})

    if tipo == "movimientos":
        data = _obtener_movimientos()[:limit]
        return JsonResponse({"ok": True, "tipo": tipo, "data": data, "total": len(data)})

    # tipo == "resumen" (default): las 3 tarjetas resumen de reportes.html
    hoy = date.today()
    ventas_mes = Venta.objects.filter(estatus="completada", fecha__year=hoy.year, fecha__month=hoy.month)
    ventas_mes_total = ventas_mes.aggregate(suma=Sum("total"))["suma"] or 0
    ventas_mes_count = ventas_mes.count()
    total_productos = Producto.objects.filter(estatus="activo").count()
    stock_bajo = Stock.objects.filter(stock_actual__gt=0, stock_actual__lt=F("stock_minimo")).count()
    agotados = Stock.objects.filter(stock_actual=0).count()

    return JsonResponse({
        "ok": True,
        "tipo": "resumen",
        "data": {
            "totalProductos": total_productos,
            "productosDisponibles": total_productos - agotados,
            "stockBajo": stock_bajo,
            "agotados": agotados,
            "totalVentasMes": ventas_mes_count,
            "ventasMes": float(ventas_mes_total),
            "alertasPendientes": stock_bajo + agotados,
        }
    })

# ── Movimientos de inventario (movimientos.html, ambos roles) ─
# Decisión del equipo: NO se agrega una tabla 'movimiento' nueva para no
# tocar el modelo ER/BD ya definido. Esta es una primera versión que
# reconstruye el historial con lo que ya existe:
#   - "salida": cada línea de detalle_venta (sí tiene fecha real y es
#     un registro histórico confiable, no se pierde con el tiempo).
#   - "ajuste": el nivel de stock actual por producto (stock.fecha se
#     sobrescribe en cada sp_disminuir_stock/sp_abastecer_stock, así que
#     esto NO es un historial real de entradas, solo la última foto
#     conocida). Se etiqueta como tal para no aparentar ser algo que no es.
# Si más adelante se necesita un historial completo y confiable de
# entradas individuales, ahí sí conviene la tabla 'movimiento' con
# trigger, tal como se discutió.
def _obtener_movimientos(search="", tipo_filtro=""):
    """
    Historial real de stock, respaldado por la tabla `movimiento` (ver
    database/migracion_tabla_movimiento.sql). Cada cambio de
    stock.stock_actual —venta, reabastecimiento o edición manual—
    dispara un trigger en Postgres que guarda ahí mismo el stock_anterior
    y stock_actual reales, así que ya no hay que reconstruir nada al
    vuelo ni adivinar "última foto conocida".
    """
    qs = Movimiento.objects.select_related("procve", "procve__catcve", "empcve")

    if tipo_filtro:
        qs = qs.filter(tipo=tipo_filtro)
    if search:
        qs = qs.filter(
            Q(procve__nombre__icontains=search)
            | Q(procve__modelo__icontains=search)
            | Q(referencia__icontains=search)
        )

    qs = qs.order_by("-fecha", "-movcve")

    movimientos = []
    for m in qs:
        p = m.procve
        movimientos.append({
            "tipo": m.tipo,
            "cantidad": m.cantidad,
            "created_at": m.fecha,
            "producto_nombre": p.nombre,
            "producto_codigo": p.modelo or f"PROD-{p.procve:04d}",
            "categoria": p.catcve.nombre if p.catcve else None,
            "referencia": m.referencia or "—",
            "stock_anterior": m.stock_anterior,
            "stock_actual": m.stock_actual,
            "usuario_nombre": f"{m.empcve.nombre} {m.empcve.apellidopaterno}".strip() if m.empcve else None,
        })

    return movimientos


@require_GET
@requiere_rol("Administrador", "Vendedor")
def movimientos_view(request):
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))
    search = request.GET.get("search", "").strip()
    tipo_filtro = request.GET.get("tipo", "").strip()

    todos = _obtener_movimientos(search=search, tipo_filtro=tipo_filtro)
    total = len(todos)
    start = (page - 1) * limit
    data = todos[start:start + limit]

    return JsonResponse({"ok": True, "data": data, "total": total})