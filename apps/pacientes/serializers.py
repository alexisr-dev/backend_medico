from rest_framework import serializers

from .models import PacientePerfil


class PacientePerfilSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source="usuario.nombre_completo", read_only=True)
    email = serializers.EmailField(source="usuario.email", read_only=True)
    telefono = serializers.CharField(source="usuario.telefono", read_only=True)
    edad = serializers.IntegerField(read_only=True)

    class Meta:
        model = PacientePerfil
        fields = [
            "id",
            "usuario",
            "nombre_completo",
            "email",
            "telefono",
            "fecha_nacimiento",
            "edad",
            "genero",
            "direccion",
            "contacto_emergencia",
            "numero_seguro",
            "created_at",
        ]
        read_only_fields = ["id", "usuario", "created_at"]


class PacienteResumenSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source="usuario.nombre_completo", read_only=True)
    email = serializers.EmailField(source="usuario.email", read_only=True)
    edad = serializers.IntegerField(read_only=True)

    class Meta:
        model = PacientePerfil
        fields = ["id", "nombre_completo", "email", "edad", "genero"]
