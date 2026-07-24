import random
import string
from decimal import Decimal
from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import RolePermission
from core.email_service import enviar_alerta_stock
from productos.models import Producto
from usuarios.models import Usuario
from alertas.models import Alerta
from .models import Venta, DetalleVenta
from .serializers import VentaSerializer


def generar_folio():
    return 'VTA-' + ''.join(random.choices(string.digits, k=6))


class VentasListCreateView(APIView):
    permission_classes = [RolePermission('Administrador', 'Vendedor')]

    def get(self, request):
        qs = Venta.objects.select_related('id_usuario').prefetch_related('detalles').order_by('-fecha_venta')
        total = qs.count()
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 10))
        qs = qs[(page - 1) * limit: (page - 1) * limit + limit]
        return Response({'ok': True, 'data': VentaSerializer(qs, many=True).data, 'total': total})

    @transaction.atomic
    def post(self, request):
        data = request.data
        items = data.get('items', [])
        if not items:
            return Response({'ok': False, 'message': 'La venta debe tener al menos un producto'}, status=400)

        vendedor_id = data.get('vendedor_id') or request.user.id_usuario
        try:
            vendedor = Usuario.objects.get(pk=vendedor_id)
        except Usuario.DoesNotExist:
            return Response({'ok': False, 'message': 'Vendedor inválido'}, status=400)

        # 1) Validar stock y bloquear filas
        productos_data = {}
        for item in items:
            try:
                prod = Producto.objects.select_for_update().get(pk=item['producto_id'], estado='Activo')
            except Producto.DoesNotExist:
                return Response({'ok': False, 'message': f"Producto ID {item['producto_id']} no encontrado"}, status=400)
            if prod.stock_actual < item['cantidad']:
                return Response({'ok': False, 'message': f'Stock insuficiente para "{prod.nombre}"'}, status=400)
            productos_data[item['producto_id']] = prod

        subtotal = sum(Decimal(str(productos_data[i['producto_id']].precio_venta)) * i['cantidad'] for i in items)
        impuestos = (subtotal * Decimal('0.16')).quantize(Decimal('0.01'))
        total = subtotal + impuestos

        venta = Venta.objects.create(
            id_usuario=vendedor,
            folio=generar_folio(),
            cliente=data.get('cliente') or None,
            subtotal=subtotal, impuestos=impuestos, total=total,
            metodo_pago=data.get('metodo_pago', 'Efectivo'),
            estado='Pagada',
        )

        alertas_para_correo = []
        for item in items:
            prod = productos_data[item['producto_id']]
            precio = prod.precio_venta
            DetalleVenta.objects.create(
                id_venta=venta, id_producto=prod, cantidad=item['cantidad'],
                precio_unitario=precio, subtotal=precio * item['cantidad'],
            )
            nuevo_stock = prod.stock_actual - item['cantidad']
            prod.stock_actual = nuevo_stock
            prod.save()

            if nuevo_stock <= prod.stock_minimo:
                tipo = 'Critica' if nuevo_stock == 0 else 'Advertencia'
                nombre_alerta = 'Sin stock' if nuevo_stock == 0 else 'Stock bajo'
                descripcion = (f'Sin unidades disponibles (mínimo: {prod.stock_minimo}).' if nuevo_stock == 0
                               else f'Quedan {nuevo_stock} unidades (mínimo: {prod.stock_minimo}).')
                Alerta.objects.create(tipo=tipo, nombre=nombre_alerta, descripcion=descripcion, id_producto=prod)
                if tipo == 'Critica':
                    alertas_para_correo.append({
                        'tipo': tipo, 'nombre': nombre_alerta, 'descripcion': descripcion,
                        'producto_nombre': prod.nombre, 'producto_codigo': prod.codigo,
                    })

        # El correo se envía fuera de la transacción crítica de stock, pero aún
        # dentro de la vista (equivalente al .catch() de emailService en Node)
        for a in alertas_para_correo:
            try:
                enviar_alerta_stock(a)
            except Exception:
                pass

        return Response({'ok': True, 'data': VentaSerializer(venta).data}, status=201)
