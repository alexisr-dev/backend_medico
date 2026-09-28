from rest_framework.permissions import BasePermission

from .models import RolUsuario


class EsPaciente(BasePermission):
    message = "Se requiere el rol de paciente."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol == RolUsuario.PACIENTE)


class EsDoctor(BasePermission):
    message = "Se requiere el rol de doctor."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol == RolUsuario.DOCTOR)


class EsAdmin(BasePermission):
    message = "Se requiere el rol de administrador."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.es_admin)


class EsDoctorOAdmin(BasePermission):
    message = "Se requiere el rol de doctor o administrador."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.rol == RolUsuario.DOCTOR or request.user.es_admin


class EsPropietarioOAdmin(BasePermission):
    message = "Solo puedes acceder a tus propios datos."

    def has_object_permission(self, request, view, obj):
        if request.user.es_admin:
            return True
        propietario = getattr(obj, "usuario", None) or getattr(obj, "user", None)
        return propietario == request.user
