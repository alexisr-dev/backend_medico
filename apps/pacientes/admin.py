from django.contrib import admin

from .models import PacientePerfil


@admin.register(PacientePerfil)
class PacientePerfilAdmin(admin.ModelAdmin):
    list_display = ["usuario", "fecha_nacimiento", "genero", "created_at"]
    list_filter = ["genero"]
    search_fields = ["usuario__email", "usuario__first_name", "usuario__last_name"]
    autocomplete_fields = ["usuario"]
