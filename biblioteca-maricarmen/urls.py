from django.contrib import admin
from django.urls import path, include
from biblioteca import views
from ninja import NinjaAPI
from biblioteca.api import api

urlpatterns = [
    path('', views.index),
    path('login/', views.index),  # Add this line
    path('cataleg/', views.index),
    path('csv-importacio/', views.index),
    path('historial-prestecs/', views.index),
    path('admin/', admin.site.urls),
    path("api/", api.urls),
    path("import_users/", views.import_users),
    
    # URLs for django-allauth
    path('accounts/', include('allauth.urls')),
    
    # Social auth endpoints
    path('api/auth/social/', views.social_auth_token, name='social_auth_token'),
    path('api/auth/social/callback/', views.social_auth_callback, name='social_auth_callback'),
    
    # Rutas para autenticación social
    path('api/auth/login/<str:provider>/', views.social_auth_login, name='social_login'),
    path('api/auth/callback/<str:provider>/', views.social_auth_callback, name='social_callback'),
    path('api/auth/login-success/', views.login_success, name='login_success'),
    path('api/auth/logout-success/', views.logout_success, name='logout_success'),
    path('api/auth/session/', views.get_session_info, name='session_info'),
]