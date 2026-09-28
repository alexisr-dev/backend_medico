from django.contrib import admin

from .models import BloqueoHorario, DisponibilidadHoraria, DoctorPerfil, Especialidad


class DisponibilidadInline(admin.TabularInline):
    model = DisponibilidadHoraria
    extra = 1


@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "descripcion"]
    search_fields = ["nombre"]


@admin.register(DoctorPerfil)
class DoctorPerfilAdmin(admin.ModelAdmin):
    list_display = ["usuario", "especialidad", "numero_licencia", "duracion_consulta_default", "activo"]
    list_filter = ["especialidad", "activo"]
    search_fields = ["usuario__email", "usuario__first_name", "usuario__last_name", "numero_licencia"]
    autocomplete_fields = ["usuario"]
    inlines = [DisponibilidadInline]


@admin.register(BloqueoHorario)
class BloqueoHorarioAdmin(admin.ModelAdmin):
    list_display = ["doctor", "fecha_inicio", "fecha_fin", "motivo"]
    list_filter = ["doctor"]
