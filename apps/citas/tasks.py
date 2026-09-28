import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.notificaciones.services import procesar_recordatorios_pendientes

from .models import Cita, EstadoCita

logger = logging.getLogger(__name__)


@shared_task(name="citas.enviar_recordatorios_pendientes")
def enviar_recordatorios_pendientes():
    resultado = procesar_recordatorios_pendientes()
    logger.info("Recordatorios procesados: %s", resultado)
    return resultado


@shared_task(name="citas.marcar_no_asistidas")
def marcar_no_asistidas(horas_de_gracia: int = 2):
    limite = timezone.now() - timedelta(hours=horas_de_gracia)
    actualizadas = Cita.objects.filter(
        estado__in=[EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA], fecha_hora_fin__lt=limite
    ).update(estado=EstadoCita.NO_ASISTIO)
    logger.info("Citas marcadas como no asistidas: %s", actualizadas)
    return actualizadas
