from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import escape, mark_safe


from .models import *

class CategoriaAdmin(admin.ModelAdmin):
	list_display = ('nom','parent')
	ordering = ('parent','nom')


class UsuariAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
            ("Dades acadèmiques", {
                'fields': ('centre','cicle','imatge'),
            }),
    )

class ExemplarsInline(admin.TabularInline):
	model = Exemplar
	extra = 1
	readonly_fields = ('pk',)
	fields = ('pk','registre','exclos_prestec','baixa')

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

	def get_form(self, request, obj=None, **kwargs):
		form = super().get_form(request, obj, **kwargs)
		if not obj and request.user.is_staff and not request.user.is_superuser and request.user.centre:
			form.base_fields['lloc'].initial = request.user.centre.nom
		return form

class RevistaAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)
    inlines = [ExemplarsInline,]
    search_fields = ('titol','autor','CDU','signatura','ISSN','editorial')
    list_display = ('titol','autor','editorial','num_exemplars')
    def num_exemplars(self,obj):
        return obj.exemplar_set.count()

class CDAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)
    inlines = [ExemplarsInline,]
    search_fields = ('titol','autor','CDU','signatura','discografica','estil')
    list_display = ('titol','autor','discografica','estil','num_exemplars')
    def num_exemplars(self,obj):
        return obj.exemplar_set.count()

class DVDAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)
    inlines = [ExemplarsInline,]
    search_fields = ('titol','autor','CDU','signatura','productora')
    list_display = ('titol','autor','productora','num_exemplars')
    def num_exemplars(self,obj):
        return obj.exemplar_set.count()

class BRAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)
    inlines = [ExemplarsInline,]
    search_fields = ('titol','autor','CDU','signatura','productora')
    list_display = ('titol','autor','productora','num_exemplars')
    def num_exemplars(self,obj):
        return obj.exemplar_set.count()

class DispositiuAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)
    inlines = [ExemplarsInline,]
    search_fields = ('titol','CDU','signatura','marca','model')
    list_display = ('titol','marca','model','num_exemplars')
    def num_exemplars(self,obj):
        return obj.exemplar_set.count()

admin.site.register(Usuari,UsuariAdmin)
admin.site.register(Categoria,CategoriaAdmin)
admin.site.register(Pais)
admin.site.register(Llengua)
admin.site.register(Llibre, LlibreAdmin)
admin.site.register(Revista, RevistaAdmin)
admin.site.register(CD, CDAdmin)
admin.site.register(DVD, DVDAdmin)
admin.site.register(BR, BRAdmin)
admin.site.register(Dispositiu, DispositiuAdmin)
admin.site.register(Imatge)

class PrestecAdmin(admin.ModelAdmin):
    readonly_fields = ('data_prestec',)
    fields = ('exemplar','usuari','data_prestec','data_retorn','anotacions')
    list_display = ('exemplar','usuari','data_prestec','data_retorn')

admin.site.register(Centre)
admin.site.register(Cicle)
admin.site.register(Reserva)
admin.site.register(Prestec,PrestecAdmin)
admin.site.register(Peticio)
