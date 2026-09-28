from datetime import timedelta

from rest_framework import serializers

from apps.doctores.models import DoctorPerfil
from apps.pacientes.models import PacientePerfil

from .models import Cita, EstadoCita


class CitaSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source="paciente.usuario.nombre_completo", read_only=True)
    paciente_email = serializers.EmailField(source="paciente.usuario.email", read_only=True)
    doctor_nombre = serializers.CharField(source="doctor.usuario.nombre_completo", read_only=True)
    especialidad = serializers.CharField(source="doctor.especialidad.nombre", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    duracion_minutos = serializers.IntegerField(read_only=True)
    puede_cancelarse = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cita
        fields = [
            "id",
            "paciente",
            "paciente_nombre",
            "paciente_email",
            "doctor",
            "doctor_nombre",
            "especialidad",
            "fecha_hora_inicio",
            "fecha_hora_fin",
            "duracion_minutos",
            "estado",
            "estado_display",
            "motivo_consulta",
            "notas_doctor",
            "motivo_cancelacion",
            "puede_cancelarse",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CrearCitaSerializer(serializers.Serializer):
    doctor = serializers.PrimaryKeyRelatedField(queryset=DoctorPerfil.objects.filter(activo=True))
    paciente = serializers.PrimaryKeyRelatedField(queryset=PacientePerfil.objects.all(), required=False)
    fecha_hora_inicio = serializers.DateTimeField()
    fecha_hora_fin = serializers.DateTimeField(required=False)
    motivo_consulta = serializers.CharField(max_length=1000)

    def validate(self, attrs):
        doctor = attrs["doctor"]
        inicio = attrs["fecha_hora_inicio"]
        fin = attrs.get("fecha_hora_fin") or inicio + timedelta(minutes=doctor.duracion_consulta_default)
        if fin <= inicio:
            raise serializers.ValidationError({"fecha_hora_fin": "Debe ser posterior al inicio."})
        attrs["fecha_hora_fin"] = fin
        return attrs


class ReprogramarCitaSerializer(serializers.Serializer):
    fecha_hora_inicio = serializers.DateTimeField()
    fecha_hora_fin = serializers.DateTimeField(required=False)
    version = serializers.IntegerField(required=False)


class CancelarCitaSerializer(serializers.Serializer):
    motivo_cancelacion = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class CambiarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(
        choices=[EstadoCita.CONFIRMADA, EstadoCita.COMPLETADA, EstadoCita.NO_ASISTIO]
    )
    notas_doctor = serializers.CharField(required=False, allow_blank=True)
