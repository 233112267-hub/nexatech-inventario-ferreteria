import re
from rest_framework import serializers
from .models import Usuario

NOMBRE_REGEX = re.compile(r'^[A-Za-zÀ-ÖØ-öø-ÿ\s]+$')


class UsuarioSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_usuario', read_only=True)
    usuario = serializers.CharField(source='username')
    correo = serializers.EmailField(source='email')
    rol = serializers.CharField(source='id_rol.nombre', read_only=True)
    estado = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'usuario', 'correo', 'rol', 'activo', 'estado',
                  'created_at', 'updated_at']

    def get_estado(self, obj):
        return 'Activo' if obj.activo else 'Inactivo'

    def validate_nombre(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError('El nombre debe tener al menos 3 caracteres.')
        if not NOMBRE_REGEX.match(value):
            raise serializers.ValidationError(
                'El nombre solo puede contener letras y espacios (sin números ni símbolos).'
            )
        return value


class VendedorLiteSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source='id_rol.nombre', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre', 'rol']