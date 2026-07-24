from django.urls import path
from . import views

urlpatterns = [
    path('productos/stock-bajo', views.stock_bajo),
    path('productos', views.ProductosListCreateView.as_view()),
    path('productos/<int:pk>', views.ProductoDetailView.as_view()),
    path('categorias', views.categorias),
]
