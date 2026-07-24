import bcrypt
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import generar_token
from core.permissions import RolePermission
from .models import Usuario, Rol
from .serializers import UsuarioSerializer, VendedorLiteSerializer


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'ok': False, 'message': 'username y password son requeridos'}, status=400)

    try:
        usuario = Usuario.objects.select_related('id_rol').get(username=username, activo=True)
    except Usuario.DoesNotExist:
        return Response({'ok': False, 'message': 'Credenciales inválidas'}, status=401)

    if not bcrypt.checkpw(password.encode(), usuario.password_hash.encode()):
        return Response({'ok': False, 'message': 'Credenciales inválidas'}, status=401)

    token = generar_token(usuario)
    return Response({
        'ok': True,
        'token': token,
        'user': {
            'id': usuario.id_usuario,
            'nombre': usuario.nombre,
            'username': usuario.username,
            'email': usuario.email,
            'rol': usuario.rol_nombre,
        }
    })


class UsuariosListCreateView(APIView):
    permission_classes = [RolePermission('Administrador')]

    def get(self, request):
        qs = Usuario.objects.select_related('id_rol').all()
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(username__icontains=search) | Q(email__icontains=search))
        estado = request.query_params.get('estado')
        if estado == 'Activo':
            qs = qs.filter(activo=True)
        elif estado == 'Inactivo':
            qs = qs.filter(activo=False)
        total = qs.count()
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 10))
        qs = qs[(page - 1) * limit: (page - 1) * limit + limit]
        return Response({'ok': True, 'data': UsuarioSerializer(qs, many=True).data, 'total': total})

    def post(self, request):
        data = request.data
        rol = Rol.objects.filter(nombre=data.get('rol')).first() or Rol.objects.filter(id_rol=data.get('id_rol')).first()
        if not rol:
            return Response({'ok': False, 'message': 'Rol inválido'}, status=400)
        hashed = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()
        usuario = Usuario.objects.create(
            nombre=data['nombre'], username=data['username'], email=data['email'],
            password_hash=hashed, id_rol=rol, activo=data.get('activo', True),
        )
        return Response({'ok': True, 'data': UsuarioSerializer(usuario).data}, status=201)


class UsuarioDetailView(APIView):
    permission_classes = [RolePermission('Administrador')]

    def get_object(self, pk):
        try:
            return Usuario.objects.select_related('id_rol').get(pk=pk)
        except Usuario.DoesNotExist:
            return None

    def get(self, request, pk):
        usuario = self.get_object(pk)
        if not usuario:
            return Response({'ok': False, 'message': 'No encontrado'}, status=404)
        return Response({'ok': True, 'data': UsuarioSerializer(usuario).data})

    def put(self, request, pk):
        return self.patch(request, pk)

    def patch(self, request, pk):
        usuario = self.get_object(pk)
        if not usuario:
            return Response({'ok': False, 'message': 'No encontrado'}, status=404)
        data = request.data
        usuario.nombre = data.get('nombre', usuario.nombre)
        usuario.username = data.get('username', usuario.username)
        usuario.email = data.get('email', usuario.email)
        usuario.activo = data.get('activo', usuario.activo)
        if data.get('password'):
            usuario.password_hash = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()
        if data.get('rol'):
            rol = Rol.objects.filter(nombre=data['rol']).first()
            if rol:
                usuario.id_rol = rol
        usuario.save()
        return Response({'ok': True, 'data': UsuarioSerializer(usuario).data})

    def delete(self, request, pk):
        usuario = self.get_object(pk)
        if not usuario:
            return Response({'ok': False, 'message': 'No encontrado'}, status=404)
        usuario.delete()
        return Response({'ok': True, 'message': 'Usuario eliminado'})


@api_view(['GET'])
@permission_classes([RolePermission('Administrador', 'Vendedor')])
def vendedores(request):
    qs = Usuario.objects.select_related('id_rol').filter(
        activo=True, id_rol__nombre__in=['Vendedor', 'Administrador']
    ).order_by('id_rol__nombre', 'nombre')
    return Response({'ok': True, 'data': VendedorLiteSerializer(qs, many=True).data})
