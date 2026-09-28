from django.db import models

from apps.core.fields import TextoCifradoField
from apps.core.models import ModeloBase
from apps.pacientes.models import PacientePerfil


class TipoSangre(models.TextChoices):
    A_POS = "A+", "A+"
    A_NEG = "A-", "A-"
    B_POS = "B+", "B+"
    B_NEG = "B-", "B-"
    AB_POS = "AB+", "AB+"
    AB_NEG = "AB-", "AB-"
    O_POS = "O+", "O+"
    O_NEG = "O-", "O-"


class TipoArchivo(models.TextChoices):
    EXAMEN = "examen", "Examen de laboratorio"
    IMAGEN = "imagen", "Imagenologia"
    INFORME = "informe", "Informe medico"
    OTRO = "otro", "Otro"


class HistorialMedico(ModeloBase):
    paciente = models.OneToOneField(PacientePerfil, on_delete=models.CASCADE, related_name="historial")
    alergias = TextoCifradoField(blank=True, default="")
    enfermedades_cronicas = TextoCifradoField(blank=True, default="")
    medicamentos_actuales = TextoCifradoField(blank=True, default="")
    antecedentes_familiares = TextoCifradoField(blank=True, default="")
    tipo_sangre = models.CharField(max_length=3, choices=TipoSangre.choices, blank=True)

    class Meta(ModeloBase.Meta):
        db_table = "historiales_medicos"
        verbose_name = "Historial medico"
        verbose_name_plural = "Historiales medicos"

    def __str__(self):
        return f"Historial de {self.paciente}"


class RegistroConsulta(ModeloBase):
    cita = models.OneToOneField("citas.Cita", on_delete=models.PROTECT, related_name="registro_consulta")
    historial = models.ForeignKey(HistorialMedico, on_delete=models.CASCADE, related_name="registros")
    diagnostico = TextoCifradoField()
    tratamiento = TextoCifradoField(blank=True, default="")
    notas = TextoCifradoField(blank=True, default="")

    class Meta(ModeloBase.Meta):
        db_table = "registros_consulta"
        verbose_name = "Registro de consulta"
        verbose_name_plural = "Registros de consulta"
        indexes = [models.Index(fields=["historial", "-created_at"], name="idx_registro_historial")]

    def __str__(self):
        return f"Consulta {self.cita_id}"


class Receta(ModeloBase):
    registro_consulta = models.ForeignKey(RegistroConsulta, on_delete=models.CASCADE, related_name="recetas")
    medicamento = models.CharField(max_length=180)
    dosis = models.CharField(max_length=120)
    frecuencia = models.CharField(max_length=120)
    duracion = models.CharField(max_length=120)
    indicaciones = models.TextField(blank=True)

    class Meta(ModeloBase.Meta):
        db_table = "recetas"
        verbose_name = "Receta"
        verbose_name_plural = "Recetas"

    def __str__(self):
        return f"{self.medicamento} {self.dosis}"


class ArchivoMedico(ModeloBase):
    registro_consulta = models.ForeignKey(RegistroConsulta, on_delete=models.CASCADE, related_name="archivos")
    archivo = models.FileField(upload_to="archivos_medicos/%Y/%m/")
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(max_length=20, choices=TipoArchivo.choices, default=TipoArchivo.OTRO)

    class Meta(ModeloBase.Meta):
        db_table = "archivos_medicos"
        verbose_name = "Archivo medico"
        verbose_name_plural = "Archivos medicos"

    def __str__(self):
        return self.nombre
