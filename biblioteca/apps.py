from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_bibliotecaris_group(sender, **kwargs):
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    from .models import (Exemplar, Llibre, Categoria, Cicle, Dispositiu, 
                        Imatge, Llengua, Pais, Prestec, Reserva, Revista,
                        DVD, BR, CD, Cataleg, Log, Peticio)  # Añadido Peticio

    # Create Bibliotecaris group if it doesn't exist
    bibliotecaris, created = Group.objects.get_or_create(name='Bibliotecaris')
    
    if created or True:  # Force update permissions
        # Lista específica de modelos que los bibliotecarios pueden gestionar
        models = [
            Exemplar,    # Añadido explícitamente
            Llibre,      # Añadido explícitamente
            Categoria,
            Cicle,
            Dispositiu,
            Imatge,
            Llengua,
            Pais,
            Prestec,
            Reserva,
            Revista,
            DVD,      # Añadido
            BR,       # Añadido
            CD,       # Añadido
            Cataleg,  # Añadido
            Log,      # Añadido
            Peticio   # Añadido Peticio a la lista
        ]
        
        # Primero, limpiar permisos existentes
        bibliotecaris.permissions.clear()
        
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            model_name = model._meta.model_name
            
            # Asignar los cuatro permisos básicos
            permissions = [
                f"add_{model_name}",
                f"change_{model_name}",
                f"delete_{model_name}",
                f"view_{model_name}"
            ]
            
            for permission_name in permissions:
                try:
                    permission = Permission.objects.get(
                        codename=permission_name,
                        content_type=content_type
                    )
                    bibliotecaris.permissions.add(permission)
                except Permission.DoesNotExist:
                    print(f"Permission {permission_name} does not exist")

class BibliotecaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'biblioteca'

    def ready(self):
        post_migrate.connect(create_bibliotecaris_group, sender=self)