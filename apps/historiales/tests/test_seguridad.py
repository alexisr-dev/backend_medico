from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.auditoria.models import AuditoriaAcceso
from apps.citas.models import Cita, EstadoCita
from apps.historiales.models import HistorialMedico


@pytest.mark.django_db
def test_campos_clinicos_quedan_cifrados_en_la_base(paciente):
    historial = paciente.historial
    historial.alergias = "Penicilina"
    historial.save()

    with connection.cursor() as cursor:
        cursor.execute("SELECT alergias FROM historiales_medicos WHERE id = %s", [historial.id])
        crudo = cursor.fetchone()[0]

    assert crudo.startswith("enc::")
    assert "Penicilina" not in crudo
    assert HistorialMedico.objects.get(pk=historial.pk).alergias == "Penicilina"


@pytest.mark.django_db
def test_paciente_accede_a_su_historial_y_queda_auditado(autenticar, paciente):
    respuesta = autenticar(paciente.usuario).get("/api/historiales/mi-historial/")

    assert respuesta.status_code == 200
    assert AuditoriaAcceso.objects.filter(
        usuario=paciente.usuario, modelo_afectado="HistorialMedico", accion="lectura"
    ).exists()


@pytest.mark.django_db
def test_cada_acceso_genera_un_solo_registro_con_el_objeto(autenticar, paciente):
    autenticar(paciente.usuario).get("/api/historiales/mi-historial/")

    registros = AuditoriaAcceso.objects.filter(usuario=paciente.usuario, modelo_afectado="HistorialMedico")

    assert registros.count() == 1
    assert registros.first().objeto_id == str(paciente.historial.pk)


@pytest.mark.django_db
def test_paciente_no_accede_al_historial_de_otro(autenticar, paciente, otro_paciente):
    respuesta = autenticar(paciente.usuario).get(f"/api/historiales/paciente/{otro_paciente.id}/")
    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_doctor_sin_cita_previa_no_accede_al_historial(autenticar, doctor, paciente):
    respuesta = autenticar(doctor.usuario).get(f"/api/historiales/paciente/{paciente.id}/")
    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_doctor_con_cita_accede_al_historial(autenticar, doctor, paciente, cita):
    respuesta = autenticar(doctor.usuario).get(f"/api/historiales/paciente/{paciente.id}/")
    assert respuesta.status_code == 200
    assert respuesta.data["paciente"] == paciente.id


@pytest.mark.django_db
def test_registro_de_consulta_requiere_cita_completada(autenticar, doctor, cita):
    api = autenticar(doctor.usuario)
    payload = {"cita": str(cita.id), "diagnostico": "Migrana tensional", "tratamiento": "Reposo"}

    assert api.post("/api/historiales/consultas/", payload, format="json").status_code == 400

    Cita.objects.filter(pk=cita.pk).update(
        estado=EstadoCita.COMPLETADA,
        fecha_hora_inicio=timezone.now() - timedelta(hours=2),
        fecha_hora_fin=timezone.now() - timedelta(hours=1),
    )

    respuesta = api.post("/api/historiales/consultas/", payload, format="json")
    assert respuesta.status_code == 201
    assert respuesta.data["diagnostico"] == "Migrana tensional"


@pytest.mark.django_db
def test_solo_admin_consulta_la_auditoria(autenticar, paciente, doctor, admin):
    assert autenticar(paciente.usuario).get("/api/auditoria/").status_code == 403
    assert autenticar(doctor.usuario).get("/api/auditoria/").status_code == 403
    assert autenticar(admin).get("/api/auditoria/").status_code == 200
