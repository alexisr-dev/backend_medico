from datetime import date

from django.conf import settings
from django.db import models

from apps.core.fields import CharCifradoField
from apps.core.models import ModeloBase


class Genero(models.TextChoices):
    MASCULINO = "masculino", "Masculino"
    FEMENINO = "femenino", "Femenino"
    OTRO = "otro", "Otro"
    NO_ESPECIFICA = "no_especifica", "Prefiere no decirlo"


class PacientePerfil(ModeloBase):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_paciente"
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=20, choices=Genero.choices, blank=True)
    direccion = CharCifradoField(blank=True, default="")
    contacto_emergencia = CharCifradoField(blank=True, default="")
    numero_seguro = CharCifradoField(blank=True, default="")

    class Meta(ModeloBase.Meta):
        db_table = "pacientes_perfil"
        verbose_name = "Perfil de paciente"
        verbose_name_plural = "Perfiles de pacientes"

    def __str__(self):
        return self.usuario.nombre_completo

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        return hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
