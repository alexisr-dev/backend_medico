from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.services import registrar_acceso
from apps.citas.services import puede_ver_historial
from apps.pacientes.models import PacientePerfil

from .models import ArchivoMedico, HistorialMedico, Receta, RegistroConsulta
from .permissions import AccesoHistorialControlado, SoloDoctorEscribeConsulta
from .serializers import (
    ArchivoMedicoSerializer,
    CrearRegistroConsultaSerializer,
    HistorialMedicoSerializer,
    RecetaSerializer,
    RegistroConsultaSerializer,
)


class HistorialMedicoViewSet(viewsets.ModelViewSet):
    serializer_class = HistorialMedicoSerializer
    queryset = HistorialMedico.objects.none()
    permission_classes = [AccesoHistorialControlado]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        usuario = self.request.user
        base = HistorialMedico.objects.select_related("paciente__usuario").prefetch_related(
            "registros__recetas", "registros__archivos", "registros__cita__doctor__usuario"
        )

        if usuario.es_admin:
            return base
        if usuario.es_doctor:
            from apps.citas.models import Cita, EstadoCita

            ids = (
                Cita.objects.filter(doctor__usuario=usuario)
                .exclude(estado=EstadoCita.CANCELADA)
                .values_list("paciente_id", flat=True)
            )
            return base.filter(paciente_id__in=ids)
        return base.filter(paciente__usuario=usuario)

    def retrieve(self, request, *args, **kwargs):
        instancia = self.get_object()
        registrar_acceso(request, "lectura", "HistorialMedico", instancia.pk)
        return Response(self.get_serializer(instancia).data)

    def perform_update(self, serializer):
        registrar_acceso(self.request, "escritura", "HistorialMedico", serializer.instance.pk)
        serializer.save()

    @action(detail=False, methods=["get"], url_path="mi-historial")
    def mi_historial(self, request):
        perfil = PacientePerfil.objects.filter(usuario=request.user).first()
        if perfil is None:
            raise NotFound("No existe un perfil de paciente para este usuario.")

        historial, _ = HistorialMedico.objects.get_or_create(paciente=perfil)
        registrar_acceso(request, "lectura", "HistorialMedico", historial.pk)
        return Response(self.get_serializer(historial).data)

    @action(detail=False, methods=["get"], url_path=r"paciente/(?P<paciente_id>\d+)")
    def por_paciente(self, request, paciente_id=None):
        paciente = get_object_or_404(PacientePerfil.objects.select_related("usuario"), pk=paciente_id)
        if not puede_ver_historial(request.user, paciente):
            raise PermissionDenied("No tienes autorizacion para acceder a este historial clinico.")

        historial, _ = HistorialMedico.objects.get_or_create(paciente=paciente)
        registrar_acceso(request, "lectura", "HistorialMedico", historial.pk)
        return Response(self.get_serializer(historial).data)


class RegistroConsultaViewSet(viewsets.ModelViewSet):
    queryset = RegistroConsulta.objects.none()
    permission_classes = [IsAuthenticated, SoloDoctorEscribeConsulta, AccesoHistorialControlado]
    filterset_fields = ["historial", "cita"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        usuario = self.request.user
        base = RegistroConsulta.objects.select_related(
            "cita__doctor__usuario", "cita__doctor__especialidad", "historial__paciente__usuario"
        ).prefetch_related("recetas", "archivos")

        if usuario.es_admin:
            return base
        if usuario.es_doctor:
            return base.filter(cita__doctor__usuario=usuario)
        return base.filter(historial__paciente__usuario=usuario)

    def get_serializer_class(self):
        if self.action == "create":
            return CrearRegistroConsultaSerializer
        return RegistroConsultaSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registro = serializer.save()
        registrar_acceso(request, "escritura", "RegistroConsulta", registro.pk)
        return Response(RegistroConsultaSerializer(registro).data, status=201)

    def retrieve(self, request, *args, **kwargs):
        instancia = self.get_object()
        registrar_acceso(request, "lectura", "RegistroConsulta", instancia.pk)
        return Response(RegistroConsultaSerializer(instancia).data)


class RecetaViewSet(viewsets.ModelViewSet):
    serializer_class = RecetaSerializer
    queryset = Receta.objects.none()
    permission_classes = [IsAuthenticated, SoloDoctorEscribeConsulta, AccesoHistorialControlado]
    filterset_fields = ["registro_consulta"]

    def get_queryset(self):
        usuario = self.request.user
        base = Receta.objects.select_related("registro_consulta__historial__paciente__usuario")
        if usuario.es_admin:
            return base
        if usuario.es_doctor:
            return base.filter(registro_consulta__cita__doctor__usuario=usuario)
        return base.filter(registro_consulta__historial__paciente__usuario=usuario)


class ArchivoMedicoViewSet(viewsets.ModelViewSet):
    serializer_class = ArchivoMedicoSerializer
    queryset = ArchivoMedico.objects.none()
    permission_classes = [IsAuthenticated, SoloDoctorEscribeConsulta, AccesoHistorialControlado]
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["registro_consulta", "tipo"]

    def get_queryset(self):
        usuario = self.request.user
        base = ArchivoMedico.objects.select_related("registro_consulta__historial__paciente__usuario")
        if usuario.es_admin:
            return base
        if usuario.es_doctor:
            return base.filter(registro_consulta__cita__doctor__usuario=usuario)
        return base.filter(registro_consulta__historial__paciente__usuario=usuario)

    def perform_create(self, serializer):
        archivo = serializer.save()
        registrar_acceso(self.request, "escritura", "ArchivoMedico", archivo.pk)
