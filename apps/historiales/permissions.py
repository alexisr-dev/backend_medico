from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.citas.services import puede_ver_historial


class AccesoHistorialControlado(BasePermission):
    message = "No tienes autorizacion para acceder a este historial clinico."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        paciente = self._paciente_de(obj)
        if paciente is None:
            return False

        if request.method in SAFE_METHODS:
            return puede_ver_historial(request.user, paciente)

        usuario = request.user
        if usuario.es_admin:
            return True
        return usuario.es_doctor and puede_ver_historial(usuario, paciente)

    def _paciente_de(self, obj):
        if hasattr(obj, "paciente"):
            return obj.paciente
        if hasattr(obj, "historial"):
            return obj.historial.paciente
        if hasattr(obj, "registro_consulta"):
            return obj.registro_consulta.historial.paciente
        return None


class SoloDoctorEscribeConsulta(BasePermission):
    message = "Solo el doctor que atendio la cita puede registrar la consulta."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and (request.user.es_doctor or request.user.es_admin))
