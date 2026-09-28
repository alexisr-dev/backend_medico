import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.core.exceptions import ConflictoDeVersion, ErrorNegocio, HorarioNoDisponible
from apps.doctores.models import DoctorPerfil
from apps.doctores.services import doctor_atiende_en
from apps.pacientes.models import PacientePerfil

from .models import ESTADOS_QUE_OCUPAN_AGENDA, Cita, EstadoCita

logger = logging.getLogger(__name__)


def _validar_solicitud(doctor: DoctorPerfil, inicio: datetime, fin: datetime):
    if inicio <= timezone.now():
        raise ErrorNegocio("No es posible agendar en el pasado.")
    if fin <= inicio:
        raise ErrorNegocio("La hora de termino debe ser posterior a la de inicio.")
    if not doctor.activo:
        raise ErrorNegocio("El doctor no esta recibiendo pacientes actualmente.")
    if not doctor_atiende_en(doctor, inicio, fin):
        raise ErrorNegocio("El doctor no atiende en ese horario o el bloque esta bloqueado.")


def _bloquear_rango(doctor: DoctorPerfil, inicio: datetime, fin: datetime, excluir_id=None):
    queryset = (
        Cita.objects.select_for_update()
        .filter(doctor=doctor, fecha_hora_inicio__lt=fin, fecha_hora_fin__gt=inicio)
        .filter(estado__in=ESTADOS_QUE_OCUPAN_AGENDA)
    )
    if excluir_id:
        queryset = queryset.exclude(pk=excluir_id)
    return list(queryset)


@transaction.atomic
def crear_cita(paciente: PacientePerfil, doctor: DoctorPerfil, inicio: datetime, fin: datetime = None, motivo: str = "") -> Cita:
    fin = fin or inicio + timedelta(minutes=doctor.duracion_consulta_default)
    _validar_solicitud(doctor, inicio, fin)

    if _bloquear_rango(doctor, inicio, fin):
        raise HorarioNoDisponible()

    if Cita.objects.filter(
        paciente=paciente,
        fecha_hora_inicio__lt=fin,
        fecha_hora_fin__gt=inicio,
        estado__in=ESTADOS_QUE_OCUPAN_AGENDA,
    ).exists():
        raise ErrorNegocio("Ya tienes otra cita agendada en ese mismo horario.")

    try:
        with transaction.atomic():
            return Cita.objects.create(
                paciente=paciente,
                doctor=doctor,
                fecha_hora_inicio=inicio,
                fecha_hora_fin=fin,
                motivo_consulta=motivo,
                estado=EstadoCita.PENDIENTE,
            )
    except IntegrityError as exc:
        logger.warning("Colision de reserva doctor=%s inicio=%s: %s", doctor.pk, inicio, exc)
        raise HorarioNoDisponible() from exc


@transaction.atomic
def reprogramar_cita(cita: Cita, inicio: datetime, fin: datetime = None, version_esperada: int = None) -> Cita:
    cita = Cita.objects.select_for_update().select_related("doctor", "paciente").get(pk=cita.pk)

    if version_esperada is not None and cita.version != version_esperada:
        raise ConflictoDeVersion()

    if cita.estado not in (EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA):
        raise ErrorNegocio("Solo se pueden reprogramar citas pendientes o confirmadas.")

    fin = fin or inicio + timedelta(minutes=cita.doctor.duracion_consulta_default)
    _validar_solicitud(cita.doctor, inicio, fin)

    if _bloquear_rango(cita.doctor, inicio, fin, excluir_id=cita.pk):
        raise HorarioNoDisponible()

    try:
        with transaction.atomic():
            actualizadas = Cita.objects.filter(pk=cita.pk, version=cita.version).update(
                fecha_hora_inicio=inicio,
                fecha_hora_fin=fin,
                estado=EstadoCita.PENDIENTE,
                version=F("version") + 1,
                updated_at=timezone.now(),
            )
    except IntegrityError as exc:
        logger.warning("Colision al reprogramar cita=%s: %s", cita.pk, exc)
        raise HorarioNoDisponible() from exc

    if actualizadas == 0:
        raise ConflictoDeVersion()

    cita.refresh_from_db()
    return cita


@transaction.atomic
def cancelar_cita(cita: Cita, usuario, motivo: str = "") -> Cita:
    cita = Cita.objects.select_for_update().get(pk=cita.pk)

    if cita.estado == EstadoCita.CANCELADA:
        raise ErrorNegocio("La cita ya se encuentra cancelada.")
    if cita.estado in (EstadoCita.COMPLETADA, EstadoCita.NO_ASISTIO):
        raise ErrorNegocio("No es posible cancelar una cita ya finalizada.")

    margen = timedelta(hours=settings.HORAS_MINIMAS_CANCELACION)
    if usuario.es_paciente and cita.fecha_hora_inicio - timezone.now() < margen:
        raise ErrorNegocio(
            f"Las cancelaciones requieren al menos {settings.HORAS_MINIMAS_CANCELACION} horas de anticipacion."
        )

    cita.estado = EstadoCita.CANCELADA
    cita.motivo_cancelacion = motivo
    cita.cancelada_por = usuario
    cita.version = F("version") + 1
    cita.save(update_fields=["estado", "motivo_cancelacion", "cancelada_por", "version", "updated_at"])
    cita.refresh_from_db()
    return cita


@transaction.atomic
def cambiar_estado(cita: Cita, nuevo_estado: str, notas: str = None) -> Cita:
    cita = Cita.objects.select_for_update().get(pk=cita.pk)

    transiciones = {
        EstadoCita.PENDIENTE: {EstadoCita.CONFIRMADA, EstadoCita.CANCELADA},
        EstadoCita.CONFIRMADA: {EstadoCita.COMPLETADA, EstadoCita.NO_ASISTIO, EstadoCita.CANCELADA},
        EstadoCita.CANCELADA: set(),
        EstadoCita.COMPLETADA: set(),
        EstadoCita.NO_ASISTIO: set(),
    }

    if nuevo_estado not in transiciones[cita.estado]:
        raise ErrorNegocio(f"No se permite pasar de '{cita.estado}' a '{nuevo_estado}'.")

    if nuevo_estado in (EstadoCita.COMPLETADA, EstadoCita.NO_ASISTIO) and cita.fecha_hora_inicio > timezone.now():
        raise ErrorNegocio("No es posible cerrar una cita que aun no ha comenzado.")

    campos = ["estado", "version", "updated_at"]
    cita.estado = nuevo_estado
    cita.version = F("version") + 1
    if notas is not None:
        cita.notas_doctor = notas
        campos.append("notas_doctor")

    cita.save(update_fields=campos)
    cita.refresh_from_db()
    return cita


def citas_visibles_para(usuario):
    base = Cita.objects.select_related(
        "paciente__usuario", "doctor__usuario", "doctor__especialidad", "cancelada_por"
    )
    if usuario.es_admin:
        return base
    if usuario.es_doctor:
        return base.filter(doctor__usuario=usuario)
    return base.filter(paciente__usuario=usuario)


def puede_ver_historial(usuario, paciente: PacientePerfil) -> bool:
    if usuario.es_admin:
        return True
    if usuario.es_paciente:
        return paciente.usuario_id == usuario.id
    if usuario.es_doctor:
        return Cita.objects.filter(
            doctor__usuario=usuario,
            paciente=paciente,
        ).filter(~Q(estado=EstadoCita.CANCELADA)).exists()
    return False
