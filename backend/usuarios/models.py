from django.db import models


class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'roles'

    def __str__(self):
        return self.nombre


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Rol, db_column='id_rol', on_delete=models.DO_NOTHING, related_name='usuarios')
    nombre = models.CharField(max_length=100)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'usuarios'

    def __str__(self):
        return self.username

    @property
    def is_authenticated(self):
        return True

    @property
    def rol_nombre(self):
        return self.id_rol.nombre
