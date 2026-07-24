from django.urls import path
from . import views

urlpatterns = [
    path('movimientos', views.MovimientosListCreateView.as_view()),
]
