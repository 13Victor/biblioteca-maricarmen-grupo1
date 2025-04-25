from biblioteca.views import error_403

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificar si la solicitud es para el panel de administración
        # Permitimos el acceso a la página de login de admin
        if request.path.startswith('/admin/') and not request.path.startswith('/admin/login/'):
            # Verificar si el usuario está autenticado
            if not request.user.is_authenticated:
                # Si no está autenticado, devolver error 403
                return error_403(request, exception=None)
            
            # Verificar si es bibliotecario o administrador
            if not (request.user.is_staff or request.user.is_superuser):
                # Si no es ni bibliotecario ni administrador, devolver error 403
                return error_403(request, exception=None)
        
        # Si pasó todas las verificaciones, continuar con la solicitud
        response = self.get_response(request)
        return response
