from django.db import models
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import RolePermission
from .models import Producto, Categoria
from .serializers import ProductoSerializer, CategoriaSerializer


class ProductosListCreateView(APIView):
    permission_classes = [RolePermission('Administrador', 'Vendedor', 'Almacenista')]

    def get(self, request):
        qs = Producto.objects.select_related('id_categoria').all()
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(codigo__icontains=search))
        estado = request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        total = qs.count()
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 10))
        qs = qs[(page - 1) * limit: (page - 1) * limit + limit]
        return Response({'ok': True, 'data': ProductoSerializer(qs, many=True).data, 'total': total})

    def post(self, request):
        permission_classes = [RolePermission('Administrador', 'Almacenista')]
        serializer_in = request.data
        categoria = Categoria.objects.filter(id_categoria=serializer_in.get('id_categoria')).first()
        if not categoria:
            return Response({'ok': False, 'message': 'Categoría inválida'}, status=400)
        producto = Producto.objects.create(
            id_categoria=categoria,
            codigo=serializer_in['codigo'],
            nombre=serializer_in['nombre'],
            descripcion=serializer_in.get('descripcion', ''),
            precio_compra=serializer_in.get('precio_compra', 0),
            precio_venta=serializer_in.get('precio_venta', 0),
            stock_actual=serializer_in.get('stock_actual', 0),
            stock_minimo=serializer_in.get('stock_minimo', 0),
        )
        return Response({'ok': True, 'data': ProductoSerializer(producto).data}, status=201)


class ProductoDetailView(APIView):
    permission_classes = [RolePermission('Administrador', 'Almacenista')]

    def get_object(self, pk):
        try:
            return Producto.objects.select_related('id_categoria').get(pk=pk)
        except Producto.DoesNotExist:
            return None

    def get(self, request, pk):
        p = self.get_object(pk)
        if not p:
            return Response({'ok': False, 'message': 'No encontrado'}, status=404)
        return Response({'ok': True, 'data': ProductoSerializer(p).data})

    def put(self, request, pk):
        return self.patch(request, pk)

    def patch(self, request, pk):
        p = self.get_object(pk)
        if not p:
            return Response({'ok': False, 'message': 'No encontrado'}, status=404)
        data = request.data
        for field in ['codigo', 'nombre', 'descripcion', 'precio_compra', 'precio_venta',
                      'stock_actual', 'stock_minimo', 'estado']:
            if field in data:
                setattr(p, field, data[field])
        if 'id_categoria' in data:
            cat = Categoria.objects.filter(id_categoria=data['id_categoria']).first()
            if cat:
                p.id_categoria = cat
        p.save()
        return Response({'ok': True, 'data': ProductoSerializer(p).data})

    def delete(self, request, pk):
        p = self.get_object(pk)
        if not p:
            return Response({'ok': False, 'message': 'No encontrado'}, status=404)
        p.estado = 'Inactivo'
        p.save()
        return Response({'ok': True, 'message': 'Producto desactivado'})


@api_view(['GET', 'POST'])
@permission_classes([RolePermission('Administrador', 'Vendedor', 'Almacenista')])
def categorias(request):
    if request.method == 'POST':
        nombre = request.data.get('nombre', '').strip()
        if not nombre:
            return Response({'ok': False, 'message': 'El nombre es requerido'}, status=400)
        if Categoria.objects.filter(nombre__iexact=nombre).exists():
            return Response({'ok': False, 'message': 'Esa categoría ya existe'}, status=400)
        categoria = Categoria.objects.create(nombre=nombre)
        return Response({'ok': True, 'data': CategoriaSerializer(categoria).data}, status=201)

    qs = Categoria.objects.annotate(total_productos=Count('productos')).order_by('nombre')
    return Response({'ok': True, 'data': CategoriaSerializer(qs, many=True).data})


@api_view(['GET'])
@permission_classes([RolePermission('Administrador', 'Vendedor', 'Almacenista')])
def stock_bajo(request):
    qs = Producto.objects.select_related('id_categoria').filter(
        estado='Activo', stock_actual__lte=models.F('stock_minimo')
    ).order_by('stock_actual')
    limit = request.query_params.get('limit')
    if limit:
        qs = qs[:int(limit)]
    return Response({'ok': True, 'data': ProductoSerializer(qs, many=True).data})
