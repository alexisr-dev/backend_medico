from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.notificaciones.models import TipoNotificacion
from apps.notificaciones.services import cancelar_recordatorios, notificar_cita, programar_recordatorios

from .models import Cita, EstadoCita

MAPA_ESTADO_NOTIFICACION = {
    EstadoCita.CONFIRMADA: TipoNotificacion.CITA_CONFIRMADA,
    EstadoCita.CANCELADA: TipoNotificacion.CITA_CANCELADA,
}


@receiver(pre_save, sender=Cita)
def registrar_cambios(sender, instance, **kwargs):
    if instance._state.adding:
        instance._estado_previo = None
        instance._inicio_previo = None
        return

    previo = Cita.objects.filter(pk=instance.pk).values("estado", "fecha_hora_inicio").first()
    instance._estado_previo = previo["estado"] if previo else None
    instance._inicio_previo = previo["fecha_hora_inicio"] if previo else None


@receiver(post_save, sender=Cita)
def propagar_efectos(sender, instance, created, **kwargs):
    if created:
        notificar_cita(instance, TipoNotificacion.CITA_CREADA)
        programar_recordatorios(instance)
        return

    estado_previo = getattr(instance, "_estado_previo", None)
    inicio_previo = getattr(instance, "_inicio_previo", None)

    if estado_previo is not None and estado_previo != instance.estado:
        tipo = MAPA_ESTADO_NOTIFICACION.get(instance.estado)
        if tipo:
            notificar_cita(instance, tipo)
        if instance.estado == EstadoCita.CANCELADA:
            cancelar_recordatorios(instance)

    if inicio_previo is not None and inicio_previo != instance.fecha_hora_inicio:
        notificar_cita(instance, TipoNotificacion.CITA_REPROGRAMADA)
        cancelar_recordatorios(instance)
        programar_recordatorios(instance)
