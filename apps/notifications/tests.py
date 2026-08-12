"""
Tests de notificaciones y procesos programados (Etapa 10).

**Cuidado al leer estos tests:** las notificaciones nacen de handlers del bus de
eventos, que corren con ``transaction.on_commit``. En un ``TestCase`` normal esos
callbacks nunca se ejecutan, así que todo lo que dependa de ellos va envuelto en
``captureOnCommitCallbacks(execute=True)``. Sin eso, la mitad de esta suite
pasaría en verde sin haber comprobado nada.
"""

import datetime
import io

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.academic.services import create_pao
from apps.accounts.models import Student
from apps.applications.services import (
    approve_application,
    reject_application,
    submit_application,
)
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.services.clubs import create_club
from apps.clubs.services.leadership import revoke_leader
from apps.clubs.services.memberships import (
    create_membership,
    freeze_expired_memberships,
    revoke_membership,
)
from apps.dynamicforms.models import Form
from apps.dynamicforms.services import create_form
from apps.events.models import EventRegistration
from apps.events.services.events import create_event, set_event_staff
from apps.events.services.registration import register_for_event
from apps.notifications.models import Notification
from apps.notifications.services import count_unread, mark_read, notify

MEMBERSHIP_SCHEMA = [
    {
        "field_id": "q1",
        "label": "¿Por qué quieres unirte?",
        "type": "textarea",
        "required": True,
        "order": 1,
    }
]


class NotificationTestCase(TestCase):
    def setUp(self):
        create_pao(
            pao_period="2026-I",
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 9, 15),
            activate=True,
        )
        self.leader = self.make_student("201899001", "Diego", "Ponce")
        self.club = create_club(
            name="Club de Software Libre KOKOA",
            acronym="KOKOA",
            description="Software libre.",
            location="FIEC 11D",
            leader_enrollment="201899001",
            faculty=Faculty.objects.get(code="FIEC"),
            interest_area_ids=[InterestArea.objects.get(name="Tecnología").id],
        )
        self.form = create_form(
            club_id=self.club.pk,
            form_type=Form.FormType.MEMBERSHIP,
            title="Postulación",
            fields=MEMBERSHIP_SCHEMA,
        )
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

    def apply(self, student=None):
        with self.captureOnCommitCallbacks(execute=True):
            return submit_application(
                student=student or self.kevin,
                club_id=self.club.pk,
                responses={"q1": "Me interesa."},
            )


class ApplicationNotificationTests(NotificationTestCase):
    def test_postular_avisa_a_quien_gestiona_la_nomina(self):
        """
        El destinatario no es "el líder": es quien tenga ``manage_members``.

        Si la presidencia delegó ese permiso, el aviso llega a quien lo tiene.
        """
        self.apply()

        aviso = Notification.objects.get(user=self.leader)
        self.assertEqual(aviso.type, Notification.Type.APPLICATION_PENDING)
        self.assertIn("Kevin Maldonado", aviso.message)
        self.assertEqual(aviso.club, self.club)

    def test_aprobar_avisa_al_postulante(self):
        application = self.apply()

        with self.captureOnCommitCallbacks(execute=True):
            approve_application(application_id=application.pk, resolved_by=self.leader)

        aviso = Notification.objects.get(
            user=self.kevin, type=Notification.Type.APPLICATION_APPROVED
        )
        self.assertIn("aprobada", aviso.message)

    def test_el_rechazo_incluye_el_motivo(self):
        """RF-29 permite reenviar de inmediato: sin el motivo, reenviaría igual."""
        application = self.apply()

        with self.captureOnCommitCallbacks(execute=True):
            reject_application(
                application_id=application.pk,
                resolved_by=self.leader,
                feedback="Cupo lleno este PAO.",
            )

        aviso = Notification.objects.get(
            user=self.kevin, type=Notification.Type.APPLICATION_REJECTED
        )
        self.assertIn("Cupo lleno este PAO.", aviso.message)

    def test_la_notificacion_enlaza_al_objeto(self):
        """Decisión D-10: sin la referencia, el usuario tendría que buscarlo."""
        application = self.apply()

        aviso = Notification.objects.get(user=self.leader)
        self.assertEqual(aviso.target_type, "MembershipApplication")
        self.assertEqual(aviso.target_id, application.pk)


