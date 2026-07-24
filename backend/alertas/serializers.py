from rest_framework import serializers
from .models import Alerta


class AlertaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='id_producto.nombre', read_only=True, default=None)
    producto_codigo = serializers.CharField(source='id_producto.codigo', read_only=True, default=None)

    class Meta:
        model = Alerta
        fields = ['id_alerta', 'tipo', 'nombre', 'descripcion', 'id_producto',
                  'producto_nombre', 'producto_codigo', 'estado', 'fecha_creacion']
