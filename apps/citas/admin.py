from django.contrib import admin

from .models import Cita


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ["paciente", "doctor", "fecha_hora_inicio", "fecha_hora_fin", "estado", "version"]
    list_filter = ["estado", "doctor__especialidad", "fecha_hora_inicio"]
    search_fields = ["paciente__usuario__email", "doctor__usuario__email", "motivo_consulta"]
    readonly_fields = ["id", "version", "created_at", "updated_at"]
    date_hierarchy = "fecha_hora_inicio"
