from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.exceptions import ErrorNegocio
from apps.pacientes.models import PacientePerfil

from .models import Cita, EstadoCita
from .permissions import PuedeGestionarCita, SoloDoctorCierraCita
from .serializers import (
    CambiarEstadoSerializer,
    CancelarCitaSerializer,
    CitaSerializer,
    CrearCitaSerializer,
    ReprogramarCitaSerializer,
)
from .services import cambiar_estado, cancelar_cita, citas_visibles_para, crear_cita, reprogramar_cita


class CitaViewSet(viewsets.ModelViewSet):
    serializer_class = CitaSerializer
    queryset = Cita.objects.none()
    permission_classes = [IsAuthenticated, PuedeGestionarCita]
    filterset_fields = ["estado", "doctor", "paciente"]
    ordering_fields = ["fecha_hora_inicio", "created_at"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = citas_visibles_para(self.request.user)

        desde = self.request.query_params.get("desde")
        hasta = self.request.query_params.get("hasta")
        if desde:
            queryset = queryset.filter(fecha_hora_inicio__date__gte=desde)
        if hasta:
            queryset = queryset.filter(fecha_hora_inicio__date__lte=hasta)

        if self.request.query_params.get("proximas") == "true":
            queryset = queryset.filter(
                fecha_hora_inicio__gte=timezone.now(),
                estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA],
            ).order_by("fecha_hora_inicio")

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return CrearCitaSerializer
        return CitaSerializer

    def _paciente_de(self, serializer):
        usuario = self.request.user
        if usuario.es_paciente:
            perfil = PacientePerfil.objects.filter(usuario=usuario).first()
            if perfil is None:
                raise NotFound("No existe un perfil de paciente para este usuario.")
            return perfil

        perfil = serializer.validated_data.get("paciente")
        if perfil is None:
            raise ErrorNegocio("Debes indicar el paciente para el que se agenda la cita.")
        return perfil

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cita = crear_cita(
            paciente=self._paciente_de(serializer),
            doctor=serializer.validated_data["doctor"],
            inicio=serializer.validated_data["fecha_hora_inicio"],
            fin=serializer.validated_data["fecha_hora_fin"],
            motivo=serializer.validated_data["motivo_consulta"],
        )
        return Response(CitaSerializer(cita).data, status=status.HTTP_201_CREATED)

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "reserva"
        return super().get_throttles()

    @action(detail=True, methods=["post"])
    def reprogramar(self, request, pk=None):
        cita = self.get_object()
        serializer = ReprogramarCitaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        actualizada = reprogramar_cita(
            cita,
            inicio=serializer.validated_data["fecha_hora_inicio"],
            fin=serializer.validated_data.get("fecha_hora_fin"),
            version_esperada=serializer.validated_data.get("version"),
        )
        return Response(CitaSerializer(actualizada).data)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        cita = self.get_object()
        serializer = CancelarCitaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        actualizada = cancelar_cita(cita, request.user, serializer.validated_data["motivo_cancelacion"])
        return Response(CitaSerializer(actualizada).data)

    @action(detail=True, methods=["post"], url_path="estado", permission_classes=[IsAuthenticated, SoloDoctorCierraCita])
    def estado(self, request, pk=None):
        cita = self.get_object()
        serializer = CambiarEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        actualizada = cambiar_estado(
            cita,
            nuevo_estado=serializer.validated_data["estado"],
            notas=serializer.validated_data.get("notas_doctor"),
        )
        return Response(CitaSerializer(actualizada).data)

    @action(detail=False, methods=["get"], url_path="agenda-hoy")
    def agenda_hoy(self, request):
        if not (request.user.es_doctor or request.user.es_admin):
            raise PermissionDenied("Solo doctores y administradores.")

        hoy = timezone.localdate()
        queryset = (
            citas_visibles_para(request.user)
            .filter(fecha_hora_inicio__date=hoy)
            .exclude(estado=EstadoCita.CANCELADA)
            .order_by("fecha_hora_inicio")
        )
        return Response(CitaSerializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        base = citas_visibles_para(request.user)
        ahora = timezone.now()
        conteo = base.aggregate(
            pendientes=Count("id", filter=Q(estado=EstadoCita.PENDIENTE)),
            confirmadas=Count("id", filter=Q(estado=EstadoCita.CONFIRMADA)),
            completadas=Count("id", filter=Q(estado=EstadoCita.COMPLETADA)),
            canceladas=Count("id", filter=Q(estado=EstadoCita.CANCELADA)),
            no_asistio=Count("id", filter=Q(estado=EstadoCita.NO_ASISTIO)),
        )
        conteo["proximas_7_dias"] = base.filter(
            fecha_hora_inicio__range=(ahora, ahora + timedelta(days=7)),
            estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA],
        ).count()
        conteo["total"] = base.count()
        return Response(conteo)
