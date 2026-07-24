from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import RolePermission
from core.email_service import enviar_alerta_stock
from productos.models import Producto
from alertas.models import Alerta
from .models import MovimientoInventario
from .serializers import MovimientoSerializer


class MovimientosListCreateView(APIView):
    permission_classes = [RolePermission('Administrador', 'Almacenista')]

    def get(self, request):
        qs = MovimientoInventario.objects.select_related('id_producto', 'id_usuario').order_by('-fecha_movimiento')
        total = qs.count()
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 10))
        qs = qs[(page - 1) * limit: (page - 1) * limit + limit]
        return Response({'ok': True, 'data': MovimientoSerializer(qs, many=True).data, 'total': total})

    @transaction.atomic
    def post(self, request):
        data = request.data
        try:
            producto = Producto.objects.select_for_update().get(pk=data['producto_id'])
        except Producto.DoesNotExist:
            return Response({'ok': False, 'message': 'Producto no encontrado'}, status=404)

        tipo = data['tipo_movimiento']  # ENTRADA / SALIDA / AJUSTE
        cantidad = int(data['cantidad'])
        stock_anterior = producto.stock_actual

        if tipo == 'ENTRADA':
            nuevo_stock = stock_anterior + cantidad
        elif tipo == 'SALIDA':
            if stock_anterior < cantidad:
                return Response({'ok': False, 'message': 'Stock insuficiente para la salida'}, status=400)
            nuevo_stock = stock_anterior - cantidad
        else:  # AJUSTE: cantidad es el nuevo stock absoluto
            nuevo_stock = cantidad

        producto.stock_actual = nuevo_stock
        producto.save()

        movimiento = MovimientoInventario.objects.create(
            id_producto=producto, id_usuario=request.user, tipo_movimiento=tipo,
            cantidad=cantidad, stock_anterior=stock_anterior, stock_nuevo=nuevo_stock,
            referencia=data.get('referencia', ''),
        )

        if nuevo_stock <= producto.stock_minimo:
            tipo_alerta = 'Critica' if nuevo_stock == 0 else 'Advertencia'
            nombre_alerta = 'Sin stock' if nuevo_stock == 0 else 'Stock bajo'
            descripcion = (f'Sin unidades disponibles (mínimo: {producto.stock_minimo}).' if nuevo_stock == 0
                           else f'Quedan {nuevo_stock} unidades (mínimo: {producto.stock_minimo}).')
            Alerta.objects.create(tipo=tipo_alerta, nombre=nombre_alerta, descripcion=descripcion, id_producto=producto)
            if tipo_alerta == 'Critica':
                try:
                    enviar_alerta_stock({
                        'tipo': tipo_alerta, 'nombre': nombre_alerta, 'descripcion': descripcion,
                        'producto_nombre': producto.nombre, 'producto_codigo': producto.codigo,
                    })
                except Exception:
                    pass

        return Response({'ok': True, 'data': MovimientoSerializer(movimiento).data}, status=201)
