from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import ModeloBase


class DiaSemana(models.IntegerChoices):
    LUNES = 0, "Lunes"
    MARTES = 1, "Martes"
    MIERCOLES = 2, "Miercoles"
    JUEVES = 3, "Jueves"
    VIERNES = 4, "Viernes"
    SABADO = 5, "Sabado"
    DOMINGO = 6, "Domingo"


class Especialidad(ModeloBase):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta(ModeloBase.Meta):
        db_table = "especialidades"
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class DoctorPerfil(ModeloBase):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_doctor"
    )
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, related_name="doctores")
    numero_licencia = models.CharField(max_length=60, unique=True)
    duracion_consulta_default = models.PositiveIntegerField(
        default=30, validators=[MinValueValidator(10), MaxValueValidator(180)]
    )
    biografia = models.TextField(blank=True)
    tarifa_consulta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True, db_index=True)

    class Meta(ModeloBase.Meta):
        db_table = "doctores_perfil"
        verbose_name = "Perfil de doctor"
        verbose_name_plural = "Perfiles de doctores"
        ordering = ["usuario__first_name"]

    def __str__(self):
        return f"Dr(a). {self.usuario.nombre_completo} - {self.especialidad.nombre}"


class DisponibilidadHoraria(ModeloBase):
    doctor = models.ForeignKey(DoctorPerfil, on_delete=models.CASCADE, related_name="disponibilidades")
    dia_semana = models.IntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta(ModeloBase.Meta):
        db_table = "disponibilidad_horaria"
        verbose_name = "Disponibilidad horaria"
        verbose_name_plural = "Disponibilidades horarias"
        ordering = ["dia_semana", "hora_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hora_fin__gt=models.F("hora_inicio")),
                name="disponibilidad_rango_valido",
            ),
            models.UniqueConstraint(
                fields=["doctor", "dia_semana", "hora_inicio", "hora_fin"],
                name="uq_disponibilidad_doctor_bloque",
            ),
        ]

    def __str__(self):
        return f"{self.doctor} {self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin}"


class BloqueoHorario(ModeloBase):
    doctor = models.ForeignKey(DoctorPerfil, on_delete=models.CASCADE, related_name="bloqueos")
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    motivo = models.CharField(max_length=255, blank=True)

    class Meta(ModeloBase.Meta):
        db_table = "bloqueo_horario"
        verbose_name = "Bloqueo de horario"
        verbose_name_plural = "Bloqueos de horario"
        ordering = ["-fecha_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fecha_fin__gt=models.F("fecha_inicio")),
                name="bloqueo_rango_valido",
            )
        ]
        indexes = [models.Index(fields=["doctor", "fecha_inicio", "fecha_fin"], name="idx_bloqueo_doctor_rango")]

    def __str__(self):
        return f"{self.doctor} bloqueado {self.fecha_inicio:%d/%m/%Y %H:%M} - {self.fecha_fin:%d/%m/%Y %H:%M}"
