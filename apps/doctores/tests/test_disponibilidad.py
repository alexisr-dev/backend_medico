from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from apps.doctores.models import BloqueoHorario
from apps.doctores.services import doctor_atiende_en, slots_disponibles


@pytest.mark.django_db
def test_genera_slots_segun_duracion_de_consulta(doctor, slot_manana):
    slots = slots_disponibles(doctor, slot_manana.date())

    assert len(slots) == 24
    assert slots[0]["duracion_minutos"] == 30


@pytest.mark.django_db
def test_bloqueo_elimina_los_slots_del_rango(doctor, slot_manana):
    BloqueoHorario.objects.create(
        doctor=doctor,
        fecha_inicio=slot_manana,
        fecha_fin=slot_manana + timedelta(hours=2),
        motivo="Cirugia programada",
    )

    horas = [slot["hora"] for slot in slots_disponibles(doctor, slot_manana.date())]

    assert "10:00" not in horas
    assert "11:30" not in horas
    assert "12:00" in horas


@pytest.mark.django_db
def test_no_devuelve_slots_pasados(doctor):
    ahora = timezone.now()
    slots = slots_disponibles(doctor, timezone.localdate())

    assert all(datetime.fromisoformat(slot["inicio"]) > ahora for slot in slots)


@pytest.mark.django_db
def test_doctor_no_atiende_fuera_de_su_horario(doctor, slot_manana):
    fuera = slot_manana.replace(hour=23, minute=0)

    assert doctor_atiende_en(doctor, slot_manana, slot_manana + timedelta(minutes=30))
    assert not doctor_atiende_en(doctor, fuera, fuera + timedelta(minutes=30))
