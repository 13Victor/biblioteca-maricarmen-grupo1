"""
URL configuration for biblio_maricarmen project.
"""
from django.contrib import admin
from django.urls import path
from biblioteca import views
from ninja import NinjaAPI
from biblioteca.api import api

urlpatterns = [
    path('', views.index),
    path('cataleg/', views.index),
    path('csv-importacio/', views.index),
    path('etiquetes/', views.index),
    path('historial-prestecs/', views.index),
    path('admin/', admin.site.urls),
    path("api/", api.urls),
    path("import_users/", views.import_users),
    path('test-403/', views.test_403),
]

# Manejadores de errores
handler404 = 'biblioteca.views.error_404'
handler403 = 'biblioteca.views.error_403'
