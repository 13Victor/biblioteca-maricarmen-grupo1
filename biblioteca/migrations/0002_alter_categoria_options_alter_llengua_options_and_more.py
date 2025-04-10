# Generated by Django 4.2 on 2025-01-09 00:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('biblioteca', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='categoria',
            options={'verbose_name_plural': 'Categories'},
        ),
        migrations.AlterModelOptions(
            name='llengua',
            options={'verbose_name_plural': 'Llengües'},
        ),
        migrations.AlterModelOptions(
            name='pais',
            options={'verbose_name_plural': 'Països'},
        ),
        migrations.AlterModelOptions(
            name='peticio',
            options={'verbose_name_plural': 'Peticions'},
        ),
        migrations.AlterModelOptions(
            name='prestec',
            options={'verbose_name_plural': 'Préstecs'},
        ),
        migrations.AlterModelOptions(
            name='reserva',
            options={'verbose_name_plural': 'Reserves'},
        ),
        migrations.AlterModelOptions(
            name='revista',
            options={'verbose_name_plural': 'Revistes'},
        ),
        migrations.AlterField(
            model_name='cataleg',
            name='CDU',
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AlterField(
            model_name='cataleg',
            name='signatura',
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AlterField(
            model_name='cataleg',
            name='tags',
            field=models.ManyToManyField(blank=True, to='biblioteca.categoria'),
        ),
        migrations.AlterField(
            model_name='llibre',
            name='ISBN',
            field=models.CharField(blank=True, max_length=13, null=True),
        ),
        migrations.AlterField(
            model_name='llibre',
            name='pagines',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='revista',
            name='ISSN',
            field=models.CharField(blank=True, max_length=13, null=True),
        ),
        migrations.AlterField(
            model_name='revista',
            name='pagines',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='usuari',
            name='cicle',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='biblioteca.cicle'),
        ),
    ]
