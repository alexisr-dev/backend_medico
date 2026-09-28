import threading
from datetime import timedelta

import pytest
from django.db import IntegrityError, connections, transaction

from apps.citas.models import Cita, EstadoCita
from apps.citas.services import crear_cita
from apps.core.exceptions import HorarioNoDisponible


@pytest.mark.django_db(transaction=True)
def test_dos_pacientes_reservan_el_mismo_slot_solo_uno_gana(doctor, paciente, otro_paciente, slot_manana):
    fin = slot_manana + timedelta(minutes=30)
    resultados = []
    barrera = threading.Barrier(2)

    def reservar(perfil_paciente):
        barrera.wait()
        try:
            crear_cita(perfil_paciente, doctor, slot_manana, fin, "Consulta simultanea")
            resultados.append("creada")
        except (HorarioNoDisponible, IntegrityError):
            resultados.append("rechazada")
        finally:
            connections.close_all()

    hilos = [
        threading.Thread(target=reservar, args=(paciente,)),
        threading.Thread(target=reservar, args=(otro_paciente,)),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=20)

    assert resultados.count("creada") == 1
    assert resultados.count("rechazada") == 1
    assert Cita.objects.exclude(estado=EstadoCita.CANCELADA).count() == 1


@pytest.mark.django_db(transaction=True)
def test_la_base_de_datos_rechaza_solapamiento_parcial(doctor, paciente, otro_paciente, slot_manana):
    Cita.objects.create(
        paciente=paciente,
        doctor=doctor,
        fecha_hora_inicio=slot_manana,
        fecha_hora_fin=slot_manana + timedelta(minutes=30),
        motivo_consulta="Primera",
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Cita.objects.create(
                paciente=otro_paciente,
                doctor=doctor,
                fecha_hora_inicio=slot_manana + timedelta(minutes=15),
                fecha_hora_fin=slot_manana + timedelta(minutes=45),
                motivo_consulta="Solapada",
            )


@pytest.mark.django_db
def test_slot_liberado_tras_cancelacion(doctor, paciente, otro_paciente, slot_manana, admin):
    from apps.citas.services import cancelar_cita

    fin = slot_manana + timedelta(minutes=30)
    primera = crear_cita(paciente, doctor, slot_manana, fin, "Primera")

    with pytest.raises(HorarioNoDisponible):
        crear_cita(otro_paciente, doctor, slot_manana, fin, "Segunda")

    cancelar_cita(primera, admin, "Paciente reagenda")
    segunda = crear_cita(otro_paciente, doctor, slot_manana, fin, "Segunda")

    assert segunda.estado == EstadoCita.PENDIENTE
    assert Cita.objects.filter(estado=EstadoCita.CANCELADA).count() == 1


@pytest.mark.django_db
def test_reprograma_con_version_desactualizada_lanza_conflicto(cita, doctor, slot_manana):
    from apps.core.exceptions import ConflictoDeVersion
    from apps.citas.services import reprogramar_cita

    nuevo_inicio = slot_manana + timedelta(hours=2)
    reprogramar_cita(cita, nuevo_inicio, version_esperada=cita.version)

    with pytest.raises(ConflictoDeVersion):
        reprogramar_cita(cita, nuevo_inicio + timedelta(hours=1), version_esperada=0)
