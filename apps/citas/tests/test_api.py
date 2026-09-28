from datetime import timedelta

import pytest
from django.utils import timezone

from apps.citas.models import Cita, EstadoCita


@pytest.mark.django_db
def test_paciente_agenda_una_cita(autenticar, paciente, doctor, slot_manana):
    api = autenticar(paciente.usuario)
    respuesta = api.post(
        "/api/citas/",
        {
            "doctor": doctor.id,
            "fecha_hora_inicio": slot_manana.isoformat(),
            "motivo_consulta": "Dolor de cabeza persistente",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.data["estado"] == EstadoCita.PENDIENTE
    assert respuesta.data["duracion_minutos"] == 30


@pytest.mark.django_db
def test_slot_ocupado_devuelve_409(autenticar, paciente, otro_paciente, doctor, slot_manana):
    autenticar(paciente.usuario).post(
        "/api/citas/",
        {"doctor": doctor.id, "fecha_hora_inicio": slot_manana.isoformat(), "motivo_consulta": "Primera"},
        format="json",
    )

    api = autenticar(otro_paciente.usuario)
    respuesta = api.post(
        "/api/citas/",
        {"doctor": doctor.id, "fecha_hora_inicio": slot_manana.isoformat(), "motivo_consulta": "Segunda"},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.data["codigo"] == "horario_no_disponible"


@pytest.mark.django_db
def test_no_se_puede_agendar_en_el_pasado(autenticar, paciente, doctor):
    api = autenticar(paciente.usuario)
    ayer = timezone.now() - timedelta(days=1)
    respuesta = api.post(
        "/api/citas/",
        {"doctor": doctor.id, "fecha_hora_inicio": ayer.isoformat(), "motivo_consulta": "Tarde"},
        format="json",
    )

    assert respuesta.status_code == 400


@pytest.mark.django_db
def test_paciente_solo_ve_sus_citas(autenticar, cita, otro_paciente, doctor, slot_manana):
    Cita.objects.create(
        paciente=otro_paciente,
        doctor=doctor,
        fecha_hora_inicio=slot_manana + timedelta(hours=3),
        fecha_hora_fin=slot_manana + timedelta(hours=3, minutes=30),
        motivo_consulta="Ajena",
    )

    respuesta = autenticar(cita.paciente.usuario).get("/api/citas/")

    assert respuesta.status_code == 200
    assert respuesta.data["total"] == 1


@pytest.mark.django_db
def test_doctor_confirma_y_completa_la_cita(autenticar, cita):
    api = autenticar(cita.doctor.usuario)

    confirmada = api.post(f"/api/citas/{cita.id}/estado/", {"estado": EstadoCita.CONFIRMADA}, format="json")
    assert confirmada.status_code == 200
    assert confirmada.data["estado"] == EstadoCita.CONFIRMADA

    Cita.objects.filter(pk=cita.pk).update(
        fecha_hora_inicio=timezone.now() - timedelta(hours=2),
        fecha_hora_fin=timezone.now() - timedelta(hours=1),
    )

    completada = api.post(
        f"/api/citas/{cita.id}/estado/",
        {"estado": EstadoCita.COMPLETADA, "notas_doctor": "Paciente estable"},
        format="json",
    )
    assert completada.status_code == 200
    assert completada.data["notas_doctor"] == "Paciente estable"


@pytest.mark.django_db
def test_paciente_no_puede_cerrar_cita_ajena(autenticar, cita):
    respuesta = autenticar(cita.paciente.usuario).post(
        f"/api/citas/{cita.id}/estado/", {"estado": EstadoCita.COMPLETADA}, format="json"
    )
    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_cancelacion_sin_anticipacion_es_rechazada(autenticar, cita):
    Cita.objects.filter(pk=cita.pk).update(
        fecha_hora_inicio=timezone.now() + timedelta(minutes=30),
        fecha_hora_fin=timezone.now() + timedelta(minutes=60),
    )

    respuesta = autenticar(cita.paciente.usuario).post(
        f"/api/citas/{cita.id}/cancelar/", {"motivo_cancelacion": "Imprevisto"}, format="json"
    )

    assert respuesta.status_code == 400


@pytest.mark.django_db
def test_disponibilidad_excluye_slots_ocupados(autenticar, cita, doctor, slot_manana):
    api = autenticar(cita.paciente.usuario)
    respuesta = api.get(f"/api/doctores/{doctor.id}/disponibilidad/?fecha={slot_manana.date().isoformat()}")

    assert respuesta.status_code == 200
    horas = [slot["hora"] for slot in respuesta.data["slots"]]
    assert slot_manana.strftime("%H:%M") not in horas


@pytest.mark.django_db
def test_crear_cita_genera_notificaciones_y_recordatorios(autenticar, paciente, doctor, slot_manana):
    from apps.notificaciones.models import Notificacion, Recordatorio

    autenticar(paciente.usuario).post(
        "/api/citas/",
        {"doctor": doctor.id, "fecha_hora_inicio": slot_manana.isoformat(), "motivo_consulta": "Control"},
        format="json",
    )

    assert Notificacion.objects.filter(usuario=paciente.usuario).exists()
    assert Notificacion.objects.filter(usuario=doctor.usuario).exists()
    assert Recordatorio.objects.count() >= 1
