# Default Django imports
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from django.template.exceptions import TemplateDoesNotExist
# ImportCSV
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
from .models import Usuari, Centre, Grup
import random
import string
# More imports ...

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
                        "error": "El email ja existeix"
                    })
                    errors_count += 1
                    continue
                
                # Validar que el teléfono no está en uso
                if telefon and Usuari.objects.filter(telefon=telefon).exists():
                    error_details.append({
                        "email": email,
                        "error": "El teléfon ja existeix"
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
                grup = None
                if "grup" in user_data and user_data["grup"]:
                    grup, _ = Grup.objects.get_or_create(
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
                    grup=grup
                )
                new_user.set_password(temp_password)
                new_user.save()
                created_count += 1
                    
            except Exception as e:
                errors_count += 1
                error_details.append({
                    "email": user_data.get("email", "desconocido"),
                    "error": str(e)
                })
                print(f"Error al procesar usuario {user_data.get('email', 'desconocido')}: {str(e)}")
        
        response_data = {
            "created": created_count,
            "errors": errors_count
        }
        
        # Agregar detalles de errores si hay alguno
        if error_details:
            response_data["error_details"] = error_details
            
        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

# Errores
def error_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def error_403(request, exception=None):
    return render(request, 'errors/403.html', status=403)