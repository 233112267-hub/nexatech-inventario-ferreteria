from rest_framework.permissions import BasePermission


def RolePermission(*roles_permitidos):
    """
    Uso: permission_classes = [RolePermission('Administrador', 'Vendedor')]
    Equivalente a roleMiddleware('Administrador','Vendedor') en Express.
    """
    class _RolePermission(BasePermission):
        def has_permission(self, request, view):
            usuario = request.user
            if not usuario or not getattr(usuario, 'is_authenticated', False):
                return False
            return usuario.rol_nombre in roles_permitidos
    return _RolePermission
