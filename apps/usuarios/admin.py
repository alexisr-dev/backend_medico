from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "rol", "is_active", "date_joined"]
    list_filter = ["rol", "is_active", "is_staff", "mfa_habilitado"]
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["id", "created_at", "updated_at", "last_login"]
    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "telefono")}),
        ("Rol y seguridad", {"fields": ("rol", "mfa_habilitado", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "rol", "password1", "password2")}),
    )
