"""
Tests de solicitudes de membresía (Etapa 6).

El foco está en RN-2, que tiene dos mitades que se contradicen si se leen a la
ligera: prohíbe duplicar una postulación pendiente, pero **permite reenviar de
inmediato** una rechazada. Implementarla como "una solicitud por estudiante y
club" rompería RF-29.
"""

import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.academic.services import create_pao
from apps.accounts.models import Student
from apps.applications import selectors
from apps.applications.models import MembershipApplication
from apps.applications.services import (
    approve_application,
    can_apply,
    count_form_responses,
    reject_application,
    submit_application,
)
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.models import Membership
from apps.clubs.services.clubs import create_club
from apps.clubs.services.leadership import revoke_leader
from apps.clubs.services.memberships import create_membership
from apps.dynamicforms.models import Form
from apps.dynamicforms.responses import form_has_responses
from apps.dynamicforms.services import create_form, update_form
from core.exceptions import BusinessRuleViolation, StateTransitionError

SCHEMA = [
    {
        "field_id": "q1",
        "label": "¿Por qué quieres unirte?",
        "type": "textarea",
        "required": True,
        "order": 1,
        "validation": {"max_length": 500},
    },
    {
        "field_id": "q2",
        "label": "Nivel de experiencia",
        "type": "select",
        "required": True,
        "order": 2,
        "options": ["Principiante", "Intermedio", "Avanzado"],
    },
]

VALID_RESPONSES = {"q1": "Me interesa el software libre.", "q2": "Intermedio"}


class ApplicationTestCase(TestCase):
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
            title="Formulario de Inscripción - KOKOA",
            fields=SCHEMA,
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

    def apply(self, student=None, responses=None):
        return submit_application(
            student=student or self.kevin,
            club_id=self.club.pk,
            responses=responses or VALID_RESPONSES,
        )


class SubmissionTests(ApplicationTestCase):
    def test_postular_crea_la_solicitud_pendiente(self):
        """Transición A1."""
        application = self.apply()

        self.assertEqual(application.status, MembershipApplication.Status.PENDING)
        self.assertEqual(application.form, self.form)
        self.assertEqual(application.submitted_at, application.created_at)

    def test_las_respuestas_se_guardan_normalizadas(self):
        application = self.apply(responses={"q1": "  Con espacios  ", "q2": "Avanzado"})
        self.assertEqual(
            application.responses,
            [
                {"field_id": "q1", "answer": "Con espacios"},
                {"field_id": "q2", "answer": "Avanzado"},
            ],
        )

    def test_rechaza_respuestas_invalidas(self):
        """CU-FO6 actúa antes de tocar la base."""
        with self.assertRaises(Exception):
            self.apply(responses={"q1": "Texto", "q2": "Experto"})
        self.assertEqual(MembershipApplication.objects.count(), 0)

    def test_no_se_puede_postular_a_un_club_sin_lider(self):
        revoke_leader(club_id=self.club.pk)
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.apply()
        self.assertEqual(ctx.exception.code, "club_not_active")

    def test_no_se_puede_postular_sin_formulario_publicado(self):
        Form.objects.all().delete()
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.apply()
        self.assertEqual(ctx.exception.code, "no_membership_form")


