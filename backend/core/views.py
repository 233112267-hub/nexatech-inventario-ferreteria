from django.db import connection
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.permissions import RolePermission
from productos.models import Producto
from ventas.models import Venta
from usuarios.models import Usuario
from alertas.models import Alerta


TODOS_LOS_ROLES = RolePermission('Administrador', 'Vendedor', 'Almacenista')


@api_view(['GET'])
@permission_classes([TODOS_LOS_ROLES])
def stats(request):
    hoy = timezone.now()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_productos = Producto.objects.filter(estado='Activo').count()
    ventas_mes_qs = Venta.objects.filter(fecha_venta__gte=inicio_mes, estado='Pagada')
    ventas_mes_total = ventas_mes_qs.aggregate(s=Sum('total'))['s'] or 0
    ventas_mes_count = ventas_mes_qs.count()
    alertas_pendientes = Alerta.objects.filter(estado='Pendiente').count()
    bajo_stock = Alerta.objects.filter(estado='Pendiente', tipo='Advertencia').count()
    agotados = Alerta.objects.filter(estado='Pendiente', tipo='Critica').count()
    usuarios_activos = Usuario.objects.filter(activo=True).count()

    return Response({'ok': True, 'data': {
        'totalProductos': total_productos,
        'ventasMes': float(ventas_mes_total),
        'ventasMesCount': ventas_mes_count,
        'alertasPendientes': alertas_pendientes,
        'bajoStock': bajo_stock,
        'agotados': agotados,
        'usuariosActivos': usuarios_activos,
    }})


@api_view(['GET'])
@permission_classes([TODOS_LOS_ROLES])
def ventas_semana(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT to_char(d::date, 'DY') AS dia, to_char(d::date, 'YYYY-MM-DD') AS fecha,
                   COALESCE(SUM(v.total), 0)::float AS total
            FROM generate_series(CURRENT_DATE - INTERVAL '6 days', CURRENT_DATE, INTERVAL '1 day') d
            LEFT JOIN ventas v ON v.fecha_venta::date = d::date AND v.estado = 'Pagada'
            GROUP BY d, dia
            ORDER BY d
        """)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return Response({'ok': True, 'data': rows})


@api_view(['GET'])
@permission_classes([TODOS_LOS_ROLES])
def ventas_por_categoria(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.nombre AS categoria, COALESCE(SUM(dv.cantidad), 0)::int AS unidades_vendidas
            FROM categorias c
            JOIN productos p ON p.id_categoria = c.id_categoria
            JOIN detalle_ventas dv ON dv.id_producto = p.id_producto
            JOIN ventas v ON v.id_venta = dv.id_venta AND v.estado = 'Pagada'
            GROUP BY c.nombre
            HAVING COALESCE(SUM(dv.cantidad), 0) > 0
            ORDER BY unidades_vendidas DESC
        """)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return Response({'ok': True, 'data': rows})
