from datetime import date, timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDate, TruncMonth

from apps.citas.models import Cita, EstadoCita
from apps.doctores.models import DisponibilidadHoraria, DoctorPerfil
from apps.doctores.services import slots_disponibles
from apps.pacientes.models import PacientePerfil


def _citas_del_rango(desde: date, hasta: date):
    return Cita.objects.filter(fecha_hora_inicio__date__gte=desde, fecha_hora_inicio__date__lte=hasta)


def ocupacion_por_doctor(desde: date, hasta: date) -> list[dict]:
    citas = _citas_del_rango(desde, hasta)
    resultado = []

    for doctor in DoctorPerfil.objects.select_related("usuario", "especialidad").filter(activo=True):
        del_doctor = citas.filter(doctor=doctor)
        agendadas = del_doctor.exclude(estado=EstadoCita.CANCELADA).count()

        minutos_disponibles = 0
        for bloque in DisponibilidadHoraria.objects.filter(doctor=doctor, activo=True):
            duracion_bloque = (
                bloque.hora_fin.hour * 60 + bloque.hora_fin.minute
            ) - (bloque.hora_inicio.hour * 60 + bloque.hora_inicio.minute)
            semanas = ((hasta - desde).days + 1) / 7
            minutos_disponibles += duracion_bloque * semanas

        capacidad = int(minutos_disponibles // doctor.duracion_consulta_default) if minutos_disponibles else 0
        ocupacion = round(agendadas / capacidad * 100, 1) if capacidad else 0.0

        resultado.append(
            {
                "doctor_id": doctor.id,
                "doctor": doctor.usuario.nombre_completo,
                "especialidad": doctor.especialidad.nombre,
                "capacidad_estimada": capacidad,
                "citas_agendadas": agendadas,
                "completadas": del_doctor.filter(estado=EstadoCita.COMPLETADA).count(),
                "canceladas": del_doctor.filter(estado=EstadoCita.CANCELADA).count(),
                "no_asistio": del_doctor.filter(estado=EstadoCita.NO_ASISTIO).count(),
                "ocupacion_porcentaje": min(ocupacion, 100.0),
            }
        )

    return sorted(resultado, key=lambda fila: fila["ocupacion_porcentaje"], reverse=True)


def tasa_no_asistencia(desde: date, hasta: date) -> dict:
    citas = _citas_del_rango(desde, hasta)
    finalizadas = citas.filter(estado__in=[EstadoCita.COMPLETADA, EstadoCita.NO_ASISTIO]).count()
    no_asistio = citas.filter(estado=EstadoCita.NO_ASISTIO).count()
    canceladas = citas.filter(estado=EstadoCita.CANCELADA).count()
    total = citas.count()

    return {
        "total_citas": total,
        "finalizadas": finalizadas,
        "no_asistio": no_asistio,
        "canceladas": canceladas,
        "tasa_no_asistencia": round(no_asistio / finalizadas * 100, 1) if finalizadas else 0.0,
        "tasa_cancelacion": round(canceladas / total * 100, 1) if total else 0.0,
        "por_especialidad": list(
            citas.values("doctor__especialidad__nombre")
            .annotate(
                total=Count("id"),
                no_asistio=Count("id", filter=Q(estado=EstadoCita.NO_ASISTIO)),
            )
            .order_by("-total")
        ),
    }


def citas_por_dia(desde: date, hasta: date) -> list[dict]:
    return list(
        _citas_del_rango(desde, hasta)
        .annotate(dia=TruncDate("fecha_hora_inicio"))
        .values("dia")
        .annotate(
            total=Count("id"),
            completadas=Count("id", filter=Q(estado=EstadoCita.COMPLETADA)),
            canceladas=Count("id", filter=Q(estado=EstadoCita.CANCELADA)),
        )
        .order_by("dia")
    )


def demanda_por_especialidad(desde: date, hasta: date) -> list[dict]:
    return list(
        _citas_del_rango(desde, hasta)
        .exclude(estado=EstadoCita.CANCELADA)
        .values("doctor__especialidad__nombre")
        .annotate(total=Count("id"), pacientes_unicos=Count("paciente", distinct=True))
        .order_by("-total")
    )


def disponibilidad_proximos_dias(dias: int = 7) -> list[dict]:
    hoy = date.today()
    resultado = []

    for doctor in DoctorPerfil.objects.select_related("usuario", "especialidad").filter(activo=True):
        libres = sum(len(slots_disponibles(doctor, hoy + timedelta(days=offset))) for offset in range(dias))
        resultado.append(
            {
                "doctor_id": doctor.id,
                "doctor": doctor.usuario.nombre_completo,
                "especialidad": doctor.especialidad.nombre,
                "slots_libres": libres,
                "duracion_consulta": doctor.duracion_consulta_default,
            }
        )

    return sorted(resultado, key=lambda fila: fila["slots_libres"], reverse=True)


def indicadores_generales(desde: date, hasta: date) -> dict:
    citas = _citas_del_rango(desde, hasta)
    anticipacion = (
        citas.exclude(estado=EstadoCita.CANCELADA)
        .filter(fecha_hora_inicio__gt=F("created_at"))
        .annotate(
            anticipacion=ExpressionWrapper(F("fecha_hora_inicio") - F("created_at"), output_field=DurationField())
        )
        .aggregate(promedio=Avg("anticipacion"))["promedio"]
    )

    return {
        "rango": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "total_citas": citas.count(),
        "total_pacientes": PacientePerfil.objects.count(),
        "total_doctores": DoctorPerfil.objects.filter(activo=True).count(),
        "pacientes_atendidos": citas.filter(estado=EstadoCita.COMPLETADA).values("paciente").distinct().count(),
        "anticipacion_promedio_horas": round(anticipacion.total_seconds() / 3600, 1) if anticipacion else 0.0,
        "tendencia_mensual": list(
            citas.annotate(mes=TruncMonth("fecha_hora_inicio"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        ),
    }
