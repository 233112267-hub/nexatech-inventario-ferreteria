from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/stats', views.stats),
    path('dashboard/ventas-semana', views.ventas_semana),
    path('dashboard/ventas-por-categoria', views.ventas_por_categoria),
]