class ApplicationRestrictionTests(ApplicationTestCase):
    """RN-2 — sus dos mitades."""

    def test_no_se_puede_duplicar_una_solicitud_pendiente(self):
        self.apply()
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.apply()

        self.assertEqual(ctx.exception.code, "already_pending")
        self.assertEqual(ctx.exception.message, "Ya tienes una solicitud pendiente en este club.")

    def test_la_base_rechaza_la_pendiente_duplicada(self):
        """
        Invariante I-10 — tercera unicidad condicional del sistema.

        Se salta el servicio por completo: bajo concurrencia, dos peticiones
        pueden pasar la validación de Python a la vez.
        """
        self.apply()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MembershipApplication.objects.create(
                    student=self.kevin,
                    club=self.club,
                    form=self.form,
                    responses=[],
                    status=MembershipApplication.Status.PENDING,
                )

    def test_un_miembro_activo_no_puede_postular(self):
        create_membership(student=self.kevin, club=self.club)
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.apply()

        self.assertEqual(ctx.exception.code, "already_member")
        self.assertEqual(ctx.exception.message, "Ya eres miembro activo de este club.")

    def test_una_solicitud_rechazada_se_puede_reenviar_de_inmediato(self):
        """
        RF-29 — la mitad de RN-2 que se pierde si se implementa a la ligera.

        Con una unicidad simple sobre (estudiante, club), esto sería imposible.
        Por eso el índice es condicional al estado Pendiente.
        """
        primera = self.apply()
        reject_application(
            application_id=primera.pk,
            resolved_by=self.leader,
            feedback="Cupo lleno este PAO; vuelve a postular el próximo período.",
        )

        segunda = self.apply()

        self.assertEqual(segunda.status, MembershipApplication.Status.PENDING)
        self.assertNotEqual(segunda.pk, primera.pk)
        self.assertEqual(MembershipApplication.objects.count(), 2)

    def test_tras_aprobar_ya_no_se_puede_postular(self):
        primera = self.apply()
        approve_application(application_id=primera.pk, resolved_by=self.leader)

        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.apply()
        self.assertEqual(ctx.exception.code, "already_member")


class CanApplyTests(ApplicationTestCase):
    def test_permite_a_un_estudiante_elegible(self):
        verdict = can_apply(self.kevin, self.club.pk)
        self.assertTrue(verdict["allowed"])
        self.assertIsNone(verdict["reason"])

    def test_los_motivos_usan_los_mensajes_canonicos(self):
        """MASTER §12: la app móvil y la web muestran exactamente estos textos."""
        self.apply()
        self.assertEqual(
            can_apply(self.kevin, self.club.pk)["reason"],
            "Ya tienes una solicitud pendiente en este club.",
        )

    def test_un_club_inexistente_no_revienta(self):
        verdict = can_apply(self.kevin, 99999)
        self.assertFalse(verdict["allowed"])
        self.assertEqual(verdict["code"], "not_found")


class ApprovalTests(ApplicationTestCase):
    """Transición A2 — la operación transaccionalmente crítica."""

    def test_aprobar_crea_la_membresia_con_el_rol_base(self):
        """RF-08."""
        application = self.apply()
        resolved = approve_application(
            application_id=application.pk, resolved_by=self.leader
        )

        self.assertEqual(resolved.status, MembershipApplication.Status.APPROVED)
        membership = resolved.resulting_membership
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role.role_name, "Miembro")
        self.assertEqual(membership.status, Membership.Status.ACTIVE)
        self.assertEqual(membership.origin, Membership.Origin.APPLICATION)

    def test_registra_quien_aprobo_y_cuando(self):
        """RF-52 / decisión D-04."""
        application = self.apply()
        resolved = approve_application(
            application_id=application.pk, resolved_by=self.leader
        )

        self.assertEqual(resolved.resolved_by, self.leader)
        self.assertIsNotNone(resolved.resolved_at)

    def test_la_membresia_apunta_de_vuelta_a_su_solicitud(self):
        application = self.apply()
        resolved = approve_application(
            application_id=application.pk, resolved_by=self.leader
        )
        self.assertEqual(resolved.resulting_membership.source_application, resolved)

    def test_no_se_aprueba_dos_veces(self):
        application = self.apply()
        approve_application(application_id=application.pk, resolved_by=self.leader)

        with self.assertRaises(StateTransitionError) as ctx:
            approve_application(application_id=application.pk, resolved_by=self.leader)
        self.assertEqual(ctx.exception.code, "application_already_resolved")

    def test_si_falla_la_membresia_la_solicitud_sigue_pendiente(self):
        """
        Atomicidad: una solicitud aprobada sin membresía sería un estado
        corrupto que ningún proceso podría reparar solo.
        """
        application = self.apply()
        create_membership(student=self.kevin, club=self.club)

        with self.assertRaises(BusinessRuleViolation):
            approve_application(application_id=application.pk, resolved_by=self.leader)

        application.refresh_from_db()
        self.assertEqual(application.status, MembershipApplication.Status.PENDING)
        self.assertIsNone(application.resulting_membership)


