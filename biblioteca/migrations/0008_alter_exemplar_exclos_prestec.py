# Generated by Django 4.2.18 on 2025-04-10 10:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biblioteca', '0007_usuari_telefon'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exemplar',
            name='exclos_prestec',
            field=models.BooleanField(default=False),
        ),
    ]
