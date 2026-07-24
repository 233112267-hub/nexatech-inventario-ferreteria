from django.urls import path
from . import views

urlpatterns = [
    path('auth/login', views.login),
    path('usuarios', views.UsuariosListCreateView.as_view()),
    path('usuarios/vendedores', views.vendedores),
    path('usuarios/<int:pk>', views.UsuarioDetailView.as_view()),
]
