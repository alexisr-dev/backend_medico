from rest_framework import serializers

from .models import AuditoriaAcceso


class AuditoriaAccesoSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.nombre_completo", read_only=True)
    usuario_rol = serializers.CharField(source="usuario.rol", read_only=True)
    accion_display = serializers.CharField(source="get_accion_display", read_only=True)

    class Meta:
        model = AuditoriaAcceso
        fields = [
            "id",
            "usuario",
            "usuario_email",
            "usuario_nombre",
            "usuario_rol",
            "accion",
            "accion_display",
            "modelo_afectado",
            "objeto_id",
            "ruta",
            "metodo",
            "ip_address",
            "fecha",
        ]
        read_only_fields = fields