class MembershipNotificationTests(NotificationTestCase):
    def test_la_baja_avisa_al_miembro(self):
        maria = self.make_student("202055789", "María", "Cevallos")
        membership = create_membership(student=maria, club=self.club)

        with self.captureOnCommitCallbacks(execute=True):
            revoke_membership(membership_id=membership.pk)

        self.assertTrue(
            Notification.objects.filter(
                user=maria, type=Notification.Type.MEMBERSHIP_REVOKED
            ).exists()
        )

    def test_el_congelamiento_avisa(self):
        maria = self.make_student("202055789", "María", "Cevallos")
        create_membership(student=maria, club=self.club)

        with self.captureOnCommitCallbacks(execute=True):
            freeze_expired_memberships(today=datetime.date(2026, 9, 16))

        self.assertTrue(
            Notification.objects.filter(
                user=maria, type=Notification.Type.MEMBERSHIP_FROZEN
            ).exists()
        )

    def test_revocar_el_liderazgo_avisa_al_lider_saliente(self):
        with self.captureOnCommitCallbacks(execute=True):
            revoke_leader(club_id=self.club.pk)

        self.assertTrue(
            Notification.objects.filter(
                user=self.leader, type=Notification.Type.LEADER_REVOKED
            ).exists()
        )


class EventNotificationTests(NotificationTestCase):
    def setUp(self):
        super().setUp()
        self.event_form = create_form(
            club_id=self.club.pk,
            form_type=Form.FormType.EVENT,
            title="Registro",
            fields=[
                {
                    "field_id": "f1",
                    "label": "Nivel",
                    "type": "radio",
                    "required": True,
                    "options": ["A", "B"],
                }
            ],
        )
        now = timezone.localtime()
        self.event = create_event(
            club_id=self.club.pk,
            event_name="Taller de Git",
            mode="Online",
            planned_date=now.date(),
            planned_hour=now.time().replace(microsecond=0),
            end_datetime=now + datetime.timedelta(hours=2),
            planned_place="Aula virtual",
            registration_form_id=self.event_form.pk,
        )

    def test_inscribirse_avisa_con_la_credencial(self):
        with self.captureOnCommitCallbacks(execute=True):
            register_for_event(
                student=self.kevin, event_id=self.event.pk, responses={"f1": "A"}
            )

        aviso = Notification.objects.get(
            user=self.kevin, type=Notification.Type.EVENT_REGISTERED
        )
        self.assertIn("credencial", aviso.message)

    def test_el_escaneo_avisa_al_asistente(self):
        maria = self.make_student("202055789", "María", "Cevallos")
        create_membership(student=maria, club=self.club)
        set_event_staff(event_id=self.event.pk, student_ids=[maria.pk])

        registration = register_for_event(
            student=self.kevin, event_id=self.event.pk, responses={"f1": "A"}
        )

        from apps.events.services.attendance import register_scan

        with self.captureOnCommitCallbacks(execute=True):
            register_scan(qr_token=registration.qr_token, staff_student=maria)

        self.assertTrue(
            Notification.objects.filter(
                user=self.kevin, type=Notification.Type.ATTENDANCE_REGISTERED
            ).exists()
        )


class IdempotencyTests(NotificationTestCase):
    """CU-NO3 — un aviso repetido no es un aviso nuevo."""

    def test_notificar_dos_veces_lo_mismo_no_duplica(self):
        application = self.apply()

        for _ in range(3):
            notify(
                user=self.kevin,
                type=Notification.Type.APPLICATION_APPROVED,
                message="Aprobada.",
                target=application,
            )

        self.assertEqual(
            Notification.objects.filter(
                user=self.kevin, type=Notification.Type.APPLICATION_APPROVED
            ).count(),
            1,
        )

    def test_el_congelamiento_repetido_no_duplica_avisos(self):
        """
        Lo que hace seguro programar el proceso a diario.

        Sin idempotencia, una membresía congelada generaría un aviso cada día
        hasta que alguien la renovara.
        """
        maria = self.make_student("202055789", "María", "Cevallos")
        create_membership(student=maria, club=self.club)

        with self.captureOnCommitCallbacks(execute=True):
            freeze_expired_memberships(today=datetime.date(2026, 9, 16))
        with self.captureOnCommitCallbacks(execute=True):
            freeze_expired_memberships(today=datetime.date(2026, 9, 17))

        self.assertEqual(
            Notification.objects.filter(
                user=maria, type=Notification.Type.MEMBERSHIP_FROZEN
            ).count(),
            1,
        )


