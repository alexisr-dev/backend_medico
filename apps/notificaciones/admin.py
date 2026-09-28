from django.contrib import admin

from .models import Notificacion, Recordatorio


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ["titulo", "usuario", "tipo", "leido", "created_at"]
    list_filter = ["tipo", "leido"]
    search_fields = ["titulo", "usuario__email"]


@admin.register(Recordatorio)
class RecordatorioAdmin(admin.ModelAdmin):
    list_display = ["cita", "tipo", "fecha_envio_programada", "enviado", "enviado_at"]
    list_filter = ["tipo", "enviado"]
