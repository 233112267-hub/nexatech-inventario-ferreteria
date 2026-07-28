# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/auth/login/', views.login_view),
    path('api/productos/', views.crear_producto_view),
]
