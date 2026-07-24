from django.urls import path
from . import views

urlpatterns = [
    path('ventas', views.VentasListCreateView.as_view()),
]
