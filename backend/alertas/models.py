from django.db import models
from productos.models import Producto


class Alerta(models.Model):
    TIPOS = (('Critica', 'Critica'), ('Advertencia', 'Advertencia'))
    ESTADOS = (('Pendiente', 'Pendiente'), ('Resuelta', 'Resuelta'))

    id_alerta = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=500, null=True, blank=True)
    id_producto = models.ForeignKey(Producto, db_column='id_producto', on_delete=models.CASCADE, related_name='alertas', null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'alertas'