class ReadingTests(NotificationTestCase):
    def setUp(self):
        super().setUp()
        self.apply()

    def test_marcar_leidas(self):
        self.assertEqual(count_unread(self.leader), 1)
        mark_read(user=self.leader)
        self.assertEqual(count_unread(self.leader), 0)

    def test_no_se_pueden_marcar_las_de_otra_persona(self):
        """Sin el filtro por usuario, bastaría con enviar ids ajenos."""
        ajena = Notification.objects.get(user=self.leader)

        marcadas = mark_read(user=self.kevin, notification_ids=[ajena.pk])

        self.assertEqual(marcadas, 0)
        ajena.refresh_from_db()
        self.assertFalse(ajena.read)


class ScheduledCommandTests(NotificationTestCase):
    """
    Los cuatro procesos del §10.

    La exigencia central: ejecutarlos dos veces no duplica efectos.
    """

    def setUp(self):
        super().setUp()
        self.maria = self.make_student("202055789", "María", "Cevallos")
        create_membership(student=self.maria, club=self.club)

        self.event_form = create_form(
            club_id=self.club.pk,
            form_type=Form.FormType.EVENT,
            title="Registro",
            fields=[
                {
                    "field_id": "f1",
                    "label": "Nivel",
                    "type": "radio",
                    "required": True,
                    "options": ["A", "B"],
                }
            ],
        )
        # Se sigue el orden real de los hechos: el evento está por ocurrir, el
        # estudiante se inscribe, y solo después el evento termina. Crearlo ya
        # terminado haría imposible la inscripción —el servicio la rechaza, y
        # con razón— y el escenario no representaría nada que pueda pasar.
        inicio = timezone.localtime()
        self.event = create_event(
            club_id=self.club.pk,
            event_name="Taller terminado",
            mode="Online",
            planned_date=inicio.date(),
            planned_hour=inicio.time().replace(microsecond=0),
            end_datetime=inicio + datetime.timedelta(hours=2),
            planned_place="Aula",
            registration_form_id=self.event_form.pk,
        )
        self.registration = register_for_event(
            student=self.kevin, event_id=self.event.pk, responses={"f1": "A"}
        )

        # Pasa el tiempo: el evento terminó hace dos días.
        pasado = inicio - datetime.timedelta(days=2)
        self.event.planned_date = pasado.date()
        self.event.planned_hour = pasado.time().replace(microsecond=0)
        self.event.end_datetime = pasado + datetime.timedelta(hours=2)
        self.event.save()

    def run_command(self, name, *args):
        out = io.StringIO()
        call_command(name, *args, stdout=out, stderr=io.StringIO())
        return out.getvalue()

    def test_dry_run_no_modifica_nada(self):
        salida = self.run_command(
            "freeze_expired_memberships", "--dry-run", "--now=2026-09-16T00:00:00"
        )

        self.assertIn("simulación", salida)
        self.assertEqual(
            self.maria.memberships.get(club=self.club).status, "Active"
        )

    def test_freeze_es_idempotente(self):
        self.run_command("freeze_expired_memberships", "--now=2026-09-16T00:00:00")
        segunda = self.run_command(
            "freeze_expired_memberships", "--now=2026-09-16T00:00:00"
        )
        self.assertIn("0 membresías", segunda)

    def test_expire_qr_tokens(self):
        """RF-37."""
        self.run_command("expire_qr_tokens")

        self.registration.refresh_from_db()
        self.assertEqual(
            self.registration.qr_status, EventRegistration.QrStatus.EXPIRED
        )

    def test_expire_qr_tokens_es_idempotente(self):
        self.run_command("expire_qr_tokens")
        self.assertIn("0 credenciales", self.run_command("expire_qr_tokens"))

    def test_mark_no_shows(self):
        self.run_command("mark_no_shows")

        self.registration.refresh_from_db()
        self.assertEqual(
            self.registration.attendance_status,
            EventRegistration.AttendanceStatus.NO_SHOW,
        )

    def test_mark_no_shows_es_idempotente(self):
        self.run_command("mark_no_shows")
        self.assertIn("0 inscripciones", self.run_command("mark_no_shows"))

    def test_expire_stale_memberships_es_idempotente(self):
        self.run_command("freeze_expired_memberships", "--now=2026-09-16T00:00:00")
        create_pao(
            pao_period="2026-II",
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2027, 2, 28),
            activate=True,
        )
        self.run_command("expire_stale_memberships")
        self.assertIn("0 membresías", self.run_command("expire_stale_memberships"))

    def test_un_now_invalido_no_revienta(self):
        salida = self.run_command("expire_qr_tokens", "--now=no-es-una-fecha")
        self.assertIn("credenciales", salida)
