from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.utils import timezone

from apps.core.fields import TextoCifradoField
from apps.core.models import ModeloBaseUUID
from apps.doctores.models import DoctorPerfil
from apps.pacientes.models import PacientePerfil


class EstadoCita(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    CONFIRMADA = "confirmada", "Confirmada"
    CANCELADA = "cancelada", "Cancelada"
    COMPLETADA = "completada", "Completada"
    NO_ASISTIO = "no_asistio", "No asistio"


ESTADOS_QUE_OCUPAN_AGENDA = [
    EstadoCita.PENDIENTE,
    EstadoCita.CONFIRMADA,
    EstadoCita.COMPLETADA,
    EstadoCita.NO_ASISTIO,
]


class RangoCita(models.Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()

    def __init__(self, inicio, fin, **extra):
        super().__init__(inicio, fin, RangeBoundary(), **extra)


class Cita(ModeloBaseUUID):
    paciente = models.ForeignKey(PacientePerfil, on_delete=models.PROTECT, related_name="citas")
    doctor = models.ForeignKey(DoctorPerfil, on_delete=models.PROTECT, related_name="citas")
    fecha_hora_inicio = models.DateTimeField(db_index=True)
    fecha_hora_fin = models.DateTimeField()
    estado = models.CharField(
        max_length=20, choices=EstadoCita.choices, default=EstadoCita.PENDIENTE, db_index=True
    )
    motivo_consulta = models.TextField()
    notas_doctor = TextoCifradoField(blank=True, default="")
    motivo_cancelacion = models.CharField(max_length=255, blank=True)
    cancelada_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.SET_NULL, null=True, blank=True, related_name="citas_canceladas"
    )
    version = models.PositiveIntegerField(default=0)

    class Meta(ModeloBaseUUID.Meta):
        db_table = "citas"
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ["-fecha_hora_inicio"]
        indexes = [
            models.Index(fields=["doctor", "fecha_hora_inicio"], name="idx_citas_doctor_fecha"),
            models.Index(fields=["paciente", "-fecha_hora_inicio"], name="idx_citas_paciente"),
            models.Index(fields=["estado", "fecha_hora_inicio"], name="idx_citas_estado_fecha"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fecha_hora_fin__gt=models.F("fecha_hora_inicio")),
                name="cita_rango_valido",
            ),
            models.UniqueConstraint(
                fields=["doctor", "fecha_hora_inicio"],
                condition=~models.Q(estado=EstadoCita.CANCELADA),
                name="uq_doctor_horario",
            ),
            ExclusionConstraint(
                name="no_solapamiento_citas",
                expressions=[
                    ("doctor", RangeOperators.EQUAL),
                    (RangoCita("fecha_hora_inicio", "fecha_hora_fin"), RangeOperators.OVERLAPS),
                ],
                condition=~models.Q(estado=EstadoCita.CANCELADA),
            ),
        ]

    def __str__(self):
        return f"{self.paciente} con {self.doctor} el {self.fecha_hora_inicio:%d/%m/%Y %H:%M}"

    @property
    def duracion_minutos(self):
        return int((self.fecha_hora_fin - self.fecha_hora_inicio).total_seconds() // 60)

    @property
    def es_futura(self):
        return self.fecha_hora_inicio > timezone.now()

    @property
    def puede_cancelarse(self):
        return self.estado in (EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA) and self.es_futura
