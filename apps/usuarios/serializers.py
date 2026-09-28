from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.doctores.models import DoctorPerfil, Especialidad
from apps.historiales.models import HistorialMedico
from apps.pacientes.models import PacientePerfil

from .models import RolUsuario, Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "nombre_completo",
            "telefono",
            "rol",
            "mfa_habilitado",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["id", "rol", "is_active", "date_joined"]


class UsuarioAdminSerializer(UsuarioSerializer):
    class Meta(UsuarioSerializer.Meta):
        read_only_fields = ["id", "date_joined"]


class RegistroPacienteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password], style={"input_type": "password"})
    password_confirmacion = serializers.CharField(write_only=True, style={"input_type": "password"})
    fecha_nacimiento = serializers.DateField(write_only=True, required=False, allow_null=True)
    genero = serializers.CharField(write_only=True, required=False, allow_blank=True)
    direccion = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Usuario
        fields = [
            "email",
            "first_name",
            "last_name",
            "telefono",
            "password",
            "password_confirmacion",
            "fecha_nacimiento",
            "genero",
            "direccion",
        ]

    def validate_email(self, value):
        if Usuario.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirmacion"):
            raise serializers.ValidationError({"password_confirmacion": "Las contrasenas no coinciden."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        datos_perfil = {
            "fecha_nacimiento": validated_data.pop("fecha_nacimiento", None),
            "genero": validated_data.pop("genero", ""),
            "direccion": validated_data.pop("direccion", ""),
        }
        password = validated_data.pop("password")
        usuario = Usuario.objects.create_user(password=password, rol=RolUsuario.PACIENTE, **validated_data)
        perfil = PacientePerfil.objects.create(usuario=usuario, **datos_perfil)
        HistorialMedico.objects.create(paciente=perfil)
        return usuario


class RegistroDoctorSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password], style={"input_type": "password"})
    especialidad_id = serializers.PrimaryKeyRelatedField(queryset=Especialidad.objects.all(), write_only=True)
    numero_licencia = serializers.CharField(write_only=True, max_length=60)
    duracion_consulta_default = serializers.IntegerField(write_only=True, default=30, min_value=10, max_value=180)
    biografia = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Usuario
        fields = [
            "email",
            "first_name",
            "last_name",
            "telefono",
            "password",
            "especialidad_id",
            "numero_licencia",
            "duracion_consulta_default",
            "biografia",
        ]

    def validate_email(self, value):
        if Usuario.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return value.lower()

    def validate_numero_licencia(self, value):
        if DoctorPerfil.objects.filter(numero_licencia=value).exists():
            raise serializers.ValidationError("Ya existe un doctor con esta licencia.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        datos_perfil = {
            "especialidad": validated_data.pop("especialidad_id"),
            "numero_licencia": validated_data.pop("numero_licencia"),
            "duracion_consulta_default": validated_data.pop("duracion_consulta_default", 30),
            "biografia": validated_data.pop("biografia", ""),
        }
        password = validated_data.pop("password")
        usuario = Usuario.objects.create_user(password=password, rol=RolUsuario.DOCTOR, **validated_data)
        DoctorPerfil.objects.create(usuario=usuario, **datos_perfil)
        return usuario


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_nueva = serializers.CharField(write_only=True, validators=[validate_password], style={"input_type": "password"})

    def validate_password_actual(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("La contrasena actual es incorrecta.")
        return value

    def save(self, **kwargs):
        usuario = self.context["request"].user
        usuario.set_password(self.validated_data["password_nueva"])
        usuario.save(update_fields=["password", "updated_at"])
        return usuario


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["rol"] = user.rol
        token["email"] = user.email
        token["nombre"] = user.nombre_completo
        return token

    def validate(self, attrs):
        datos = super().validate(attrs)
        datos["usuario"] = UsuarioSerializer(self.user).data
        datos["perfil_id"] = self._perfil_id()
        return datos

    def _perfil_id(self):
        if self.user.es_paciente:
            perfil = PacientePerfil.objects.filter(usuario=self.user).first()
            return perfil.id if perfil else None
        if self.user.es_doctor:
            perfil = DoctorPerfil.objects.filter(usuario=self.user).first()
            return perfil.id if perfil else None
        return None