class RejectionTests(ApplicationTestCase):
    """Transición A3 — RN-5."""

    def test_rechazar_exige_feedback(self):
        application = self.apply()

        for vacio in ["", "   ", None]:
            with self.assertRaises(BusinessRuleViolation) as ctx:
                reject_application(
                    application_id=application.pk,
                    resolved_by=self.leader,
                    feedback=vacio,
                )
            self.assertEqual(ctx.exception.code, "rejection_feedback_required")

    def test_rechazar_con_feedback_funciona(self):
        application = self.apply()
        resolved = reject_application(
            application_id=application.pk,
            resolved_by=self.leader,
            feedback="Cupo lleno este PAO.",
        )

        self.assertEqual(resolved.status, MembershipApplication.Status.REJECTED)
        self.assertEqual(resolved.leader_feedback, "Cupo lleno este PAO.")
        self.assertEqual(resolved.resolved_by, self.leader)
        self.assertIsNone(resolved.resulting_membership)

    def test_la_base_rechaza_una_negativa_sin_justificacion(self):
        """RN-5 defendida por CHECK, no solo en Python."""
        application = self.apply()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MembershipApplication.objects.filter(pk=application.pk).update(
                    status=MembershipApplication.Status.REJECTED, leader_feedback=""
                )

    def test_rechazar_no_crea_membresia(self):
        application = self.apply()
        reject_application(
            application_id=application.pk,
            resolved_by=self.leader,
            feedback="No este período.",
        )
        self.assertFalse(
            Membership.objects.filter(student=self.kevin, club=self.club).exists()
        )


class FormImmutabilityIntegrationTests(ApplicationTestCase):
    """
    RF-24 con el contador **real**, no simulado.

    Hasta esta etapa ningún flujo generaba respuestas, así que la inmutabilidad
    de los formularios nunca llegaba a activarse.
    """

    def test_una_solicitud_bloquea_la_edicion_del_formulario(self):
        self.assertFalse(form_has_responses(self.form))

        self.apply()

        self.assertTrue(form_has_responses(self.form))
        with self.assertRaises(StateTransitionError) as ctx:
            update_form(form_id=self.form.pk, title="Ya no debería poder")
        self.assertEqual(ctx.exception.code, "form_has_responses")

    def test_las_solicitudes_resueltas_tambien_cuentan(self):
        """
        Una solicitud resuelta sigue siendo una respuesta ligada a ese esquema:
        editarlo volvería ilegible el histórico.
        """
        application = self.apply()
        reject_application(
            application_id=application.pk,
            resolved_by=self.leader,
            feedback="No este período.",
        )
        self.assertEqual(count_form_responses(self.form), 1)


class SelectorTests(ApplicationTestCase):
    def test_la_bandeja_filtra_por_estado(self):
        pendiente = self.apply()
        lucia = self.make_student("202144556", "Lucía", "Torres")
        rechazada = self.apply(student=lucia)
        reject_application(
            application_id=rechazada.pk, resolved_by=self.leader, feedback="No."
        )

        pendientes = selectors.get_club_applications(
            self.club.pk, status=MembershipApplication.Status.PENDING
        )
        self.assertEqual([a.pk for a in pendientes], [pendiente.pk])
        self.assertEqual(selectors.count_pending(self.club.pk), 1)

    def test_las_respuestas_se_resuelven_contra_su_propia_version(self):
        """
        Si el formulario se versiona, la solicitud vieja debe seguir mostrando
        las preguntas que su autor vio, no las nuevas.
        """
        application = self.apply()
        etiquetas = [entry["label"] for entry in application.answers_with_labels()]
        self.assertEqual(etiquetas, ["¿Por qué quieres unirte?", "Nivel de experiencia"])
