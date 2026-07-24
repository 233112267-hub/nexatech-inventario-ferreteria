from rest_framework import serializers
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source='id_rol.nombre', read_only=True)
    estado = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre', 'username', 'email', 'id_rol', 'rol',
                  'activo', 'estado', 'created_at', 'updated_at']
        extra_kwargs = {'id_rol': {'write_only': True}}

    def get_estado(self, obj):
        return 'Activo' if obj.activo else 'Inactivo'


class VendedorLiteSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source='id_rol.nombre', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre', 'rol']
