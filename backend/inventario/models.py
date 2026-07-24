from django.db import models
from productos.models import Producto
from usuarios.models import Usuario


class MovimientoInventario(models.Model):
    TIPOS = (('ENTRADA', 'Entrada'), ('SALIDA', 'Salida'), ('AJUSTE', 'Ajuste'))

    id_movimiento = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey(Producto, db_column='id_producto', on_delete=models.DO_NOTHING, related_name='movimientos')
    id_usuario = models.ForeignKey(Usuario, db_column='id_usuario', on_delete=models.DO_NOTHING, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=20, choices=TIPOS)
    cantidad = models.IntegerField()
    stock_anterior = models.IntegerField()
    stock_nuevo = models.IntegerField()
    referencia = models.CharField(max_length=100, null=True, blank=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'movimientos_inventario'
