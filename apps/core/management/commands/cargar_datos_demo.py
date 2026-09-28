import random
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.citas.models import Cita, EstadoCita
from apps.core.utils import combinar_fecha_hora, generar_slots
from apps.doctores.models import BloqueoHorario, DisponibilidadHoraria, DoctorPerfil, Especialidad
from apps.historiales.models import HistorialMedico, Receta, RegistroConsulta
from apps.notificaciones.services import programar_recordatorios
from apps.pacientes.models import Genero, PacientePerfil
from apps.usuarios.models import RolUsuario, Usuario

PASSWORD_DEMO = "Clave.Segura1"

DIAS_HISTORIA = 28
DIAS_FUTURO = 21
CITAS_POR_DOCTOR_DIA = (5, 11)
PACIENTES_ADICIONALES = 34

NOMBRES_EXTRA = [
    "Alonso", "Beatriz", "Cristobal", "Daniela", "Emilio", "Fernanda", "Gonzalo", "Helena",
    "Ignacio", "Josefa", "Karina", "Lucas", "Macarena", "Nicolas", "Olivia", "Pablo",
    "Rocio",
]
APELLIDOS_EXTRA = ["Aravena", "Bustos", "Carrasco", "Donoso", "Escobar", "Farias", "Gallardo", "Henriquez"]

ESPECIALIDADES = [
    ("Medicina General", "Atencion primaria y control preventivo."),
    ("Cardiologia", "Diagnostico y tratamiento de enfermedades cardiovasculares."),
    ("Pediatria", "Atencion medica de ninos y adolescentes."),
    ("Dermatologia", "Enfermedades de la piel, cabello y unas."),
    ("Traumatologia", "Lesiones del sistema musculoesqueletico."),
    ("Ginecologia", "Salud del sistema reproductor femenino."),
]

DOCTORES = [
    ("Laura", "Mendoza", "Medicina General", 30, 25000),
    ("Carlos", "Ibanez", "Cardiologia", 45, 48000),
    ("Sofia", "Nunez", "Pediatria", 30, 32000),
    ("Andres", "Fuentes", "Dermatologia", 30, 40000),
    ("Valentina", "Rios", "Traumatologia", 40, 45000),
    ("Ricardo", "Salas", "Ginecologia", 40, 42000),
]

PACIENTES = [
    ("Martin", "Godoy", date(1988, 3, 12), Genero.MASCULINO),
    ("Camila", "Sepulveda", date(1995, 7, 24), Genero.FEMENINO),
    ("Diego", "Contreras", date(1979, 11, 2), Genero.MASCULINO),
    ("Antonia", "Vargas", date(2001, 5, 18), Genero.FEMENINO),
    ("Felipe", "Moraga", date(1992, 9, 30), Genero.MASCULINO),
    ("Isidora", "Pizarro", date(1985, 1, 8), Genero.FEMENINO),
    ("Tomas", "Herrera", date(1998, 4, 21), Genero.MASCULINO),
    ("Javiera", "Lagos", date(1990, 12, 15), Genero.FEMENINO),
]

MOTIVOS = [
    "Control preventivo anual",
    "Dolor toracico intermitente",
    "Revision de tratamiento en curso",
    "Erupcion cutanea persistente",
    "Dolor lumbar tras esfuerzo",
    "Chequeo ginecologico de rutina",
    "Fiebre y malestar general",
    "Seguimiento post operatorio",
]

DIAGNOSTICOS = [
    ("Hipertension arterial leve", "Dieta hiposodica y control en 30 dias"),
    ("Dermatitis de contacto", "Corticoide topico por 7 dias"),
    ("Lumbago mecanico", "Kinesioterapia y analgesia"),
    ("Faringitis viral", "Hidratacion y reposo relativo"),
    ("Control sano", "Sin indicaciones farmacologicas"),
]

