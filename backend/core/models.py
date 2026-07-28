# core/models.py
from django.db import models

class Surcusal(models.Model):
    surcve = models.AutoField(primary_key=True)
    estado = models.CharField(max_length=50)
    municipio = models.CharField(max_length=50)
    localidad = models.CharField(max_length=50)
    referencia = models.CharField(max_length=150, blank=True, null=True)
    direccion = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'surcusal'


class Empleado(models.Model):
    empcve = models.AutoField(primary_key=True)
    surcve = models.ForeignKey(Surcusal, on_delete=models.DO_NOTHING, db_column='surcve')
    nombre = models.CharField(max_length=60)
    apellidopaterno = models.CharField(max_length=60)
    apellidomaterno = models.CharField(max_length=60, blank=True, null=True)
    rol = models.CharField(max_length=20)
    estatus = models.CharField(max_length=20, default='activo')
    username = models.CharField(max_length=50, unique=True)
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    reset_token = models.CharField(max_length=64, blank=True, null=True)
    reset_token_expira = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'empleado'


class Cliente(models.Model):
    clicve = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=60)
    apellidopaterno = models.CharField(max_length=60)
    apellidomaterno = models.CharField(max_length=60, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    username = models.CharField(max_length=50, unique=True)
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    membresia = models.CharField(max_length=20, default='basica')
    estatus = models.CharField(max_length=20, default='activo')
    reset_token = models.CharField(max_length=64, blank=True, null=True)
    reset_token_expira = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cliente'

