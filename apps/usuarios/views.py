from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.doctores.models import DoctorPerfil
from apps.pacientes.models import PacientePerfil

from .models import RolUsuario, Usuario
from .permissions import EsAdmin
from .serializers import (
    CambiarPasswordSerializer,
    LoginSerializer,
    RegistroDoctorSerializer,
    RegistroPacienteSerializer,
    UsuarioAdminSerializer,
    UsuarioSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_scope = "autenticacion"


class RegistroPacienteView(CreateAPIView):
    serializer_class = RegistroPacienteSerializer
    permission_classes = [AllowAny]
    throttle_scope = "autenticacion"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)


class RegistroDoctorView(CreateAPIView):
    serializer_class = RegistroDoctorSerializer
    permission_classes = [EsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(responses=UsuarioSerializer),
    patch=extend_schema(request=UsuarioSerializer, responses=UsuarioSerializer),
)
class PerfilActualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(self._payload(request.user))

    def patch(self, request):
        serializer = UsuarioSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._payload(request.user))

    def _payload(self, usuario):
        datos = UsuarioSerializer(usuario).data
        datos["perfil_id"] = None
        if usuario.es_paciente:
            perfil = PacientePerfil.objects.filter(usuario=usuario).first()
            datos["perfil_id"] = perfil.id if perfil else None
        elif usuario.es_doctor:
            perfil = DoctorPerfil.objects.select_related("especialidad").filter(usuario=usuario).first()
            if perfil:
                datos["perfil_id"] = perfil.id
                datos["especialidad"] = perfil.especialidad.nombre
                datos["duracion_consulta_default"] = perfil.duracion_consulta_default
        return datos


@extend_schema(request=CambiarPasswordSerializer, responses=OpenApiTypes.OBJECT)
class CambiarPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "autenticacion"

    def post(self, request):
        serializer = CambiarPasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Contrasena actualizada correctamente."})


class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioAdminSerializer
    queryset = Usuario.objects.none()
    permission_classes = [EsAdmin]
    filterset_fields = ["rol", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["date_joined", "first_name", "email"]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Usuario.objects.all()
        termino = self.request.query_params.get("q")
        if termino:
            queryset = queryset.filter(
                Q(email__icontains=termino) | Q(first_name__icontains=termino) | Q(last_name__icontains=termino)
            )
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        usuario = self.get_object()
        usuario.is_active = True
        usuario.save(update_fields=["is_active", "updated_at"])
        return Response(UsuarioAdminSerializer(usuario).data)

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        return Response(
            {
                "total": Usuario.objects.count(),
                "pacientes": Usuario.objects.filter(rol=RolUsuario.PACIENTE).count(),
                "doctores": Usuario.objects.filter(rol=RolUsuario.DOCTOR).count(),
                "administradores": Usuario.objects.filter(rol=RolUsuario.ADMIN).count(),
                "inactivos": Usuario.objects.filter(is_active=False).count(),
            }
        )
