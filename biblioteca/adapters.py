from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from django.http import HttpResponseRedirect
import json

class CustomAccountAdapter(DefaultAccountAdapter):
    def respond_user_inactive(self, request, user):
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/login?error=inactive_user")
    
    def respond_email_verification_sent(self, request, user):
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/login?info=verification_sent")

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Interviene antes de que se complete el login social.
        """
        # Si el usuario ya existe, asegurarse de que la cuenta social se conecte
        if sociallogin.is_existing:
            return
            
        # Intentar conectar con un usuario existente por email
        if sociallogin.email_addresses:
            email = sociallogin.email_addresses[0].email
            User = self.get_user_model()
            
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass
    
    def save_user(self, request, sociallogin, form=None):
        """
        Personaliza la creación del usuario a partir de datos sociales
        """
        user = super().save_user(request, sociallogin, form)
        
        # Extrae información adicional específica por proveedor
        if sociallogin.account.provider == 'google':
            data = sociallogin.account.extra_data
            if 'given_name' in data:
                user.first_name = data['given_name']
            if 'family_name' in data:
                user.last_name = data['family_name']
        
        elif sociallogin.account.provider == 'microsoft':
            data = sociallogin.account.extra_data
            if 'givenName' in data:
                user.first_name = data['givenName']
            if 'surname' in data:
                user.last_name = data['surname']
        
        user.save()
        return user
    
    def get_connect_redirect_url(self, request, socialaccount):
        """
        Después de conectar una cuenta social, redirige al frontend
        """
        return f"{settings.FRONTEND_URL}/perfil"
