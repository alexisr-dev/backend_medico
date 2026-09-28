from django.conf import settings
from django.db import models

from apps.core.models import ModeloBase


class TipoNotificacion(models.TextChoices):
    CITA_CREADA = "cita_creada", "Cita creada"
    CITA_CONFIRMADA = "cita_confirmada", "Cita confirmada"
    CITA_CANCELADA = "cita_cancelada", "Cita cancelada"
    CITA_REPROGRAMADA = "cita_reprogramada", "Cita reprogramada"
    RECORDATORIO = "recordatorio", "Recordatorio"
    SISTEMA = "sistema", "Sistema"


class CanalRecordatorio(models.TextChoices):
    EMAIL = "email", "Correo electronico"
    SMS = "sms", "SMS"
    PUSH = "push", "Push"


class Notificacion(ModeloBase):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones"
    )
    titulo = models.CharField(max_length=160)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=30, choices=TipoNotificacion.choices, default=TipoNotificacion.SISTEMA)
    leido = models.BooleanField(default=False, db_index=True)
    url_destino = models.CharField(max_length=255, blank=True)

    class Meta(ModeloBase.Meta):
        db_table = "notificaciones"
        verbose_name = "Notificacion"
        verbose_name_plural = "Notificaciones"
        indexes = [models.Index(fields=["usuario", "leido", "-created_at"], name="idx_notif_usuario_leido")]

    def __str__(self):
        return f"{self.titulo} -> {self.usuario.email}"


class Recordatorio(ModeloBase):
    cita = models.ForeignKey("citas.Cita", on_delete=models.CASCADE, related_name="recordatorios")
    tipo = models.CharField(max_length=20, choices=CanalRecordatorio.choices, default=CanalRecordatorio.EMAIL)
    fecha_envio_programada = models.DateTimeField(db_index=True)
    enviado = models.BooleanField(default=False, db_index=True)
    enviado_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta(ModeloBase.Meta):
        db_table = "recordatorios"
        verbose_name = "Recordatorio"
        verbose_name_plural = "Recordatorios"
        ordering = ["fecha_envio_programada"]
        constraints = [
            models.UniqueConstraint(
                fields=["cita", "tipo", "fecha_envio_programada"], name="uq_recordatorio_cita_canal_fecha"
            )
        ]

    def __str__(self):
        return f"Recordatorio {self.tipo} para {self.cita_id} el {self.fecha_envio_programada:%d/%m %H:%M}"
