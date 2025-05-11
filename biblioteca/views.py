# Default Django imports
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from django.template.exceptions import TemplateDoesNotExist
# ImportCSV
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
from .models import Usuari, Centre, Cicle
import random
import string

import requests
import secrets
import urllib.parse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth import login
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.microsoft.views import MicrosoftGraphOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.helpers import complete_social_login
from django.shortcuts import redirect
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.helpers import render_authentication_error
from allauth.socialaccount import providers

# Constantes para la autenticación
FRONTEND_URL = 'http://localhost:8000'  # Cambia esto por la URL de tu frontend en producción

@csrf_exempt
def social_auth_token(request):
    """
    Iniciar el flujo de autenticación OAuth2 para Google o Microsoft
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    provider = request.GET.get('provider')
    if provider not in ['google', 'microsoft']:
        return JsonResponse({'error': 'Proveedor no soportado'}, status=400)
    
    # Generar un estado único para prevenir CSRF
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    
    try:
        if provider == 'google':
            social_app = SocialApp.objects.get(provider='google')
            authorize_url = 'https://accounts.google.com/o/oauth2/auth'
            
            # La URL de callback debe coincidir exactamente con la registrada en Google Cloud Console
            callback_url = f"{request.build_absolute_uri('/').rstrip('/')}/api/auth/social/callback/"
            
            params = {
                'client_id': social_app.client_id,
                'redirect_uri': callback_url,
                'response_type': 'code',
                'scope': 'email profile',
                'state': f"{state}|google",
                'prompt': 'select_account',
            }
        else:  # microsoft
            social_app = SocialApp.objects.get(provider='microsoft')
            authorize_url = 'https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize'
            
            # La URL de callback debe coincidir exactamente con la registrada en Azure Portal
            callback_url = f"{request.build_absolute_uri('/').rstrip('/')}/api/auth/social/callback/"
            
            params = {
                'client_id': social_app.client_id,
                'redirect_uri': callback_url,
                'response_type': 'code',
                'scope': 'User.Read email profile openid',
                'state': f"{state}|microsoft",
                'prompt': 'select_account',
            }
        auth_url = f"{authorize_url}?{urllib.parse.urlencode(params)}"
        return JsonResponse({'auth_url': auth_url})
    except ObjectDoesNotExist:
        return JsonResponse({'error': f'Configuración para {provider} no encontrada'}, status=500)

@csrf_exempt
def social_auth_callback(request):
    """ 
    Callback para procesar la respuesta del proveedor de OAuth2
    """
    code = request.GET.get('code')
    state = request.GET.get('state', '')
    
    if not code:
        return redirect(f"{FRONTEND_URL}/login?error=auth_failed")
    
    try:
        # Verificar el estado para prevenir CSRF
        stored_state = request.session.get('oauth_state')
        state_parts = state.split('|')
        
        if len(state_parts) != 2 or state_parts[0] != stored_state:
            return redirect(f"{FRONTEND_URL}/login?error=invalid_state")
        
        provider = state_parts[1]
        
        # Configurar parámetros según el proveedor
        if provider == 'google':
            token_url = 'https://oauth2.googleapis.com/token'
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            social_app = SocialApp.objects.get(provider='google')
        elif provider == 'microsoft':
            token_url = 'https://login.microsoftonline.com/consumers/oauth2/v2.0/token'
            userinfo_url = 'https://graph.microsoft.com/v1.0/me'
            social_app = SocialApp.objects.get(provider='microsoft')
        else:
            return redirect(f"{FRONTEND_URL}/login?error=invalid_provider")
        
        # Obtener token de acceso
        token_data = {
            'code': code,
            'client_id': social_app.client_id,
            'client_secret': social_app.secret,
            'redirect_uri': f"{request.build_absolute_uri('/').rstrip('/')}/api/auth/social/callback/",
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            return redirect(f"{FRONTEND_URL}/login?error=token_error")
        
        access_token = token_json['access_token']
        
        # Obtener info del usuario
        headers = {
            'Authorization': f"Bearer {access_token}"
        }
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo = userinfo_response.json()
        
        # Crear o actualizar usuario
        email = userinfo.get('email')
        if not email and provider == 'microsoft':
            # Microsoft Graph a veces no incluye email en la respuesta básica
            email = userinfo.get('userPrincipalName')
            
        if not email:
            return redirect(f"{FRONTEND_URL}/login?error=no_email")
            
        # Buscar usuario existente o crear uno nuevo
        try:
            usuario = Usuari.objects.get(email=email)
        except Usuari.DoesNotExist:
            # Crear un nuevo usuario
            username = email.split('@')[0]
            firstname = userinfo.get('given_name', '')
            lastname = userinfo.get('family_name', '')
            
            # Crear usuario con datos del social login
            usuario = Usuari(
                username=username,
                email=email,
                first_name=firstname,
                last_name=lastname,
                is_active=True
            )
            usuario.save()
            # Guardar la cuenta social
            social_account = SocialAccount(
                user=usuario,
                provider=provider,
                uid=userinfo.get('sub') if provider == 'google' else userinfo.get('id'),
                extra_data=userinfo
            )
            social_account.save()
            
        # Iniciar sesión
        login(request, usuario)
        
        # Generar token JWT para la API
        from django.utils.crypto import get_random_string
        auth_token = get_random_string(32)
        usuario.auth_token = auth_token
        usuario.save()
        
        # Redirigir al frontend con el token
        return redirect(f"{FRONTEND_URL}/auth/callback?token={auth_token}")
        
    except Exception as e:
        print(f"Error en social_auth_callback: {str(e)}")
        return redirect(f"{FRONTEND_URL}/login?error=server_error")

def social_auth_login(request, provider):
    """ 
    Inicia el flujo de autenticación OAuth2 para Google o Microsoft
    """
    if provider not in ['google', 'microsoft']:
        return JsonResponse({'error': 'Proveedor no soportado'}, status=400)
    
    # Obtener el estado para CSRF protection y la URL de redirección frontend
    redirect_uri = request.GET.get('redirect_uri', f"{settings.FRONTEND_URL}/")
    next_url = request.GET.get('next', '/')
    
    # Construir URL de callback completa
    callback_url = request.build_absolute_uri(reverse('social_callback', kwargs={'provider': provider}))
    
    try:
        # Configuración específica según el proveedor
        if provider == 'google':
            social_app = SocialApp.objects.get(provider='google')
            authorize_url = 'https://accounts.google.com/o/oauth2/auth'
            
            params = {
                'client_id': social_app.client_id,
                'redirect_uri': callback_url,
                'response_type': 'code',
                'scope': 'email profile',
                'state': urllib.parse.quote(f"{redirect_uri}|{next_url}"),
            }
        else:  # microsoft
            social_app = SocialApp.objects.get(provider='microsoft')
            authorize_url = 'https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize'
            
            params = {
                'client_id': social_app.client_id,
                'redirect_uri': callback_url,
                'response_type': 'code',
                'scope': 'User.Read email profile openid',
                'state': urllib.parse.quote(f"{redirect_uri}|{next_url}"),
            }
        # Construir y redirigir a la URL de autorización
        auth_url = f"{authorize_url}?{urllib.parse.urlencode(params)}"
        return HttpResponseRedirect(auth_url)
    except SocialApp.DoesNotExist:
        return JsonResponse({'error': f'Configuración para {provider} no encontrada'}, status=500)

def social_auth_callback(request, provider=None):
    """ 
    Procesa la respuesta del proveedor OAuth y completa el inicio de sesión
    """
    # Si recibimos parámetro provider directamente, usarlo, sino extraerlo del state
    if provider is None and 'state' in request.GET:
        state_parts = request.GET.get('state', '').split('|')
        provider = state_parts[1] if len(state_parts) > 1 else None
    
    if 'error' in request.GET:
        error = request.GET.get('error')
        return HttpResponseRedirect(f"{FRONTEND_URL}/login?error={error}")
    
    code = request.GET.get('code')
    if not code:
        return HttpResponseRedirect(f"{FRONTEND_URL}/login?error=no_code")
    
    try:
        if provider == 'google':
            social_app = SocialApp.objects.get(provider='google')
            token_url = 'https://oauth2.googleapis.com/token'
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        elif provider == 'microsoft':
            social_app = SocialApp.objects.get(provider='microsoft')
            token_url = 'https://login.microsoftonline.com/consumers/oauth2/v2.0/token'
            userinfo_url = 'https://graph.microsoft.com/v1.0/me'
        else:
            return HttpResponseRedirect(f"{settings.FRONTEND_URL}/login?error=invalid_provider")
        
        # URL de callback exactamente igual a la configurada en los proveedores
        callback_url = f"{request.build_absolute_uri('/').rstrip('/')}/api/auth/social/callback/"
        
        # Obtener token
        token_data = {
            'code': code,
            'client_id': social_app.client_id,
            'client_secret': social_app.secret,
            'redirect_uri': callback_url,
            'grant_type': 'authorization_code',
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            print("Error obteniendo token:", token_json)
            return HttpResponseRedirect(f"{FRONTEND_URL}/login?error=token_error")
        
        # Obtener datos del usuario
        headers = {
            'Authorization': f"Bearer {token_json['access_token']}"
        }
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo = userinfo_response.json()
        
        # Extraer email y datos de usuario
        email = userinfo.get('email')
        if not email and provider == 'microsoft':
            email = userinfo.get('userPrincipalName')
        
        if not email:
            return HttpResponseRedirect(f"{FRONTEND_URL}/login?error=no_email")
        
        # Crear o actualizar usuario
        try:
            usuario = Usuari.objects.get(email=email)
            # Actualizar los datos del usuario existente
            has_changed = False
            
            if provider == 'google':
                if 'given_name' in userinfo and not usuario.first_name:
                    usuario.first_name = userinfo.get('given_name', '')
                    has_changed = True
                if 'family_name' in userinfo and not usuario.last_name:
                    usuario.last_name = userinfo.get('family_name', '')
                    has_changed = True
            elif provider == 'microsoft':
                if 'givenName' in userinfo and not usuario.first_name:
                    usuario.first_name = userinfo.get('givenName', '')
                    has_changed = True
                if 'surname' in userinfo and not usuario.last_name:
                    usuario.last_name = userinfo.get('surname', '')
                    has_changed = True
            
            # Guardar cambios si se realizaron
            if has_changed:
                usuario.save()
                
        except Usuari.DoesNotExist:
            # Crear usuario
            username = email.split('@')[0]
            
            # Verificar si el username ya existe y generar uno único si es necesario
            base_username = username
            count = 1
            while Usuari.objects.filter(username=username).exists():
                username = f"{base_username}{count}"
                count += 1
            
            # Extraer nombre según el proveedor
            if provider == 'google':
                first_name = userinfo.get('given_name', '')
                last_name = userinfo.get('family_name', '')
            else:  # microsoft
                first_name = userinfo.get('givenName', '')
                last_name = userinfo.get('surname', '')
            
            usuario = Usuari(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            usuario.save()
            
            # Crear relación con la cuenta social (importante para Microsoft)
            social_account = SocialAccount(
                user=usuario,
                provider=provider,
                uid=userinfo.get('sub', '') if provider == 'google' else userinfo.get('id', ''),
                extra_data=userinfo
            )
            social_account.save()
        
        # Iniciar sesión
        login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
        
        # Generar token para API
        from django.utils.crypto import get_random_string
        auth_token = get_random_string(32)
        
        # Guardar token en sesión para ser recogido por el frontend
        request.session['auth_token'] = auth_token
        
        # Redirigir al frontend
        return HttpResponseRedirect(f"{FRONTEND_URL}/?logged_in=true&token={auth_token}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponseRedirect(f"{FRONTEND_URL}/login?error=auth_error&details={str(e)}")

@ensure_csrf_cookie
def get_session_info(request):
    """
    Devuelve información sobre la sesión actual y el usuario autenticado
    """
    user = request.user
    
    # Generar token CSRF para solicitudes posteriores
    csrf_token = get_token(request)
    
    if user.is_authenticated:
        return JsonResponse({
            'isAuthenticated': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser
            },
            'csrfToken': csrf_token
        })
    else:
        return JsonResponse({
            'isAuthenticated': False,
            'csrfToken': csrf_token
        })

def login_success(request):
    """
    Página de éxito después del login - redirige al frontend
    """
    next_url = request.GET.get('next', '/')
    return HttpResponseRedirect(f"{settings.FRONTEND_URL}{next_url}")

def logout_success(request):
    """
    Página de éxito después del logout - redirige al frontend
    """
    return HttpResponseRedirect(f"{settings.FRONTEND_URL}/login?logged_out=true")

# Index View
def index(response):
    try:
        tpl = get_template("index.html")
        return render(response,"index.html")
    except TemplateDoesNotExist:
        return HttpResponse("Backend OK. Posa en marxa el frontend seguint el README.")

# ImportCSV
# Pendiente añadir autenticación
@csrf_exempt
def import_users(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
        created_count = 0
        errors_count = 0
        error_details = []

        for user_data in data:
            try:
                email = user_data.get("email")
                telefon = user_data.get("telefon")

                # Validar que el email no está en uso
                if Usuari.objects.filter(email=email).exists():
                    error_details.append({
                        "email": email,
                        "error": "El email ya existe en la base de datos"
                    })
                    errors_count += 1
                    continue

                # Validar que el teléfono no está en uso
                if telefon and Usuari.objects.filter(telefon=telefon).exists():
                    error_details.append({
                        "email": email,
                        "error": "El teléfono ya está registrado en la base de datos"
                    })
                    errors_count += 1
                    continue

                # Búsqueda o creación de Centro
                centre = None
                if "centre" in user_data and user_data["centre"]:
                    centre, _ = Centre.objects.get_or_create(
                        nom=user_data["centre"]
                    )

                # Búsqueda o creación de Ciclo
                cicle = None
                if "grup" in user_data and user_data["grup"]:
                    cicle, _ = Cicle.objects.get_or_create(
                        nom=user_data["grup"]
                    )

                # Crear nuevo usuario con contraseña aleatoria temporal
                first_initial = user_data["nom"][0].lower() if user_data["nom"] else ""
                last_name1 = user_data.get("cognom1", "").lower()
                last_name2 = user_data.get("cognom2", "").lower()
                username = f"{first_initial}{last_name1}{last_name2}".strip()
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

                new_user = Usuari(
                    username=username,
                    email=email,
                    first_name=user_data["nom"],
                    last_name=f"{user_data.get('cognom1', '')} {user_data.get('cognom2', '')}".strip(),
                    telefon=telefon,
                    centre=centre,
                    cicle=cicle
                )
                new_user.set_password(temp_password)
                new_user.save()
                created_count += 1

            except Exception as e:
                error_details.append({
                    "email": user_data.get("email", "desconocido"),
                    "error": str(e)
                })
                errors_count += 1
                print(f"Error al procesar usuario {user_data.get('email', 'desconocido')}: {str(e)}")

        response_data = {
            "created": created_count,
            "errors": errors_count
        }

        if error_details:
            response_data["error_details"] = error_details

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

# Errores
def error_404(request, exception):
    return render(request, 'errors/Error404.html', status=404)

def error_403(request, exception=None):
    return render(request, 'errors/Error403.html', status=403)