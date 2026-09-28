from datetime import date, datetime, timedelta

from django.utils import timezone

from apps.core.utils import combinar_fecha_hora, generar_slots, rangos_se_solapan

from .models import BloqueoHorario, DisponibilidadHoraria, DoctorPerfil

DIAS_MAXIMOS_CONSULTA = 90


def slots_disponibles(doctor: DoctorPerfil, dia: date, duracion_minutos: int = None) -> list[dict]:
    from apps.citas.models import Cita, EstadoCita

    duracion = duracion_minutos or doctor.duracion_consulta_default
    bloques = DisponibilidadHoraria.objects.filter(doctor=doctor, dia_semana=dia.weekday(), activo=True)
    if not bloques.exists():
        return []

    inicio_dia = combinar_fecha_hora(dia, datetime.min.time())
    fin_dia = inicio_dia + timedelta(days=1)

    ocupadas = list(
        Cita.objects.filter(
            doctor=doctor,
            fecha_hora_inicio__lt=fin_dia,
            fecha_hora_fin__gt=inicio_dia,
        )
        .exclude(estado=EstadoCita.CANCELADA)
        .values_list("fecha_hora_inicio", "fecha_hora_fin")
    )

    bloqueos = list(
        BloqueoHorario.objects.filter(
            doctor=doctor,
            fecha_inicio__lt=fin_dia,
            fecha_fin__gt=inicio_dia,
        ).values_list("fecha_inicio", "fecha_fin")
    )

    ahora = timezone.now()
    resultado = []

    for bloque in bloques:
        inicio = combinar_fecha_hora(dia, bloque.hora_inicio)
        fin = combinar_fecha_hora(dia, bloque.hora_fin)

        for slot_inicio, slot_fin in generar_slots(inicio, fin, duracion):
            if slot_inicio <= ahora:
                continue
            if any(rangos_se_solapan(slot_inicio, slot_fin, ini, f) for ini, f in ocupadas):
                continue
            if any(rangos_se_solapan(slot_inicio, slot_fin, ini, f) for ini, f in bloqueos):
                continue
            resultado.append(
                {
                    "inicio": slot_inicio.isoformat(),
                    "fin": slot_fin.isoformat(),
                    "hora": timezone.localtime(slot_inicio).strftime("%H:%M"),
                    "duracion_minutos": duracion,
                }
            )

    return sorted(resultado, key=lambda s: s["inicio"])


def agenda_del_rango(doctor: DoctorPerfil, desde: date, hasta: date) -> list[dict]:
    dias = min((hasta - desde).days + 1, DIAS_MAXIMOS_CONSULTA)
    agenda = []
    for offset in range(max(dias, 0)):
        dia = desde + timedelta(days=offset)
        slots = slots_disponibles(doctor, dia)
        agenda.append(
            {
                "fecha": dia.isoformat(),
                "dia_semana": dia.weekday(),
                "total_slots": len(slots),
                "slots": slots,
            }
        )
    return agenda


def doctor_atiende_en(doctor: DoctorPerfil, inicio: datetime, fin: datetime) -> bool:
    local_inicio = timezone.localtime(inicio)
    local_fin = timezone.localtime(fin)

    if local_inicio.date() != local_fin.date():
        return False

    dentro_de_horario = DisponibilidadHoraria.objects.filter(
        doctor=doctor,
        dia_semana=local_inicio.weekday(),
        activo=True,
        hora_inicio__lte=local_inicio.time(),
        hora_fin__gte=local_fin.time(),
    ).exists()

    if not dentro_de_horario:
        return False

    return not BloqueoHorario.objects.filter(
        doctor=doctor, fecha_inicio__lt=fin, fecha_fin__gt=inicio
    ).exists()
