"""
Tests de eventos, credenciales y asistencia (Etapa 7).

El foco está en CU-EV9. Es la única operación del sistema que ocurre bajo
concurrencia real —varias personas del staff escaneando a la vez en la puerta—
y la que MASTER §20.5 y §20.6 señalan como incompleta en la Fase 1.
"""

import datetime
import threading

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.academic.services import create_pao
from apps.accounts.models import Student
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.services.clubs import create_club
from apps.clubs.services.memberships import create_membership
from apps.dynamicforms.models import Form
from apps.dynamicforms.services import create_form, update_form
from apps.events import selectors
from apps.events.models import (
    Event,
    EventAttendance,
    EventRegistration,
    EventStaff,
)
from apps.events.qr import issue_qr_token, read_qr_token
from apps.events.services.attendance import register_scan
from apps.events.services.events import (
    can_register,
    create_event,
    delete_event,
    set_event_staff,
)
from apps.events.services.registration import (
    expire_qr_tokens,
    mark_no_shows,
    register_for_event,
)
from core.exceptions import (
    BusinessRuleViolation,
    PermissionDeniedError,
    StateTransitionError,
)

EVENT_SCHEMA = [
    {
        "field_id": "f1",
        "label": "Nivel",
        "type": "radio",
        "required": True,
        "order": 1,
        "options": ["Principiante", "Intermedio", "Avanzado"],
    }
]


def build_scenario(prefix=""):
    """
    Escenario compartido: un club activo, un evento en curso y su formulario.

    Se define como función y no en un ``setUp`` porque lo usan tanto los tests
    normales como el de concurrencia, que necesita ``TransactionTestCase``.
    """
    create_pao(
        pao_period="2026-I",
        start_date=datetime.date(2026, 5, 1),
        end_date=datetime.date(2026, 9, 15),
        activate=True,
    )
    faculty, _ = Faculty.objects.get_or_create(
        code="FIEC", defaults={"name": "Facultad de Ingeniería en Electricidad"}
    )
    area, _ = InterestArea.objects.get_or_create(name="Tecnología")

    leader = Student.objects.create_user(
        enrollment=f"{prefix}201899001",
        email=f"{prefix}dponce@espol.edu.ec",
        password="clave-de-prueba",
        first_name="Diego",
        last_name="Ponce",
        is_verified=True,
    )
    club = create_club(
        name="Club de Software Libre KOKOA",
        acronym="KOKOA",
        description="Software libre.",
        location="FIEC 11D",
        leader_enrollment=leader.enrollment,
        faculty=faculty,
        interest_area_ids=[area.id],
    )
    form = create_form(
        club_id=club.pk,
        form_type=Form.FormType.EVENT,
        title="Registro - Taller de Git",
        fields=EVENT_SCHEMA,
    )

    # El evento está ocurriendo ahora, para que la ventana de escaneo esté
    # abierta sin tener que manipular el reloj en cada test.
    now = timezone.localtime()
    event = create_event(
        club_id=club.pk,
        event_name="CLI - Comandos Básicos Parte #1",
        mode=Event.Mode.ONLINE,
        planned_date=now.date(),
        planned_hour=now.time().replace(microsecond=0),
        end_datetime=now + datetime.timedelta(hours=2),
        planned_place="Aula virtual",
        registration_form_id=form.pk,
    )
    return {"leader": leader, "club": club, "form": form, "event": event}


