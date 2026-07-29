# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
     # post login productos y empleados 
    path('api/auth/login/', views.login_view),
    path('api/productos/', views.crear_producto_view),
    path('api/empleados/', views.crear_empleado_view),

    # get productos y empleados
    path('api/productos/listar/', views.listar_productos_view),
    path('api/empleados/listar/', views.listar_empleados_view),

    # put y delete productos y empleados
    path('api/productos/<int:procve>/', views.actualizar_producto_view),
    path('api/empleados/<int:empcve>/', views.actualizar_empleado_view),
]