import pytest


@pytest.mark.django_db
def test_reporte_ocupacion_visible_para_doctor(autenticar, doctor, cita):
    respuesta = autenticar(doctor.usuario).get("/api/reportes/ocupacion/")

    assert respuesta.status_code == 200
    assert respuesta.data["resultados"][0]["doctor_id"] == doctor.id


@pytest.mark.django_db
def test_paciente_no_accede_a_reportes(autenticar, paciente):
    assert autenticar(paciente.usuario).get("/api/reportes/ocupacion/").status_code == 403
    assert autenticar(paciente.usuario).get("/api/reportes/indicadores/").status_code == 403


@pytest.mark.django_db
def test_indicadores_solo_para_admin(autenticar, admin, doctor, cita):
    assert autenticar(doctor.usuario).get("/api/reportes/indicadores/").status_code == 403

    respuesta = autenticar(admin).get("/api/reportes/indicadores/")
    assert respuesta.status_code == 200
    assert respuesta.data["total_doctores"] == 1


@pytest.mark.django_db
def test_disponibilidad_global_lista_slots_libres(autenticar, admin, doctor):
    respuesta = autenticar(admin).get("/api/reportes/disponibilidad/?dias=3")

    assert respuesta.status_code == 200
    assert respuesta.data["resultados"][0]["slots_libres"] > 0
