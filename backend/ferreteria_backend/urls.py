"""
URL configuration for ferreteria_backend project.
"""

# ferreteria_backend/urls.py
from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
]