class EventTestCase(TestCase):
    def setUp(self):
        scenario = build_scenario()
        self.leader = scenario["leader"]
        self.club = scenario["club"]
        self.form = scenario["form"]
        self.event = scenario["event"]

        self.maria = self.make_student("202055789", "María", "Cevallos")
        create_membership(student=self.maria, club=self.club)
        self.kevin = self.make_student("202311346", "Kevin", "Maldonado")

    def make_student(self, enrollment, first_name, last_name):
        return Student.objects.create_user(
            enrollment=enrollment,
            email=f"{enrollment.lower()}@espol.edu.ec",
            password="clave-de-prueba",
            first_name=first_name,
            last_name=last_name,
            is_verified=True,
        )

    def register(self, student=None):
        return register_for_event(
            student=student or self.kevin,
            event_id=self.event.pk,
            responses={"f1": "Intermedio"},
        )

    def make_staff(self, student=None):
        student = student or self.maria
        set_event_staff(
            event_id=self.event.pk,
            student_ids=[student.pk],
            assigned_by=self.leader,
        )
        return student


class EventCreationTests(EventTestCase):
    def test_start_datetime_se_deriva_de_fecha_y_hora(self):
        self.assertEqual(
            timezone.localtime(self.event.start_datetime).date(),
            self.event.planned_date,
        )

    def test_el_fin_debe_ser_posterior_al_inicio(self):
        with self.assertRaises(Exception):
            create_event(
                club_id=self.club.pk,
                event_name="Inválido",
                mode=Event.Mode.ONLINE,
                planned_date=datetime.date(2026, 6, 1),
                planned_hour=datetime.time(14, 0),
                end_datetime=timezone.make_aware(
                    datetime.datetime(2026, 6, 1, 10, 0)
                ),
                planned_place="X",
            )

    def test_la_base_rechaza_un_fin_anterior_al_inicio(self):
        """I-14 defendida por CHECK, no solo en Python."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Event.objects.filter(pk=self.event.pk).update(
                    end_datetime=self.event.start_datetime
                    - datetime.timedelta(hours=1)
                )

    def test_la_fecha_limite_no_puede_superar_el_inicio(self):
        with self.assertRaises(Exception):
            create_event(
                club_id=self.club.pk,
                event_name="Límite tardío",
                mode=Event.Mode.ONLINE,
                planned_date=datetime.date(2026, 6, 1),
                planned_hour=datetime.time(14, 0),
                end_datetime=timezone.make_aware(
                    datetime.datetime(2026, 6, 1, 18, 0)
                ),
                planned_place="X",
                registration_deadline=timezone.make_aware(
                    datetime.datetime(2026, 6, 2, 0, 0)
                ),
            )

    def test_el_formulario_debe_ser_del_mismo_club(self):
        otro = create_club(
            name="Otro club",
            acronym="OTRO",
            description="x",
            location="y",
            leader_enrollment="",
            faculty=None,
            interest_area_ids=[InterestArea.objects.first().id],
        )
        with self.assertRaises(BusinessRuleViolation) as ctx:
            create_event(
                club_id=otro.pk,
                event_name="Ajeno",
                mode=Event.Mode.ONLINE,
                planned_date=datetime.date(2026, 6, 1),
                planned_hour=datetime.time(14, 0),
                end_datetime=timezone.make_aware(
                    datetime.datetime(2026, 6, 1, 18, 0)
                ),
                planned_place="X",
                registration_form_id=self.form.pk,
            )
        self.assertEqual(ctx.exception.code, "club_read_only")

    def test_no_se_borra_un_evento_con_inscripciones(self):
        self.register()
        with self.assertRaises(BusinessRuleViolation) as ctx:
            delete_event(event_id=self.event.pk)
        self.assertEqual(ctx.exception.code, "event_has_registrations")


class EventVisibilityTests(EventTestCase):
    """RF-31 — los MembersOnly son visibles; lo que se bloquea es el registro."""

    def setUp(self):
        super().setUp()
        self.event.visibility = Event.Visibility.MEMBERS_ONLY
        self.event.save(update_fields=["visibility"])

    def test_un_no_miembro_ve_el_evento(self):
        visibles = selectors.get_visible_events(self.kevin)
        self.assertIn(self.event.pk, [e.pk for e in visibles])

    def test_pero_no_puede_inscribirse(self):
        verdict = can_register(self.kevin, self.event)
        self.assertFalse(verdict["can_register"])
        self.assertEqual(verdict["code"], "members_only")
        self.assertEqual(verdict["reason"], "Evento exclusivo para miembros.")

    def test_usa_el_mensaje_personalizado_del_lider(self):
        self.event.blocked_message = "Solo para la directiva de KOKOA."
        self.event.save(update_fields=["blocked_message"])
        self.assertEqual(
            can_register(self.kevin, self.event)["reason"],
            "Solo para la directiva de KOKOA.",
        )

    def test_un_miembro_si_puede(self):
        self.assertTrue(can_register(self.maria, self.event)["can_register"])


class RegistrationTests(EventTestCase):
    def test_inscribirse_emite_una_credencial_activa(self):
        registration = self.register()

        self.assertEqual(registration.qr_status, EventRegistration.QrStatus.ACTIVE)
        self.assertEqual(
            registration.attendance_status,
            EventRegistration.AttendanceStatus.REGISTERED,
        )
        self.assertEqual(read_qr_token(registration.qr_token), registration.pk)

    def test_el_token_no_revela_al_estudiante_ni_al_evento(self):
        """
        RNF-05: ``signing.dumps`` firma pero no cifra, así que el contenido es
        legible. Por eso solo lleva el id de la inscripción.
        """
        registration = self.register()
        payload = read_qr_token(registration.qr_token)

        self.assertEqual(payload, registration.pk)
        self.assertNotIn(str(self.kevin.pk), str(payload))
        self.assertNotIn(str(self.event.pk), str(payload))

    def test_no_se_puede_inscribir_dos_veces(self):
        self.register()
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.register()
        self.assertEqual(ctx.exception.code, "already_registered")
        self.assertEqual(ctx.exception.message, "Ya estás inscrito en este evento.")

    def test_la_base_rechaza_la_inscripcion_duplicada(self):
        self.register()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EventRegistration.objects.create(
                    event=self.event,
                    student=self.kevin,
                    form=self.form,
                    responses=[],
                    qr_token="token-distinto",
                )

    def test_sin_formulario_no_hay_registro_abierto(self):
        self.event.registration_form = None
        self.event.save(update_fields=["registration_form"])

        verdict = can_register(self.kevin, self.event)
        self.assertEqual(verdict["code"], "no_registration_form")
        self.assertEqual(verdict["reason"], "Este evento no tiene registro abierto.")

    def test_la_fecha_limite_cierra_el_registro(self):
        """RF-34."""
        self.event.registration_deadline = timezone.now() - datetime.timedelta(hours=1)
        self.event.save(update_fields=["registration_deadline"])

        verdict = can_register(self.kevin, self.event)
        self.assertEqual(verdict["code"], "registration_closed")

    def test_sin_tope_de_participantes(self):
        """RF-33: expected_participants es solo planificación."""
        self.event.expected_participants = 1
        self.event.save(update_fields=["expected_participants"])

        self.register(self.kevin)
        segunda = self.register(self.maria)
        self.assertIsNotNone(segunda.pk)

    def test_las_respuestas_se_validan_contra_el_esquema(self):
        with self.assertRaises(Exception):
            register_for_event(
                student=self.kevin,
                event_id=self.event.pk,
                responses={"f1": "Experto"},
            )
        self.assertEqual(EventRegistration.objects.count(), 0)


class StaffAssignmentTests(EventTestCase):
    def test_solo_miembros_activos_pueden_ser_staff(self):
        """Invariante I-20."""
        with self.assertRaises(BusinessRuleViolation) as ctx:
            set_event_staff(event_id=self.event.pk, student_ids=[self.kevin.pk])
        self.assertEqual(ctx.exception.code, "staff_must_be_active_member")

    def test_la_asignacion_reemplaza_la_anterior(self):
        andres = self.make_student("201977882", "Andrés", "Vera")
        create_membership(student=andres, club=self.club)

        set_event_staff(event_id=self.event.pk, student_ids=[self.maria.pk])
        set_event_staff(event_id=self.event.pk, student_ids=[andres.pk])

        asignados = list(
            EventStaff.objects.filter(event=self.event).values_list(
                "student_id", flat=True
            )
        )
        self.assertEqual(asignados, [andres.pk])

    def test_asignar_dos_veces_al_mismo_no_duplica(self):
        set_event_staff(event_id=self.event.pk, student_ids=[self.maria.pk])
        set_event_staff(event_id=self.event.pk, student_ids=[self.maria.pk])
        self.assertEqual(EventStaff.objects.filter(event=self.event).count(), 1)


class ScanChainTests(EventTestCase):
    """
    CU-EV9 — la cadena de guardas, en el orden exacto.

    El orden no es estético: se responde primero lo que le sirve a quien
    escanea, con una cola esperando.
    """

    def setUp(self):
        super().setUp()
        self.registration = self.register()
        self.staff = self.make_staff()

    def scan(self, token=None, staff=None):
        return register_scan(
            qr_token=token if token is not None else self.registration.qr_token,
            staff_student=staff or self.staff,
        )

    def test_escaneo_valido_registra_la_asistencia(self):
        attendance = self.scan()

        self.assertEqual(attendance.student, self.kevin)
        self.assertEqual(attendance.scanned_by_staff, self.staff)
        self.assertEqual(attendance.qr_token_validated, self.registration.qr_token)

        self.registration.refresh_from_db()
        self.assertEqual(self.registration.qr_status, EventRegistration.QrStatus.USED)
        self.assertEqual(
            self.registration.attendance_status,
            EventRegistration.AttendanceStatus.ATTENDED,
        )

    def test_la_asistencia_referencia_su_inscripcion_y_el_token(self):
        """Cierra la divergencia §20.5: la Fase 1 no escribía ninguno de los dos."""
        attendance = self.scan()
        self.assertEqual(attendance.registration, self.registration)
        self.assertTrue(attendance.qr_token_validated)

    def test_la_hora_la_pone_el_servidor(self):
        """RNF-12."""
        antes = timezone.now()
        attendance = self.scan()
        self.assertGreaterEqual(attendance.scanned_at, antes)
        self.assertLessEqual(attendance.scanned_at, timezone.now())

    def test_token_vacio(self):
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.scan(token="")
        self.assertEqual(ctx.exception.message, "Ingresa o escanea un código.")

    def test_token_desconocido(self):
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.scan(token="basura-inventada")
        self.assertEqual(ctx.exception.message, "Credencial no reconocida.")

    def test_un_token_bien_firmado_pero_sin_fila_tampoco_vale(self):
        """
        La firma descarta basura; la autoridad es la base.

        Un token con firma perfecta para una inscripción inexistente no
        autoriza nada.
        """
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.scan(token=issue_qr_token(999999))
        self.assertEqual(ctx.exception.message, "Credencial no reconocida.")

    def test_no_se_reescanea(self):
        """RN-6."""
        self.scan()
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.scan()
        self.assertEqual(
            ctx.exception.message, "Esta credencial ya registró asistencia."
        )
        self.assertEqual(EventAttendance.objects.count(), 1)

    def test_un_qr_expirado_no_sirve(self):
        self.registration.qr_status = EventRegistration.QrStatus.EXPIRED
        self.registration.save(update_fields=["qr_status"])

        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.scan()
        self.assertEqual(ctx.exception.code, "qr_expired")

    def test_quien_no_es_staff_no_escanea(self):
        """RF-35 / divergencia §20.6: en la Fase 1 no se comprobaba."""
        andres = self.make_student("201977882", "Andrés", "Vera")
        create_membership(student=andres, club=self.club)

        with self.assertRaises(PermissionDeniedError) as ctx:
            self.scan(staff=andres)
        self.assertEqual(ctx.exception.code, "not_event_staff")
        self.assertEqual(EventAttendance.objects.count(), 0)

    def test_el_staff_de_otro_evento_tampoco(self):
        """El permiso nace y muere con el evento asignado."""
        otro_evento = create_event(
            club_id=self.club.pk,
            event_name="Otro taller",
            mode=Event.Mode.ONLINE,
            planned_date=timezone.localdate(),
            planned_hour=datetime.time(9, 0),
            end_datetime=timezone.now() + datetime.timedelta(hours=6),
            planned_place="Aula 2",
        )
        andres = self.make_student("201977882", "Andrés", "Vera")
        create_membership(student=andres, club=self.club)
        set_event_staff(event_id=otro_evento.pk, student_ids=[andres.pk])

        with self.assertRaises(PermissionDeniedError):
            self.scan(staff=andres)

    def test_fuera_de_la_ventana_no_se_escanea(self):
        """Decisión D-08."""
        self.event.planned_date = timezone.localdate() + datetime.timedelta(days=30)
        self.event.end_datetime = timezone.now() + datetime.timedelta(days=30, hours=2)
        self.event.save()

        with self.assertRaises(PermissionDeniedError) as ctx:
            self.scan()
        self.assertEqual(ctx.exception.code, "outside_scan_window")

    def test_la_base_rechaza_la_asistencia_duplicada(self):
        """
        RN-6 defendida por UNIQUE, saltándose el servicio.

        Es la única capa que no se puede eludir, y la que sostiene el caso
        concurrente.
        """
        self.scan()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EventAttendance.objects.create(
                    registration=self.registration,
                    event=self.event,
                    student=self.kevin,
                    scanned_at=timezone.now(),
                    qr_token_validated="otro",
                )


class ScheduledProcessTests(EventTestCase):
    def setUp(self):
        super().setUp()
        self.registration = self.register()

    def test_expira_los_qr_de_eventos_terminados(self):
        """RF-37."""
        despues = self.event.end_datetime + datetime.timedelta(minutes=1)
        tocados = expire_qr_tokens(now=despues)

        self.registration.refresh_from_db()
        self.assertEqual(tocados, 1)
        self.assertEqual(self.registration.qr_status, EventRegistration.QrStatus.EXPIRED)

    def test_la_expiracion_es_idempotente(self):
        despues = self.event.end_datetime + datetime.timedelta(minutes=1)
        expire_qr_tokens(now=despues)
        self.assertEqual(expire_qr_tokens(now=despues), 0)

    def test_marca_no_show_a_quien_no_fue_escaneado(self):
        despues = self.event.end_datetime + datetime.timedelta(minutes=1)
        mark_no_shows(now=despues)

        self.registration.refresh_from_db()
        self.assertEqual(
            self.registration.attendance_status,
            EventRegistration.AttendanceStatus.NO_SHOW,
        )

    def test_quien_asistio_no_se_marca_no_show(self):
        self.make_staff()
        register_scan(
            qr_token=self.registration.qr_token, staff_student=self.maria
        )

        despues = self.event.end_datetime + datetime.timedelta(minutes=1)
        mark_no_shows(now=despues)

        self.registration.refresh_from_db()
        self.assertEqual(
            self.registration.attendance_status,
            EventRegistration.AttendanceStatus.ATTENDED,
        )

    def test_los_dos_ejes_de_estado_son_independientes(self):
        """
        §5.4: un QR Expired con asistencia NoShow es un estado normal.

        No son dos formas de decir lo mismo: uno describe la credencial y el
        otro la participación.
        """
        despues = self.event.end_datetime + datetime.timedelta(minutes=1)
        expire_qr_tokens(now=despues)
        mark_no_shows(now=despues)

        self.registration.refresh_from_db()
        self.assertEqual(self.registration.qr_status, EventRegistration.QrStatus.EXPIRED)
        self.assertEqual(
            self.registration.attendance_status,
            EventRegistration.AttendanceStatus.NO_SHOW,
        )


class MetricsTests(EventTestCase):
    def test_inscritos_vs_asistentes(self):
        """RF-38."""
        self.register(self.kevin)
        registro_maria = self.register(self.maria)
        self.make_staff()
        register_scan(qr_token=registro_maria.qr_token, staff_student=self.maria)

        evento = selectors.get_event(self.event.pk)
        self.assertEqual(evento.registered_count, 2)
        self.assertEqual(evento.attended_count, 1)

    def test_resumen_de_asistencia(self):
        self.register(self.kevin)
        resumen = selectors.event_attendance_summary(self.event.pk)
        self.assertEqual(resumen["registered"], 1)
        self.assertEqual(resumen["pending"], 1)
        self.assertEqual(resumen["attended"], 0)


class FormImmutabilityTests(EventTestCase):
    def test_una_inscripcion_bloquea_la_edicion_del_formulario(self):
        """RF-24 con el segundo contador real."""
        self.register()
        with self.assertRaises(StateTransitionError) as ctx:
            update_form(form_id=self.form.pk, title="Ya no")
        self.assertEqual(ctx.exception.code, "form_has_responses")


class ConcurrentScanTests(TransactionTestCase):
    """
    La prueba que justifica el diseño de CU-EV9.

    Dos hilos escanean el **mismo** código a la vez, como pasaría con dos
    personas del staff en dos puertas. Solo una asistencia debe quedar
    registrada, y la otra debe recibir el mensaje de credencial ya usada —no un
    error de integridad crudo ni un 500.

    Necesita ``TransactionTestCase`` porque ``TestCase`` envuelve todo en una
    transacción que nunca se confirma, y entonces los hilos no verían nada de lo
    que hace el otro.
    """

    # Restaura los datos cargados por las migraciones (los catálogos) tras el
    # flush que hace TransactionTestCase, para no dejar sin ellos al resto de
    # la suite.
    serialized_rollback = True

    def test_dos_escaneos_simultaneos_registran_una_sola_asistencia(self):
        scenario = build_scenario()
        club, event = scenario["club"], scenario["event"]

        estudiante = Student.objects.create_user(
            enrollment="202311346",
            email="kmaldon@espol.edu.ec",
            password="clave-de-prueba",
            first_name="Kevin",
            last_name="Maldonado",
            is_verified=True,
        )
        staff = Student.objects.create_user(
            enrollment="202055789",
            email="mcevallos@espol.edu.ec",
            password="clave-de-prueba",
            first_name="María",
            last_name="Cevallos",
            is_verified=True,
        )
        create_membership(student=staff, club=club)
        set_event_staff(event_id=event.pk, student_ids=[staff.pk])

        registration = register_for_event(
            student=estudiante, event_id=event.pk, responses={"f1": "Intermedio"}
        )

        resultados = []
        barrera = threading.Barrier(2)

        def escanear():
            try:
                # Los dos hilos llegan al escaneo a la vez, no uno tras otro.
                barrera.wait(timeout=5)
                register_scan(
                    qr_token=registration.qr_token, staff_student=staff
                )
                resultados.append("registrada")
            except BusinessRuleViolation as exc:
                resultados.append(exc.code)
            except Exception as exc:  # pragma: no cover - diagnóstico
                resultados.append(f"inesperado: {type(exc).__name__}: {exc}")
            finally:
                # Cada hilo abre su propia conexión y debe cerrarla, o el flush
                # final del test se queda bloqueado esperándolas.
                connection.close()

        hilos = [threading.Thread(target=escanear) for _ in range(2)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=15)

        self.assertEqual(
            EventAttendance.objects.filter(
                event=event, student=estudiante
            ).count(),
            1,
            "RN-6 debe impedir dos asistencias para el mismo par evento/estudiante.",
        )
        self.assertEqual(resultados.count("registrada"), 1, resultados)
        self.assertEqual(resultados.count("qr_already_used"), 1, resultados)