MEDICAMENTOS = [
    ("Paracetamol 500mg", "1 comprimido", "cada 8 horas", "5 dias"),
    ("Ibuprofeno 400mg", "1 comprimido", "cada 12 horas", "7 dias"),
    ("Losartan 50mg", "1 comprimido", "cada 24 horas", "30 dias"),
    ("Cetirizina 10mg", "1 comprimido", "cada 24 horas", "10 dias"),
]

ALERGIAS = ["Penicilina", "Polen y acaros", "Mariscos", "Ninguna conocida", "Aspirina"]
CRONICAS = ["Hipertension", "Diabetes tipo 2", "Asma bronquial", "Ninguna", "Hipotiroidismo"]
TIPOS_SANGRE = ["A+", "O+", "B+", "AB+", "O-", "A-"]


class Command(BaseCommand):
    help = "Carga un set completo de datos de demostracion para el sistema de reservas medicas."

    def add_arguments(self, parser):
        parser.add_argument("--limpiar", action="store_true", help="Elimina los datos existentes antes de cargar.")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(2026)

        if options["limpiar"]:
            self._limpiar()

        especialidades = self._crear_especialidades()
        admin = self._crear_admin()
        doctores = self._crear_doctores(especialidades)
        pacientes = self._crear_pacientes()
        citas = self._crear_citas(doctores, pacientes)
        self._crear_registros(citas)

        self.stdout.write(self.style.SUCCESS("\nDatos de demostracion cargados correctamente."))
        self.stdout.write(f"  Especialidades : {len(especialidades)}")
        self.stdout.write(f"  Doctores       : {len(doctores)}")
        self.stdout.write(f"  Pacientes      : {len(pacientes)}")
        self.stdout.write(f"  Citas          : {len(citas)}")
        self.stdout.write(self.style.WARNING("\nCredenciales de acceso (password comun: " + PASSWORD_DEMO + ")"))
        self.stdout.write(f"  Admin    : {admin.email}")
        self.stdout.write(f"  Doctor   : {doctores[0].usuario.email}")
        self.stdout.write(f"  Paciente : {pacientes[0].usuario.email}")

    def _limpiar(self):
        Receta.objects.all().delete()
        RegistroConsulta.objects.all().delete()
        Cita.objects.all().delete()
        HistorialMedico.objects.all().delete()
        BloqueoHorario.objects.all().delete()
        DisponibilidadHoraria.objects.all().delete()
        DoctorPerfil.objects.all().delete()
        PacientePerfil.objects.all().delete()
        Usuario.objects.filter(is_superuser=False).delete()
        Especialidad.objects.all().delete()
        self.stdout.write(self.style.WARNING("Datos previos eliminados."))

    def _crear_especialidades(self):
        registros = {}
        for nombre, descripcion in ESPECIALIDADES:
            especialidad, _ = Especialidad.objects.get_or_create(
                nombre=nombre, defaults={"descripcion": descripcion}
            )
            registros[nombre] = especialidad
        return registros

    def _crear_admin(self):
        admin = Usuario.objects.filter(email="admin@clinicasalud.cl").first()
        if admin is None:
            admin = Usuario.objects.create_superuser(
                email="admin@clinicasalud.cl",
                password=PASSWORD_DEMO,
                first_name="Elena",
                last_name="Bravo",
                telefono="+56 9 5555 0001",
            )
        return admin

    def _crear_doctores(self, especialidades):
        perfiles = []
        for indice, (nombre, apellido, especialidad, duracion, tarifa) in enumerate(DOCTORES, start=1):
            email = f"{nombre.lower()}.{apellido.lower()}@clinicasalud.cl"
            usuario = Usuario.objects.filter(email=email).first()
            if usuario is None:
                usuario = Usuario.objects.create_user(
                    email=email,
                    password=PASSWORD_DEMO,
                    first_name=nombre,
                    last_name=apellido,
                    telefono=f"+56 9 5555 1{indice:03d}",
                    rol=RolUsuario.DOCTOR,
                    mfa_habilitado=True,
                )

            perfil, creado = DoctorPerfil.objects.get_or_create(
                usuario=usuario,
                defaults={
                    "especialidad": especialidades[especialidad],
                    "numero_licencia": f"LIC-{2000 + indice}",
                    "duracion_consulta_default": duracion,
                    "tarifa_consulta": tarifa,
                    "biografia": (
                        f"Especialista en {especialidad.lower()} con mas de {8 + indice} anos de experiencia "
                        "clinica y docencia universitaria."
                    ),
                },
            )

            if creado:
                self._crear_disponibilidad(perfil, indice)

            perfiles.append(perfil)

        self._crear_bloqueos(perfiles)
        return perfiles

    def _crear_disponibilidad(self, doctor, indice):
        turno_manana = (time(8, 30), time(13, 0))
        turno_tarde = (time(14, 30), time(19, 0))

        for dia in range(5):
            DisponibilidadHoraria.objects.create(
                doctor=doctor, dia_semana=dia, hora_inicio=turno_manana[0], hora_fin=turno_manana[1]
            )
            if (dia + indice) % 3 != 0:
                DisponibilidadHoraria.objects.create(
                    doctor=doctor, dia_semana=dia, hora_inicio=turno_tarde[0], hora_fin=turno_tarde[1]
                )

        if indice % 2 == 0:
            DisponibilidadHoraria.objects.create(
                doctor=doctor, dia_semana=5, hora_inicio=time(9, 0), hora_fin=time(13, 0)
            )

    def _crear_bloqueos(self, doctores):
        if BloqueoHorario.objects.exists():
            return

        base = timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        BloqueoHorario.objects.create(
            doctor=doctores[1],
            fecha_inicio=base + timedelta(days=9),
            fecha_fin=base + timedelta(days=13),
            motivo="Congreso internacional de cardiologia",
        )
        BloqueoHorario.objects.create(
            doctor=doctores[4],
            fecha_inicio=base + timedelta(days=4, hours=14),
            fecha_fin=base + timedelta(days=4, hours=19),
            motivo="Pabellon quirurgico",
        )

    def _catalogo_pacientes(self):
        catalogo = list(PACIENTES)
        generos = [Genero.MASCULINO, Genero.FEMENINO, Genero.OTRO]

        for indice in range(PACIENTES_ADICIONALES):
            nombre = NOMBRES_EXTRA[indice % len(NOMBRES_EXTRA)]
            apellido = APELLIDOS_EXTRA[(indice // len(NOMBRES_EXTRA) + indice) % len(APELLIDOS_EXTRA)]
            nacimiento = date(1960 + (indice * 7) % 45, (indice % 12) + 1, (indice % 27) + 1)
            catalogo.append((f"{nombre}{indice + 1}", apellido, nacimiento, generos[indice % 3]))

        return catalogo

    def _crear_pacientes(self):
        perfiles = []
        for indice, (nombre, apellido, nacimiento, genero) in enumerate(self._catalogo_pacientes(), start=1):
            email = f"{nombre.lower()}.{apellido.lower()}@correo.cl"
            usuario = Usuario.objects.filter(email=email).first()
            if usuario is None:
                usuario = Usuario.objects.create_user(
                    email=email,
                    password=PASSWORD_DEMO,
                    first_name=nombre,
                    last_name=apellido,
                    telefono=f"+56 9 6666 2{indice:03d}",
                    rol=RolUsuario.PACIENTE,
                )

            perfil, _ = PacientePerfil.objects.get_or_create(
                usuario=usuario,
                defaults={
                    "fecha_nacimiento": nacimiento,
                    "genero": genero,
                    "direccion": f"Av. Los Alerces {1000 + indice * 37}, Santiago",
                    "contacto_emergencia": f"+56 9 7777 3{indice:03d}",
                    "numero_seguro": f"ISP-{80000 + indice * 13}",
                },
            )

            HistorialMedico.objects.get_or_create(
                paciente=perfil,
                defaults={
                    "alergias": random.choice(ALERGIAS),
                    "enfermedades_cronicas": random.choice(CRONICAS),
                    "medicamentos_actuales": random.choice(["Ninguno", "Losartan 50mg", "Levotiroxina 75mcg"]),
                    "antecedentes_familiares": random.choice(
                        ["Padre hipertenso", "Madre diabetica", "Sin antecedentes relevantes"]
                    ),
                    "tipo_sangre": random.choice(TIPOS_SANGRE),
                },
            )
            perfiles.append(perfil)
        return perfiles

    def _slots_del_dia(self, doctor, dia):
        slots = []
        bloques = DisponibilidadHoraria.objects.filter(doctor=doctor, dia_semana=dia.weekday(), activo=True)
        for bloque in bloques:
            inicio = combinar_fecha_hora(dia, bloque.hora_inicio)
            fin = combinar_fecha_hora(dia, bloque.hora_fin)
            slots.extend(generar_slots(inicio, fin, doctor.duracion_consulta_default))
        return slots

    def _crear_citas(self, doctores, pacientes):
        if Cita.objects.exists():
            return list(Cita.objects.all())

        creadas = []
        hoy = timezone.localdate()
        ocupacion_paciente: dict[int, set] = {paciente.id: set() for paciente in pacientes}

        for offset in range(-DIAS_HISTORIA, DIAS_FUTURO + 1):
            dia = hoy + timedelta(days=offset)
            if dia.weekday() > 5:
                continue

            for doctor in doctores:
                disponibles = self._slots_del_dia(doctor, dia)
                if not disponibles:
                    continue

                cantidad = min(len(disponibles), random.randint(*CITAS_POR_DOCTOR_DIA))
                for inicio, fin in random.sample(disponibles, k=cantidad):
                    paciente = self._paciente_libre(pacientes, ocupacion_paciente, inicio)
                    if paciente is None:
                        continue

                    cita = Cita.objects.create(
                        paciente=paciente,
                        doctor=doctor,
                        fecha_hora_inicio=inicio,
                        fecha_hora_fin=fin,
                        motivo_consulta=random.choice(MOTIVOS),
                        estado=self._estado_para(inicio),
                    )
                    ocupacion_paciente[paciente.id].add(inicio)
                    if cita.es_futura:
                        programar_recordatorios(cita)
                    creadas.append(cita)

        return creadas

    def _paciente_libre(self, pacientes, ocupacion, inicio):
        for paciente in random.sample(pacientes, k=len(pacientes)):
            if inicio not in ocupacion[paciente.id]:
                return paciente
        return None

    def _estado_para(self, inicio):
        if inicio > timezone.now():
            return random.choices(
                [EstadoCita.PENDIENTE, EstadoCita.CONFIRMADA, EstadoCita.CANCELADA], weights=[45, 45, 10]
            )[0]
        return random.choices(
            [EstadoCita.COMPLETADA, EstadoCita.NO_ASISTIO, EstadoCita.CANCELADA], weights=[75, 15, 10]
        )[0]

    def _crear_registros(self, citas):
        for cita in citas:
            if cita.estado != EstadoCita.COMPLETADA or RegistroConsulta.objects.filter(cita=cita).exists():
                continue

            diagnostico, tratamiento = random.choice(DIAGNOSTICOS)
            historial, _ = HistorialMedico.objects.get_or_create(paciente=cita.paciente)
            registro = RegistroConsulta.objects.create(
                cita=cita,
                historial=historial,
                diagnostico=diagnostico,
                tratamiento=tratamiento,
                notas="Paciente evoluciona favorablemente. Se indica control segun necesidad.",
            )

            for medicamento, dosis, frecuencia, duracion in random.sample(MEDICAMENTOS, k=random.randint(0, 2)):
                Receta.objects.create(
                    registro_consulta=registro,
                    medicamento=medicamento,
                    dosis=dosis,
                    frecuencia=frecuencia,
                    duracion=duracion,
                    indicaciones="Administrar despues de las comidas.",
                )
