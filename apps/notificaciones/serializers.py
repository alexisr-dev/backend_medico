from rest_framework import serializers

from .models import Notificacion, Recordatorio


class NotificacionSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Notificacion
        fields = ["id", "titulo", "mensaje", "tipo", "tipo_display", "leido", "url_destino", "created_at"]
        read_only_fields = ["id", "titulo", "mensaje", "tipo", "url_destino", "created_at"]


class RecordatorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recordatorio
        fields = ["id", "cita", "tipo", "fecha_envio_programada", "enviado", "enviado_at", "error"]
        read_only_fields = fields
