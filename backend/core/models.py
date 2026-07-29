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

class Categoria(models.Model):
    catcve = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=80)
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    estatus = models.CharField(max_length=20, default='activo')
    fecha = models.DateField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'categoria'


class Producto(models.Model):
    procve = models.AutoField(primary_key=True)
    catcve = models.ForeignKey(Categoria, on_delete=models.DO_NOTHING, db_column='catcve')
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    estatus = models.CharField(max_length=20, default='activo')
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)
    modelo = models.CharField(max_length=50, blank=True, null=True)
    marca = models.CharField(max_length=50, blank=True, null=True)
    informacion_adicional = models.CharField(max_length=255, blank=True, null=True)
    nombre = models.CharField(max_length=100)
    color = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'producto'

class Venta(models.Model):
    vencve = models.AutoField(primary_key=True)
    empcve = models.ForeignKey(Empleado, on_delete=models.DO_NOTHING, db_column='empcve')
    clicve = models.ForeignKey(Cliente, on_delete=models.DO_NOTHING, db_column='clicve', blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descripcion = models.CharField(max_length=150, blank=True, null=True)
    estatus = models.CharField(max_length=20, default='completada')
    metodo_pago = models.CharField(max_length=20, default='efectivo')
    tipo_entrega = models.CharField(max_length=20, default='mostrador')
    direccion_entrega = models.CharField(max_length=200, blank=True, null=True)
    codigo_postal = models.CharField(max_length=10, blank=True, null=True)
    fecha = models.DateField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'venta'


class DetalleVenta(models.Model):
    detcve = models.AutoField(primary_key=True)
    procve = models.ForeignKey(Producto, on_delete=models.DO_NOTHING, db_column='procve')
    vencve = models.ForeignKey(Venta, on_delete=models.DO_NOTHING, db_column='vencve')
    fecha = models.DateField(auto_now_add=True)
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    estatus = models.CharField(max_length=20, default='activo')
    modalidad = models.CharField(max_length=20, default='normal')

    class Meta:
        managed = False
        db_table = 'detalle_venta'
