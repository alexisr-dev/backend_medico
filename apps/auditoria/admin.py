from django.contrib import admin

from .models import AuditoriaAcceso


@admin.register(AuditoriaAcceso)
class AuditoriaAccesoAdmin(admin.ModelAdmin):
    list_display = ["fecha", "usuario", "accion", "modelo_afectado", "objeto_id", "ip_address"]
    list_filter = ["accion", "modelo_afectado", "fecha"]
    search_fields = ["usuario__email", "objeto_id", "ruta"]
    readonly_fields = [f.name for f in AuditoriaAcceso._meta.fields]
    date_hierarchy = "fecha"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
