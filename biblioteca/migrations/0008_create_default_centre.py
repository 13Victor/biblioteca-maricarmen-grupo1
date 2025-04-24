from django.db import migrations

def create_default_centre(apps, schema_editor):
    Centre = apps.get_model('biblioteca', 'Centre')
    Centre.objects.create(nom='Centre Principal')

class Migration(migrations.Migration):
    dependencies = [
        ('biblioteca', '0007_usuari_telefon'),  # Ajusta esto según tu número de migración anterior
    ]

    operations = [
        migrations.RunPython(create_default_centre),
    ]
