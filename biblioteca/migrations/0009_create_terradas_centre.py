from django.db import migrations

def create_terradas_centre(apps, schema_editor):
    Centre = apps.get_model('biblioteca', 'Centre')
    Centre.objects.create(nom='IES Esteve Terradas i Illa')

def remove_terradas_centre(apps, schema_editor):
    Centre = apps.get_model('biblioteca', 'Centre')
    Centre.objects.filter(nom='IES Esteve Terradas i Illa').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('biblioteca', '0008_create_default_centre'),  # Ajusta esto según tu número de migración anterior
    ]

    operations = [
        migrations.RunPython(create_terradas_centre, remove_terradas_centre),
    ]
