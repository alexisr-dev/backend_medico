from datetime import time, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.citas.models import Cita, EstadoCita
from apps.doctores.models import DisponibilidadHoraria, DoctorPerfil, Especialidad
from apps.historiales.models import HistorialMedico
from apps.pacientes.models import PacientePerfil
from apps.usuarios.models import RolUsuario, Usuario


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def especialidad(db):
    return Especialidad.objects.create(nombre="Medicina General", descripcion="Atencion primaria")


@pytest.fixture
def admin(db):
    return Usuario.objects.create_user(
        email="admin@clinica.cl", password="Clave.Segura1", first_name="Ana", last_name="Torres", rol=RolUsuario.ADMIN
    )


@pytest.fixture
def doctor(db, especialidad):
    usuario = Usuario.objects.create_user(
        email="doctor@clinica.cl", password="Clave.Segura1", first_name="Luis", last_name="Rojas", rol=RolUsuario.DOCTOR
    )
    perfil = DoctorPerfil.objects.create(
        usuario=usuario, especialidad=especialidad, numero_licencia="LIC-0001", duracion_consulta_default=30
    )
    for dia in range(7):
        DisponibilidadHoraria.objects.create(
            doctor=perfil, dia_semana=dia, hora_inicio=time(8, 0), hora_fin=time(20, 0)
        )
    return perfil


@pytest.fixture
def paciente(db):
    usuario = Usuario.objects.create_user(
        email="paciente@correo.cl", password="Clave.Segura1", first_name="Maria", last_name="Diaz"
    )
    perfil = PacientePerfil.objects.create(usuario=usuario)
    HistorialMedico.objects.create(paciente=perfil)
    return perfil


@pytest.fixture
def otro_paciente(db):
    usuario = Usuario.objects.create_user(
        email="paciente2@correo.cl", password="Clave.Segura1", first_name="Jorge", last_name="Silva"
    )
    perfil = PacientePerfil.objects.create(usuario=usuario)
    HistorialMedico.objects.create(paciente=perfil)
    return perfil


@pytest.fixture
def slot_manana():
    referencia = timezone.localtime(timezone.now()) + timedelta(days=1)
    return referencia.replace(hour=10, minute=0, second=0, microsecond=0)


@pytest.fixture
def cita(db, paciente, doctor, slot_manana):
    return Cita.objects.create(
        paciente=paciente,
        doctor=doctor,
        fecha_hora_inicio=slot_manana,
        fecha_hora_fin=slot_manana + timedelta(minutes=30),
        motivo_consulta="Control anual",
        estado=EstadoCita.PENDIENTE,
    )


@pytest.fixture
def autenticar(api):
    def _autenticar(usuario):
        api.force_authenticate(user=usuario)
        return api

    return _autenticar
