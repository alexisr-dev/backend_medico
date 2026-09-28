from rest_framework.permissions import BasePermission, SAFE_METHODS


class PuedeGestionarCita(BasePermission):
    message = "No tienes permiso sobre esta cita."

    def has_object_permission(self, request, view, obj):
        usuario = request.user
        if usuario.es_admin:
            return True
        if usuario.es_doctor:
            return obj.doctor.usuario_id == usuario.id
        return obj.paciente.usuario_id == usuario.id


class SoloDoctorCierraCita(BasePermission):
    message = "Solo el doctor asignado o un administrador puede cerrar la cita."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        usuario = request.user
        return usuario.es_admin or (usuario.es_doctor and obj.doctor.usuario_id == usuario.id)
