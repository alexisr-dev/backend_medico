import pytest

from apps.pacientes.models import PacientePerfil
from apps.usuarios.models import RolUsuario, Usuario


@pytest.mark.django_db
def test_registro_de_paciente_crea_perfil_e_historial(api):
    respuesta = api.post(
        "/api/auth/registro/",
        {
            "email": "Nuevo@Correo.CL",
            "first_name": "Camila",
            "last_name": "Vera",
            "telefono": "+56911112222",
            "password": "Clave.Segura1",
            "password_confirmacion": "Clave.Segura1",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    usuario = Usuario.objects.get(email="nuevo@correo.cl")
    assert usuario.rol == RolUsuario.PACIENTE
    perfil = PacientePerfil.objects.get(usuario=usuario)
    assert perfil.historial is not None


@pytest.mark.django_db
def test_email_duplicado_es_rechazado(api, paciente):
    respuesta = api.post(
        "/api/auth/registro/",
        {
            "email": paciente.usuario.email.upper(),
            "first_name": "Otra",
            "last_name": "Persona",
            "password": "Clave.Segura1",
            "password_confirmacion": "Clave.Segura1",
        },
        format="json",
    )

    assert respuesta.status_code == 400


@pytest.mark.django_db
def test_login_devuelve_tokens_y_rol(api, paciente):
    respuesta = api.post(
        "/api/auth/login/", {"email": paciente.usuario.email, "password": "Clave.Segura1"}, format="json"
    )

    assert respuesta.status_code == 200
    assert "access" in respuesta.data
    assert "refresh" in respuesta.data
    assert respuesta.data["usuario"]["rol"] == RolUsuario.PACIENTE
    assert respuesta.data["perfil_id"] == paciente.id


@pytest.mark.django_db
def test_solo_admin_lista_usuarios(autenticar, paciente, admin):
    assert autenticar(paciente.usuario).get("/api/auth/usuarios/").status_code == 403
    assert autenticar(admin).get("/api/auth/usuarios/").status_code == 200


@pytest.mark.django_db
def test_solo_admin_registra_doctores(autenticar, paciente, admin, especialidad):
    payload = {
        "email": "nuevo.doctor@clinica.cl",
        "first_name": "Pedro",
        "last_name": "Lagos",
        "password": "Clave.Segura1",
        "especialidad_id": especialidad.id,
        "numero_licencia": "LIC-9999",
        "duracion_consulta_default": 45,
    }

    assert autenticar(paciente.usuario).post("/api/auth/registro-doctor/", payload, format="json").status_code == 403

    respuesta = autenticar(admin).post("/api/auth/registro-doctor/", payload, format="json")
    assert respuesta.status_code == 201
    assert Usuario.objects.get(email="nuevo.doctor@clinica.cl").rol == RolUsuario.DOCTOR
