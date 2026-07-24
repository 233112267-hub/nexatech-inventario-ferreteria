from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import RolePermission
from core.email_service import enviar_alerta_stock
from .models import Alerta
from .serializers import AlertaSerializer


class AlertasListView(APIView):
    permission_classes = [RolePermission('Administrador', 'Vendedor', 'Almacenista')]

    def get(self, request):
        qs = Alerta.objects.select_related('id_producto').order_by('-fecha_creacion')
        tipo = request.query_params.get('tipo')
        if tipo:
            tipo_norm = 'Critica' if tipo in ('Crítica', 'Critica') else tipo
            qs = qs.filter(tipo=tipo_norm)
        estado = request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        total = qs.count()
        limit = request.query_params.get('limit')
        if limit:
            qs = qs[:int(limit)]
        return Response({'ok': True, 'data': AlertaSerializer(qs, many=True).data, 'total': total})


@api_view(['PATCH'])
@permission_classes([RolePermission('Administrador', 'Almacenista')])
def resolver(request, pk):
    try:
        alerta = Alerta.objects.get(pk=pk, estado='Pendiente')
    except Alerta.DoesNotExist:
        return Response({'ok': False, 'message': 'Alerta no encontrada o ya resuelta'}, status=404)
    alerta.estado = 'Resuelta'
    alerta.save()
    return Response({'ok': True, 'message': 'Alerta marcada como resuelta'})


@api_view(['POST'])
@permission_classes([RolePermission('Administrador', 'Vendedor', 'Almacenista')])
def notificar(request, pk):
    try:
        alerta = Alerta.objects.select_related('id_producto').get(pk=pk)
    except Alerta.DoesNotExist:
        return Response({'ok': False, 'message': 'Alerta no encontrada'}, status=404)

    resultado = enviar_alerta_stock({
        'tipo': alerta.tipo, 'nombre': alerta.nombre, 'descripcion': alerta.descripcion,
        'producto_nombre': alerta.id_producto.nombre if alerta.id_producto else None,
        'producto_codigo': alerta.id_producto.codigo if alerta.id_producto else None,
    })
    if not resultado['ok']:
        return Response({'ok': False, 'message': resultado.get('message')}, status=502)
    return Response({'ok': True, 'message': 'Notificación enviada', 'destinatarios': resultado['destinatarios']})
