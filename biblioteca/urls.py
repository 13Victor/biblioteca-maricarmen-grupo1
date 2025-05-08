from django.urls import path, include
from . import views

urlpatterns = [
    # ...existing routes...
    
    # Rutas para autenticación social
    path('api/auth/', include([
        path('login/<str:provider>/', views.social_auth_login, name='social_login'),
        path('callback/<str:provider>/', views.social_auth_callback, name='social_callback'),
        path('login-success/', views.login_success, name='login_success'),
        path('logout-success/', views.logout_success, name='logout_success'),
    ])),
    
    # La URL para verificar la sesión actual y obtener información del usuario
    path('api/auth/session/', views.get_session_info, name='session_info'),
]
