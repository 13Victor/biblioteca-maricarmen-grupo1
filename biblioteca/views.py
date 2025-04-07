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
from .models import Usuari, Centre, Cicle
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
        updated_count = 0
        errors_count = 0
        error_details = []

        for user_data in data:
            try:
                email = user_data.get("email")
                telefon = user_data.get("telefon")

                # Validar que el email no está en uso por otro usuario
                existing_email = Usuari.objects.filter(email=email).exists()
                
                # Error si el email ya existe
                if existing_email:
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
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                new_user = Usuari(
                    username=email,  # Usar el email como username
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
                errors_count += 1
                error_details.append({
                    "email": user_data.get("email", "desconocido"),
                    "error": str(e)
                })
                print(f"Error al procesar usuario {user_data.get('email', 'desconocido')}: {str(e)}")
        
        response_data = {
            "created": created_count,
            "updated": updated_count,
            "errors": errors_count
        }
        
        # Agregar detalles de errores si hay alguno
        if error_details:
            response_data["error_details"] = error_details
            
        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)