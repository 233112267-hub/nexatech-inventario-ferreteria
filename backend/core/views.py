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
from django.db import transaction, DatabaseError
from .models import Empleado, Cliente
from .models import Empleado, Cliente, Producto, Categoria, Surcusal, Venta, DetalleVenta
from .models import Empleado, Cliente, Producto, Categoria, Surcusal
from .jwt_utils import generar_jwt
#vista de modelo
from django.db.models import Sum, Count, Q
from datetime import date, timedelta
from .models import Stock

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

    try:
        precio = float(precio)
    except (TypeError, ValueError):
        return JsonResponse({"error": "El precio debe ser un número válido"}, status=400)

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
        return JsonResponse({"error": "JSON inválido"}, status=400)

    empcve = data.get("empcve")
    clicve = data.get("clicve")  # opcional, venta puede ser sin cliente registrado
    items = data.get("items")    # lista de {"procve": X, "cantidad": Y}

    if not empcve or not items or not isinstance(items, list) or len(items) == 0:
        return JsonResponse({"error": "Faltan campos obligatorios: empcve, items (lista no vacía)"}, status=400)

    try:
        empleado = Empleado.objects.get(empcve=empcve)
    except Empleado.DoesNotExist:
        return JsonResponse({"error": "El empleado indicado no existe"}, status=400)

    cliente = None
    if clicve:
        try:
            cliente = Cliente.objects.get(clicve=clicve)
        except Cliente.DoesNotExist:
            return JsonResponse({"error": "El cliente indicado no existe"}, status=400)

    tipo_entrega = data.get("tipo_entrega", "mostrador")
    if tipo_entrega not in ("mostrador", "domicilio"):
        return JsonResponse({"error": "tipo_entrega inválido. Use mostrador o domicilio"}, status=400)

    if tipo_entrega == "domicilio" and not data.get("direccion_entrega"):
        return JsonResponse({"error": "domicilio requiere direccion_entrega"}, status=400)

    # Validar cada item antes de tocar la base de datos
    productos_validados = []
    for item in items:
        procve = item.get("procve")
        cantidad = item.get("cantidad")

        if not procve or not cantidad or cantidad <= 0:
            return JsonResponse({"error": "Cada item requiere procve y cantidad > 0"}, status=400)

        try:
            producto = Producto.objects.get(procve=procve, estatus="activo")
        except Producto.DoesNotExist:
            return JsonResponse({"error": f"El producto {procve} no existe o está inactivo"}, status=400)

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
        return JsonResponse({"error": f"No se pudo completar la venta: {mensaje}"}, status=400)

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
        "mensaje": "Venta creada correctamente",
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
#stock bajo, ventas del mes, total de productos, total de usuarios
#/dashboard/stats  las 4 tarjetas de arriba:
@require_GET
@requiere_rol("Administrador", "Vendedor")
def dashboard_stats_view(request):
    total_productos = Producto.objects.filter(estatus="activo").count()

    hoy = date.today()
    ventas_mes = Venta.objects.filter(estatus="completada", fecha__year=hoy.year, fecha__month=hoy.month)
    ventas_mes_total = ventas_mes.aggregate(suma=Sum("total"))["suma"] or 0
    ventas_mes_count = ventas_mes.count()

    stock_bajo = Stock.objects.filter(estatus="alerta", stock_actual__gt=0).count()
    agotados = Stock.objects.filter(stock_actual=0).count()

    total_usuarios = Empleado.objects.filter(estatus="activo").count()

    return JsonResponse({
        "ok": True,
        "data": {
            "totalProductos": total_productos,
            "ventasMes": float(ventas_mes_total),
            "totalVentasMes": ventas_mes_count,
            "alertasPendientes": stock_bajo + agotados,
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
@requiere_rol("Administrador", "Vendedor", "Almacenista")
def stock_bajo_view(request):
    stocks = Stock.objects.filter(estatus="alerta").select_related("procve").order_by("stock_actual")

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

#/alertas con ?estado=Pendiente&limit= — lista de alertas:
@require_GET
@requiere_rol("Administrador", "Vendedor", "Almacenista")
def alertas_view(request):
    limit = int(request.GET.get("limit", 10))
    stocks = Stock.objects.filter(estatus="alerta").select_related("procve").order_by("stock_actual")[:limit]

    data = []
    for s in stocks:
        critica = s.stock_actual == 0
        data.append({
            "tipo": "Crítica" if critica else "Advertencia",
            "nombre": "Sin stock" if critica else "Stock bajo",
            "producto_nombre": s.procve.nombre,
            "descripcion": f"Quedan {s.stock_actual} unidades (mínimo {s.stock_minimo})",
        })
    return JsonResponse({"ok": True, "data": data})

# /categorias con conteo — para la dona de "Productos por categoría":
@require_GET
@requiere_rol("Administrador", "Vendedor", "Almacenista")
def categorias_con_conteo_view(request):
    categorias = Categoria.objects.filter(estatus="activo").annotate(
        total_productos=Count("producto", filter=Q(producto__estatus="activo"))
    )
    data = [
        {"catcve": c.catcve, "nombre": c.nombre, "total_productos": c.total_productos}
        for c in categorias
    ]
    return JsonResponse({"ok": True, "data": data})

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