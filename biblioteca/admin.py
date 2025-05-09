from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import escape, mark_safe


from .models import *

class CategoriaAdmin(admin.ModelAdmin):
	list_display = ('nom','parent')
	ordering = ('parent','nom')


class UsuariAdmin(UserAdmin):
    # Obtener una copia de los fieldsets originals
    fieldsets = list(UserAdmin.fieldsets)
    # Modificar la tupla de 'Personal info' (que está en el índice 1)
    fieldsets[1] = (
        'Informació personal', 
        {'fields': fieldsets[1][1]['fields'] + ('telefon',)}
    )
    # Añadir la sección de datos académicos
    fieldsets = tuple(fieldsets) + (
        ("Dades acadèmiques", {
            'fields': ('centre','grup','imatge'),
        }),
    )

class ExemplarsInline(admin.TabularInline):
    model = Exemplar
    extra = 1
    fields = ('centre', 'exclos_prestec', 'baixa')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "centre":
            if not request.user.is_superuser and request.user.centre:
                kwargs["initial"] = request.user.centre
                kwargs["disabled"] = True
                kwargs["queryset"] = Centre.objects.filter(id=request.user.centre.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.centre:
            return qs.filter(centre=request.user.centre)
        return qs

class LlibreAdmin(admin.ModelAdmin):
	filter_horizontal = ('tags',)
	inlines = [ExemplarsInline,]
	search_fields = ('titol','autor','CDU','signatura','ISBN','editorial','colleccio')
	list_display = ('titol','autor','editorial','num_exemplars')
	readonly_fields = ('thumb',)
	def num_exemplars(self,obj):
		return obj.exemplar_set.count()
	def thumb(self,obj):
		return mark_safe("<img src='{}' />".format(escape(obj.thumbnail_url)))
	thumb.allow_tags = True

class CatalegAdmin(admin.ModelAdmin):
    list_display = ('titol', 'autor', 'CDU', 'signatura')
    search_fields = ('titol', 'autor', 'CDU', 'signatura')
    filter_horizontal = ('tags',)

class DVDAdmin(admin.ModelAdmin):
    list_display = ('titol', 'autor', 'productora', 'duracio')
    search_fields = ('titol', 'autor', 'productora')
    inlines = [ExemplarsInline,]

class BRAdmin(admin.ModelAdmin):
    list_display = ('titol', 'autor', 'productora', 'duracio')
    search_fields = ('titol', 'autor', 'productora')
    inlines = [ExemplarsInline,]

class CDAdmin(admin.ModelAdmin):
    list_display = ('titol', 'autor', 'discografica', 'estil', 'duracio')
    search_fields = ('titol', 'autor', 'discografica', 'estil')
    inlines = [ExemplarsInline,]

class LogAdmin(admin.ModelAdmin):
    list_display = ('usuari', 'accio', 'data_accio', 'tipus')
    list_filter = ('tipus', 'data_accio')
    search_fields = ('usuari', 'accio')
    readonly_fields = ('data_accio',)

class ExemplarAdmin(admin.ModelAdmin):
    list_display = ('registre', 'cataleg', 'centre', 'exclos_prestec', 'baixa')
    list_filter = ('centre', 'exclos_prestec', 'baixa')
    search_fields = ('registre', 'cataleg__titol')
    readonly_fields = ['registre', 'cdu']  # Añadimos 'cdu' como campo de solo lectura
    fields = ('registre', 'cataleg', 'centre', 'exclos_prestec', 'baixa', 'cdu')  # Incluimos 'cdu' en los campos

    def cdu(self, obj):
        return obj.cataleg.CDU if obj.cataleg else "N/A"  # Obtenemos el CDU del catálogo relacionado
    cdu.short_description = "CDU"  # Etiqueta para el campo en el admin

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser and request.user.centre:
            form.base_fields['centre'].initial = request.user.centre
            form.base_fields['centre'].disabled = True
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.centre:
            return qs.filter(centre=request.user.centre)
        return qs

class RevistaAdmin(admin.ModelAdmin):
    inlines = [ExemplarsInline,]
    list_display = ('titol', 'autor', 'editorial')
    search_fields = ('titol', 'autor', 'editorial')

class DispositiuAdmin(admin.ModelAdmin):
    inlines = [ExemplarsInline,]
    list_display = ('titol', 'marca', 'model')
    search_fields = ('titol', 'marca', 'model')

admin.site.register(Usuari,UsuariAdmin)
admin.site.register(Categoria,CategoriaAdmin)
admin.site.register(Pais)
admin.site.register(Llengua)
admin.site.register(Llibre,LlibreAdmin)
admin.site.register(Revista, RevistaAdmin)
admin.site.register(Dispositiu, DispositiuAdmin)
admin.site.register(Imatge)
admin.site.register(Cataleg, CatalegAdmin)
admin.site.register(DVD, DVDAdmin)
admin.site.register(BR, BRAdmin)
admin.site.register(CD, CDAdmin)
admin.site.register(Log, LogAdmin)
admin.site.register(Exemplar, ExemplarAdmin)

class PrestecAdmin(admin.ModelAdmin):
    readonly_fields = ('data_prestec',)
    fields = ('exemplar','usuari','data_prestec','data_retorn','anotacions')
    list_display = ('exemplar','usuari','data_prestec','data_retorn')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.centre:
            return qs.filter(exemplar__centre=request.user.centre)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and request.user.centre:
            if db_field.name == "exemplar":
                kwargs["queryset"] = Exemplar.objects.filter(centre=request.user.centre)
            elif db_field.name == "usuari":
                kwargs["queryset"] = Usuari.objects.filter(centre=request.user.centre)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Centre)
admin.site.register(Grup)
admin.site.register(Reserva)
admin.site.register(Prestec,PrestecAdmin)
admin.site.register(Peticio)
