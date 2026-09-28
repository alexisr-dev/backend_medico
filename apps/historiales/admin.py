from django.contrib import admin

from .models import ArchivoMedico, HistorialMedico, Receta, RegistroConsulta


class RecetaInline(admin.TabularInline):
    model = Receta
    extra = 0


@admin.register(HistorialMedico)
class HistorialMedicoAdmin(admin.ModelAdmin):
    list_display = ["paciente", "tipo_sangre", "updated_at"]
    search_fields = ["paciente__usuario__email", "paciente__usuario__first_name"]


@admin.register(RegistroConsulta)
class RegistroConsultaAdmin(admin.ModelAdmin):
    list_display = ["cita", "historial", "created_at"]
    inlines = [RecetaInline]


@admin.register(ArchivoMedico)
class ArchivoMedicoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "registro_consulta", "created_at"]
    list_filter = ["tipo"]
