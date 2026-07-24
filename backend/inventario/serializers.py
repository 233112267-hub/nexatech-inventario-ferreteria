from rest_framework import serializers
from .models import MovimientoInventario


class MovimientoSerializer(serializers.ModelSerializer):
    producto = serializers.CharField(source='id_producto.nombre', read_only=True)
    usuario = serializers.CharField(source='id_usuario.nombre', read_only=True)

    class Meta:
        model = MovimientoInventario
        fields = ['id_movimiento', 'id_producto', 'producto', 'id_usuario', 'usuario',
                  'tipo_movimiento', 'cantidad', 'stock_anterior', 'stock_nuevo',
                  'referencia', 'fecha_movimiento']
