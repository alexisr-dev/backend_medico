from datetime import date, timedelta

from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.usuarios.permissions import EsAdmin, EsDoctorOAdmin

from .models import BloqueoHorario, DisponibilidadHoraria, DoctorPerfil, Especialidad
from .serializers import (
    BloqueoHorarioSerializer,
    DisponibilidadHorariaSerializer,
    DoctorPerfilSerializer,
    DoctorResumenSerializer,
    EspecialidadSerializer,
    SlotSerializer,
)
from .services import agenda_del_rango, slots_disponibles


class EspecialidadViewSet(viewsets.ModelViewSet):
    serializer_class = EspecialidadSerializer
    search_fields = ["nombre"]
    ordering_fields = ["nombre"]

    def get_queryset(self):
        return Especialidad.objects.annotate(
            total_doctores=Count("doctores", filter=Q(doctores__activo=True))
        )

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [EsAdmin()]


class DoctorPerfilViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorPerfilSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = None
    filterset_fields = ["especialidad", "activo"]
    search_fields = ["usuario__first_name", "usuario__last_name", "especialidad__nombre"]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return DoctorPerfil.objects.select_related("usuario", "especialidad").prefetch_related("disponibilidades")

    def get_serializer_class(self):
        if self.action == "list":
            return DoctorResumenSerializer
        return DoctorPerfilSerializer

    def perform_update(self, serializer):
        usuario = self.request.user
        if not usuario.es_admin and serializer.instance.usuario_id != usuario.id:
            raise PermissionDenied("Solo puedes editar tu propio perfil.")
        serializer.save()

    def _perfil_doctor_actual(self):
        perfil = DoctorPerfil.objects.select_related("usuario", "especialidad").filter(usuario=self.request.user).first()
        if perfil is None:
            raise NotFound("No existe un perfil de doctor para este usuario.")
        return perfil

    @action(detail=False, methods=["get"], url_path="mi-perfil", permission_classes=[EsDoctorOAdmin])
    def mi_perfil(self, request):
        return Response(DoctorPerfilSerializer(self._perfil_doctor_actual()).data)

    @action(detail=True, methods=["get"], url_path="disponibilidad", throttle_scope="disponibilidad")
    def disponibilidad(self, request, pk=None):
        doctor = self.get_object()
        fecha_texto = request.query_params.get("fecha")
        dia = parse_date(fecha_texto) if fecha_texto else date.today()
        if dia is None:
            raise ValidationError({"fecha": "Formato de fecha invalido. Usa YYYY-MM-DD."})

        slots = slots_disponibles(doctor, dia)
        return Response(
            {
                "doctor": doctor.id,
                "fecha": dia.isoformat(),
                "duracion_minutos": doctor.duracion_consulta_default,
                "slots": SlotSerializer(slots, many=True).data,
            }
        )

    @action(detail=True, methods=["get"], url_path="agenda", throttle_scope="disponibilidad")
    def agenda(self, request, pk=None):
        doctor = self.get_object()
        desde_texto = request.query_params.get("desde")
        hasta_texto = request.query_params.get("hasta")

        desde = parse_date(desde_texto) if desde_texto else date.today()
        if desde is None:
            raise ValidationError({"desde": "Formato de fecha invalido. Usa YYYY-MM-DD."})

        hasta = parse_date(hasta_texto) if hasta_texto else desde + timedelta(days=13)
        if hasta is None or hasta < desde:
            raise ValidationError({"hasta": "Debe ser una fecha posterior o igual a 'desde'."})

        return Response({"doctor": doctor.id, "agenda": agenda_del_rango(doctor, desde, hasta)})


class DisponibilidadHorariaViewSet(viewsets.ModelViewSet):
    serializer_class = DisponibilidadHorariaSerializer
    queryset = DisponibilidadHoraria.objects.none()
    permission_classes = [EsDoctorOAdmin]
    filterset_fields = ["doctor", "dia_semana", "activo"]

    def get_queryset(self):
        queryset = DisponibilidadHoraria.objects.select_related("doctor__usuario")
        if self.request.user.es_admin:
            return queryset
        return queryset.filter(doctor__usuario=self.request.user)

    def _doctor_objetivo(self):
        if self.request.user.es_admin and self.request.data.get("doctor"):
            doctor = DoctorPerfil.objects.filter(pk=self.request.data["doctor"]).first()
            if doctor is None:
                raise ValidationError({"doctor": "El doctor indicado no existe."})
            return doctor
        doctor = DoctorPerfil.objects.filter(usuario=self.request.user).first()
        if doctor is None:
            raise NotFound("No existe un perfil de doctor para este usuario.")
        return doctor

    def perform_create(self, serializer):
        serializer.save(doctor=self._doctor_objetivo())


class BloqueoHorarioViewSet(viewsets.ModelViewSet):
    serializer_class = BloqueoHorarioSerializer
    queryset = BloqueoHorario.objects.none()
    permission_classes = [EsDoctorOAdmin]
    filterset_fields = ["doctor"]

    def get_queryset(self):
        queryset = BloqueoHorario.objects.select_related("doctor__usuario")
        if self.request.user.es_admin:
            return queryset
        return queryset.filter(doctor__usuario=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.es_admin and self.request.data.get("doctor"):
            doctor = DoctorPerfil.objects.filter(pk=self.request.data["doctor"]).first()
            if doctor is None:
                raise ValidationError({"doctor": "El doctor indicado no existe."})
        else:
            doctor = DoctorPerfil.objects.filter(usuario=self.request.user).first()
            if doctor is None:
                raise NotFound("No existe un perfil de doctor para este usuario.")
        serializer.save(doctor=doctor)
