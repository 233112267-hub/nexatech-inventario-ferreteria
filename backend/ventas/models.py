from django.db import models
from usuarios.models import Usuario
from productos.models import Producto


class Venta(models.Model):
    METODOS = (('Efectivo', 'Efectivo'), ('Tarjeta', 'Tarjeta'), ('Transferencia', 'Transferencia'))
    ESTADOS = (('Pagada', 'Pagada'), ('Pendiente', 'Pendiente'), ('Cancelada', 'Cancelada'))

    id_venta = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, db_column='id_usuario', on_delete=models.DO_NOTHING, related_name='ventas')
    folio = models.CharField(max_length=50, unique=True)
    cliente = models.CharField(max_length=150, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=20, choices=METODOS, default='Efectivo')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pagada')
    fecha_venta = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ventas'


class DetalleVenta(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    id_venta = models.ForeignKey(Venta, db_column='id_venta', on_delete=models.CASCADE, related_name='detalles')
    id_producto = models.ForeignKey(Producto, db_column='id_producto', on_delete=models.DO_NOTHING, related_name='detalle_ventas')
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'detalle_ventas'
