from rest_framework import serializers
from .models import Venta, DetalleVenta


class DetalleVentaSerializer(serializers.ModelSerializer):
    producto = serializers.CharField(source='id_producto.nombre', read_only=True)

    class Meta:
        model = DetalleVenta
        fields = ['id_detalle', 'id_producto', 'producto', 'cantidad', 'precio_unitario', 'subtotal']


class VentaSerializer(serializers.ModelSerializer):
    vendedor = serializers.CharField(source='id_usuario.nombre', read_only=True)
    detalles = DetalleVentaSerializer(many=True, read_only=True)

    class Meta:
        model = Venta
        fields = ['id_venta', 'folio', 'cliente', 'subtotal', 'descuento', 'impuestos',
                  'total', 'metodo_pago', 'estado', 'fecha_venta', 'id_usuario', 'vendedor', 'detalles']
