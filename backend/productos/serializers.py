from rest_framework import serializers
from .models import Producto, Categoria


class ProductoSerializer(serializers.ModelSerializer):
    categoria = serializers.CharField(source='id_categoria.nombre', read_only=True)

    class Meta:
        model = Producto
        fields = ['id_producto', 'codigo', 'nombre', 'descripcion', 'precio_compra',
                  'precio_venta', 'stock_actual', 'stock_minimo', 'estado',
                  'id_categoria', 'categoria', 'created_at', 'updated_at']
        extra_kwargs = {'id_categoria': {'write_only': True}}


class CategoriaSerializer(serializers.ModelSerializer):
    total_productos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre', 'total_productos']
