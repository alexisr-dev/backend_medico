from datetime import datetime, time, timedelta

from django.utils import timezone


def ip_del_request(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def combinar_fecha_hora(fecha, hora: time) -> datetime:
    ingenuo = datetime.combine(fecha, hora)
    return timezone.make_aware(ingenuo, timezone.get_current_timezone())


def generar_slots(inicio: datetime, fin: datetime, duracion_minutos: int):
    paso = timedelta(minutes=duracion_minutos)
    actual = inicio
    while actual + paso <= fin:
        yield actual, actual + paso
        actual += paso


def rangos_se_solapan(inicio_a, fin_a, inicio_b, fin_b) -> bool:
    return inicio_a < fin_b and fin_a > inicio_b
