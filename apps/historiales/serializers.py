from rest_framework import serializers

from apps.citas.models import Cita, EstadoCita

from .models import ArchivoMedico, HistorialMedico, Receta, RegistroConsulta


class RecetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receta
        fields = ["id", "registro_consulta", "medicamento", "dosis", "frecuencia", "duracion", "indicaciones"]


class ArchivoMedicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivoMedico
        fields = ["id", "registro_consulta", "archivo", "nombre", "tipo", "created_at"]
        read_only_fields = ["created_at"]


class RegistroConsultaSerializer(serializers.ModelSerializer):
    recetas = RecetaSerializer(many=True, read_only=True)
    archivos = ArchivoMedicoSerializer(many=True, read_only=True)
    doctor_nombre = serializers.CharField(source="cita.doctor.usuario.nombre_completo", read_only=True)
    especialidad = serializers.CharField(source="cita.doctor.especialidad.nombre", read_only=True)
    fecha_consulta = serializers.DateTimeField(source="cita.fecha_hora_inicio", read_only=True)

    class Meta:
        model = RegistroConsulta
        fields = [
            "id",
            "cita",
            "historial",
            "doctor_nombre",
            "especialidad",
            "fecha_consulta",
            "diagnostico",
            "tratamiento",
            "notas",
            "recetas",
            "archivos",
            "created_at",
        ]
        read_only_fields = ["historial", "created_at"]


class CrearRegistroConsultaSerializer(serializers.ModelSerializer):
    recetas = RecetaSerializer(many=True, required=False)

    class Meta:
        model = RegistroConsulta
        fields = ["cita", "diagnostico", "tratamiento", "notas", "recetas"]

    def validate_cita(self, cita):
        usuario = self.context["request"].user
        if not usuario.es_admin and cita.doctor.usuario_id != usuario.id:
            raise serializers.ValidationError("Solo puedes registrar consultas de tus propias citas.")
        if cita.estado != EstadoCita.COMPLETADA:
            raise serializers.ValidationError("La cita debe estar marcada como completada.")
        if RegistroConsulta.objects.filter(cita=cita).exists():
            raise serializers.ValidationError("Esta cita ya tiene un registro de consulta.")
        return cita

    def create(self, validated_data):
        recetas = validated_data.pop("recetas", [])
        cita: Cita = validated_data["cita"]
        historial, _ = HistorialMedico.objects.get_or_create(paciente=cita.paciente)
        registro = RegistroConsulta.objects.create(historial=historial, **validated_data)
        for receta in recetas:
            receta.pop("registro_consulta", None)
            Receta.objects.create(registro_consulta=registro, **receta)
        return registro


class HistorialMedicoSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source="paciente.usuario.nombre_completo", read_only=True)
    edad = serializers.IntegerField(source="paciente.edad", read_only=True)
    genero = serializers.CharField(source="paciente.genero", read_only=True)
    registros = RegistroConsultaSerializer(many=True, read_only=True)

    class Meta:
        model = HistorialMedico
        fields = [
            "id",
            "paciente",
            "paciente_nombre",
            "edad",
            "genero",
            "tipo_sangre",
            "alergias",
            "enfermedades_cronicas",
            "medicamentos_actuales",
            "antecedentes_familiares",
            "registros",
            "updated_at",
        ]
        read_only_fields = ["id", "paciente", "updated_at"]
