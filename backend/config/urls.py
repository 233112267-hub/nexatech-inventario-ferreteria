"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.http import JsonResponse


def health(request):
    return JsonResponse({
        'ok': True,
        'message': 'Ferretería API (Django) corriendo 🔧',
        'version': '1.0.0',
    })


urlpatterns = [
    path('', health),
    path('api/', include('usuarios.urls')),
    path('api/', include('productos.urls')),
    path('api/', include('ventas.urls')),
    path('api/', include('inventario.urls')),
    path('api/', include('alertas.urls')),
    path('api/', include('core.urls')),
]
