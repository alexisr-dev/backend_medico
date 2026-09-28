from django.conf import settings
from django.db import models


class AccionAuditoria(models.TextChoices):
    LECTURA = "lectura", "Lectura"
    ESCRITURA = "escritura", "Escritura"
    EXPORTACION = "exportacion", "Exportacion"
    ELIMINACION = "eliminacion", "Eliminacion"


class AuditoriaAcceso(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="accesos_auditados"
    )
    accion = models.CharField(max_length=20, choices=AccionAuditoria.choices, db_index=True)
    modelo_afectado = models.CharField(max_length=80, db_index=True)
    objeto_id = models.CharField(max_length=64, blank=True)
    ruta = models.CharField(max_length=255, blank=True)
    metodo = models.CharField(max_length=10, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "auditoria_acceso"
        verbose_name = "Acceso auditado"
        verbose_name_plural = "Accesos auditados"
        ordering = ["-fecha"]
        indexes = [models.Index(fields=["usuario", "-fecha"], name="idx_auditoria_usuario_fecha")]

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} {self.usuario_id} {self.accion} {self.modelo_afectado}"
