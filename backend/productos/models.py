from django.db import models


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        managed = False
        db_table = 'categorias'

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    ESTADOS = (('Activo', 'Activo'), ('Inactivo', 'Inactivo'))

    id_producto = models.AutoField(primary_key=True)
    id_categoria = models.ForeignKey(Categoria, db_column='id_categoria', on_delete=models.DO_NOTHING, related_name='productos')
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.CharField(max_length=500, null=True, blank=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'productos'

    def __str__(self):
        return self.nombre
