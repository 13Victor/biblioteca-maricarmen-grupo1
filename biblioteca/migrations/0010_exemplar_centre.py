from django.db import migrations, models
import django.db.models.deletion

def set_default_centre(apps, schema_editor):
    Centre = apps.get_model('biblioteca', 'Centre')
    Exemplar = apps.get_model('biblioteca', 'Exemplar')
    default_centre = Centre.objects.get(nom='IES Esteve Terradas i Illa')
    Exemplar.objects.filter(centre__isnull=True).update(centre=default_centre)

class Migration(migrations.Migration):
    dependencies = [
        ('biblioteca', '0009_create_terradas_centre'),
    ]

    operations = [
        migrations.AddField(
            model_name='exemplar',
            name='centre',
            field=models.ForeignKey(to='biblioteca.Centre', on_delete=django.db.models.deletion.PROTECT, null=True),
        ),
        migrations.RunPython(set_default_centre),
        migrations.AlterField(
            model_name='exemplar',
            name='centre',
            field=models.ForeignKey(to='biblioteca.Centre', on_delete=django.db.models.deletion.PROTECT),
        ),
    ]
