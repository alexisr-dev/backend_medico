import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import CanalRecordatorio, Notificacion, Recordatorio, TipoNotificacion

logger = logging.getLogger(__name__)


def crear_notificacion(usuario, titulo, mensaje, tipo=TipoNotificacion.SISTEMA, url_destino=""):
    return Notificacion.objects.create(
        usuario=usuario, titulo=titulo, mensaje=mensaje, tipo=tipo, url_destino=url_destino
    )


def notificar_cita(cita, tipo: str):
    plantillas = {
        TipoNotificacion.CITA_CREADA: (
            "Nueva cita agendada",
            "Tu cita con {doctor} quedo agendada para el {fecha}.",
            "El paciente {paciente} agendo una cita para el {fecha}.",
        ),
        TipoNotificacion.CITA_CONFIRMADA: (
            "Cita confirmada",
            "Tu cita con {doctor} del {fecha} fue confirmada.",
            "Confirmaste la cita con {paciente} del {fecha}.",
        ),
        TipoNotificacion.CITA_CANCELADA: (
            "Cita cancelada",
            "Tu cita con {doctor} del {fecha} fue cancelada.",
            "La cita con {paciente} del {fecha} fue cancelada.",
        ),
        TipoNotificacion.CITA_REPROGRAMADA: (
            "Cita reprogramada",
            "Tu cita con {doctor} se movio al {fecha}.",
            "La cita con {paciente} se movio al {fecha}.",
        ),
    }

    if tipo not in plantillas:
        return []

    titulo, texto_paciente, texto_doctor = plantillas[tipo]
    contexto = {
        "doctor": cita.doctor.usuario.nombre_completo,
        "paciente": cita.paciente.usuario.nombre_completo,
        "fecha": timezone.localtime(cita.fecha_hora_inicio).strftime("%d/%m/%Y a las %H:%M"),
    }

    return [
        crear_notificacion(
            cita.paciente.usuario, titulo, texto_paciente.format(**contexto), tipo, f"/paciente/citas/{cita.id}"
        ),
        crear_notificacion(
            cita.doctor.usuario, titulo, texto_doctor.format(**contexto), tipo, f"/doctor/agenda/{cita.id}"
        ),
    ]


def programar_recordatorios(cita):
    creados = []
    for horas in settings.HORAS_ANTICIPACION_RECORDATORIO:
        momento = cita.fecha_hora_inicio - timedelta(hours=horas)
        if momento <= timezone.now():
            continue
        recordatorio, creado = Recordatorio.objects.get_or_create(
            cita=cita,
            tipo=CanalRecordatorio.EMAIL,
            fecha_envio_programada=momento,
        )
        if creado:
            creados.append(recordatorio)
    return creados


def cancelar_recordatorios(cita):
    return Recordatorio.objects.filter(cita=cita, enviado=False).delete()[0]


def enviar_recordatorio(recordatorio: Recordatorio) -> bool:
    cita = recordatorio.cita
    fecha = timezone.localtime(cita.fecha_hora_inicio).strftime("%d/%m/%Y a las %H:%M")
    asunto = "Recordatorio de tu consulta medica"
    cuerpo = (
        f"Hola {cita.paciente.usuario.first_name},\n\n"
        f"Te recordamos tu consulta con {cita.doctor.usuario.nombre_completo} "
        f"({cita.doctor.especialidad.nombre}) el {fecha}.\n\n"
        f"Motivo registrado: {cita.motivo_consulta}\n\n"
        "Si no puedes asistir, cancela con al menos "
        f"{settings.HORAS_MINIMAS_CANCELACION} horas de anticipacion."
    )

    try:
        send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [cita.paciente.usuario.email], fail_silently=False)
    except Exception as exc:
        logger.error("Fallo el envio del recordatorio %s: %s", recordatorio.pk, exc)
        recordatorio.error = str(exc)
        recordatorio.save(update_fields=["error", "updated_at"])
        return False

    recordatorio.enviado = True
    recordatorio.enviado_at = timezone.now()
    recordatorio.error = ""
    recordatorio.save(update_fields=["enviado", "enviado_at", "error", "updated_at"])

    crear_notificacion(
        cita.paciente.usuario,
        asunto,
        f"Tu consulta con {cita.doctor.usuario.nombre_completo} es el {fecha}.",
        TipoNotificacion.RECORDATORIO,
        f"/paciente/citas/{cita.id}",
    )
    return True


def procesar_recordatorios_pendientes() -> dict:
    pendientes = Recordatorio.objects.select_related(
        "cita__paciente__usuario", "cita__doctor__usuario", "cita__doctor__especialidad"
    ).filter(enviado=False, fecha_envio_programada__lte=timezone.now())

    enviados = 0
    fallidos = 0
    for recordatorio in pendientes:
        if enviar_recordatorio(recordatorio):
            enviados += 1
        else:
            fallidos += 1

    return {"enviados": enviados, "fallidos": fallidos}
