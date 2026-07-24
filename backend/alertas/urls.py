from django.urls import path
from . import views

urlpatterns = [
    path('alertas', views.AlertasListView.as_view()),
    path('alertas/<int:pk>/resolver', views.resolver),
    path('alertas/<int:pk>/notificar', views.notificar),
]
