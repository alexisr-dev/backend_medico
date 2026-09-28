from rest_framework import serializers

from .models import BloqueoHorario, DisponibilidadHoraria, DoctorPerfil, Especialidad


class EspecialidadSerializer(serializers.ModelSerializer):
    total_doctores = serializers.IntegerField(read_only=True)

    class Meta:
        model = Especialidad
        fields = ["id", "nombre", "descripcion", "total_doctores"]


class DisponibilidadHorariaSerializer(serializers.ModelSerializer):
    dia_semana_display = serializers.CharField(source="get_dia_semana_display", read_only=True)

    class Meta:
        model = DisponibilidadHoraria
        fields = ["id", "doctor", "dia_semana", "dia_semana_display", "hora_inicio", "hora_fin", "activo"]
        read_only_fields = ["doctor"]

    def validate(self, attrs):
        inicio = attrs.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        fin = attrs.get("hora_fin", getattr(self.instance, "hora_fin", None))
        if inicio and fin and fin <= inicio:
            raise serializers.ValidationError({"hora_fin": "La hora de fin debe ser posterior a la de inicio."})
        return attrs


class BloqueoHorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloqueoHorario
        fields = ["id", "doctor", "fecha_inicio", "fecha_fin", "motivo", "created_at"]
        read_only_fields = ["doctor", "created_at"]

    def validate(self, attrs):
        inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))
        if inicio and fin and fin <= inicio:
            raise serializers.ValidationError({"fecha_fin": "La fecha de fin debe ser posterior a la de inicio."})
        return attrs


class DoctorPerfilSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source="usuario.nombre_completo", read_only=True)
    email = serializers.EmailField(source="usuario.email", read_only=True)
    telefono = serializers.CharField(source="usuario.telefono", read_only=True)
    especialidad_nombre = serializers.CharField(source="especialidad.nombre", read_only=True)
    disponibilidades = DisponibilidadHorariaSerializer(many=True, read_only=True)

    class Meta:
        model = DoctorPerfil
        fields = [
            "id",
            "usuario",
            "nombre_completo",
            "email",
            "telefono",
            "especialidad",
            "especialidad_nombre",
            "numero_licencia",
            "duracion_consulta_default",
            "biografia",
            "tarifa_consulta",
            "activo",
            "disponibilidades",
        ]
        read_only_fields = ["id", "usuario", "numero_licencia"]


class DoctorResumenSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source="usuario.nombre_completo", read_only=True)
    especialidad_nombre = serializers.CharField(source="especialidad.nombre", read_only=True)

    class Meta:
        model = DoctorPerfil
        fields = [
            "id",
            "nombre_completo",
            "especialidad",
            "especialidad_nombre",
            "duracion_consulta_default",
            "tarifa_consulta",
            "biografia",
            "activo",
        ]


class SlotSerializer(serializers.Serializer):
    inicio = serializers.DateTimeField()
    fin = serializers.DateTimeField()
    hora = serializers.CharField()
    duracion_minutos = serializers.IntegerField()
