from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.citas.models import Cita, EstadoCita
from apps.usuarios.permissions import EsPropietarioOAdmin

from .models import PacientePerfil
from .serializers import PacientePerfilSerializer, PacienteResumenSerializer


class PacientePerfilViewSet(viewsets.ModelViewSet):
    serializer_class = PacientePerfilSerializer
    queryset = PacientePerfil.objects.none()
    permission_classes = [EsPropietarioOAdmin]
    search_fields = ["usuario__first_name", "usuario__last_name", "usuario__email"]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        usuario = self.request.user
        base = PacientePerfil.objects.select_related("usuario")

        if usuario.es_admin:
            return base
        if usuario.es_doctor:
            ids = Cita.objects.filter(doctor__usuario=usuario).values_list("paciente_id", flat=True)
            return base.filter(id__in=ids)
        return base.filter(usuario=usuario)

    @action(detail=False, methods=["get", "patch"], url_path="mi-perfil")
    def mi_perfil(self, request):
        perfil = PacientePerfil.objects.select_related("usuario").filter(usuario=request.user).first()
        if perfil is None:
            raise NotFound("No existe un perfil de paciente para este usuario.")

        if request.method == "PATCH":
            serializer = self.get_serializer(perfil, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(self.get_serializer(perfil).data)

    @action(detail=False, methods=["get"], url_path="mis-pacientes")
    def mis_pacientes(self, request):
        if not (request.user.es_doctor or request.user.es_admin):
            return Response({"detail": "Solo doctores y administradores.", "codigo": "permiso_denegado"}, status=403)

        queryset = self.get_queryset()
        termino = request.query_params.get("q")
        if termino:
            queryset = queryset.filter(
                Q(usuario__first_name__icontains=termino)
                | Q(usuario__last_name__icontains=termino)
                | Q(usuario__email__icontains=termino)
            )
        return Response(PacienteResumenSerializer(queryset.distinct(), many=True).data)

    @action(detail=True, methods=["get"])
    def citas(self, request, pk=None):
        from apps.citas.serializers import CitaSerializer

        perfil = self.get_object()
        queryset = (
            Cita.objects.select_related("doctor__usuario", "doctor__especialidad", "paciente__usuario")
            .filter(paciente=perfil)
            .exclude(estado=EstadoCita.CANCELADA)
            .order_by("-fecha_hora_inicio")
        )
        return Response(CitaSerializer(queryset, many=True).data)
