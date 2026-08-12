"""
Tests de trámites ante GBP (Etapa 9).

El foco está en dos cosas: la máquina de estados §5.5 —que **no** admite el
salto directo de Submitted a Approved— y el snapshot de nómina de D-09, que es
lo que convierte el trámite en evidencia auditable en vez de en una consulta que
cambia con el tiempo.
"""

import datetime

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.academic.services import activate_pao, create_pao
from apps.accounts.models import Student
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.services.clubs import create_club
from apps.clubs.services.leadership import revoke_leader
from apps.clubs.services.memberships import create_membership, revoke_membership
from apps.gbp import selectors
from apps.gbp.models import GbpDocumentProcess
from apps.gbp.services import (
    build_roster_snapshot,
    get_history_by_pao,
    resolve_process,
    submit_process,
    take_process,
)
from core.exceptions import BusinessRuleViolation, StateTransitionError
from core.management.commands.seed_demo_data import build_minimal_pdf


class GbpTestCase(TestCase):
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
        self.member = self.make_student("202055789", "María", "Cevallos")
        create_membership(student=self.member, club=self.club)

        self.gbp = Student.objects.create_user(
            enrollment="GBP-001",
            email="arivas@espol.edu.ec",
            password="clave-de-prueba",
            first_name="Ana",
            last_name="Rivas",
            is_gbp_admin=True,
            is_verified=True,
        )

    def make_student(self, enrollment, first_name, last_name):
        return Student.objects.create_user(
            enrollment=enrollment,
            email=f"{enrollment.lower()}@espol.edu.ec",
            password="clave-de-prueba",
            first_name=first_name,
            last_name=last_name,
            is_verified=True,
        )

    def submit(self, document_type="Nómina de Miembros", pao="2026-I"):
        return submit_process(
            club_id=self.club.pk,
            pao_period=pao,
            document_type=document_type,
            file=ContentFile(build_minimal_pdf(document_type), name="nomina.pdf"),
            submitted_by=self.leader,
        )


class SubmissionTests(GbpTestCase):
    def test_enviar_crea_el_tramite_en_submitted(self):
        """Transición G1."""
        process = self.submit()

        self.assertEqual(process.status, GbpDocumentProcess.Status.SUBMITTED)
        self.assertEqual(process.submitted_by, self.leader)
        self.assertEqual(process.uploaded_at, process.created_at)

    def test_un_club_sin_lider_no_envia_tramites(self):
        revoke_leader(club_id=self.club.pk)
        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.submit()
        self.assertEqual(ctx.exception.code, "club_read_only")

    def test_solo_admite_pdf(self):
        """RNF-08."""
        with self.assertRaises(Exception):
            submit_process(
                club_id=self.club.pk,
                pao_period="2026-I",
                document_type="Nómina",
                file=ContentFile(b"no soy un pdf", name="nomina.docx"),
                submitted_by=self.leader,
            )


class RosterSnapshotTests(GbpTestCase):
    """Decisión D-09 — el trámite congela su evidencia."""

    def test_el_snapshot_recoge_la_nomina_del_momento(self):
        process = self.submit()

        matriculas = {fila["enrollment"] for fila in process.roster_snapshot}
        self.assertEqual(matriculas, {"201899001", "202055789"})
        self.assertEqual(process.snapshot_size, 2)

    def test_el_snapshot_no_cambia_si_la_nomina_cambia_despues(self):
        """
        El punto de la decisión D-09.

        Sin snapshot, un PDF aprobado dejaría de corresponder a los datos del
        sistema en cuanto alguien se diera de baja, y la auditoría no tendría
        contra qué contrastar.
        """
        process = self.submit()
        self.assertEqual(process.snapshot_size, 2)

        membership = self.member.memberships.get(club=self.club)
        revoke_membership(membership_id=membership.pk)

        process.refresh_from_db()
        self.assertEqual(process.snapshot_size, 2)
        # Mientras que la nómina viva sí refleja la baja.
        self.assertEqual(len(build_roster_snapshot(self.club.pk, "2026-I")), 2)
        self.assertEqual(self.club.members_count, 1)

    def test_el_snapshot_guarda_datos_resueltos_no_identificadores(self):
        """
        Debe poder leerse dentro de dos años, cuando el rol se haya renombrado
        o el estudiante ya no esté activo.
        """
        fila = self.submit().roster_snapshot[0]

        self.assertIn("full_name", fila)
        self.assertIn("role", fila)
        self.assertNotIn("student_id", fila)
        self.assertNotIn("role_id", fila)


class ReviewFlowTests(GbpTestCase):
    """Máquina de estados §5.5."""

    def setUp(self):
        super().setUp()
        self.process = self.submit()

    def test_no_se_puede_aprobar_sin_tomar_el_tramite(self):
        """
        Resuelve PPD-05: Submitted → Approved directo no existe.

        Obligar a pasar por Under Review garantiza que siempre haya un
        administrador identificable como responsable (RF-52).
        """
        with self.assertRaises(StateTransitionError) as ctx:
            resolve_process(
                process_id=self.process.pk, reviewer=self.gbp, approved=True
            )
        self.assertEqual(ctx.exception.code, "process_not_under_review")

    def test_tomar_registra_quien_revisa(self):
        """Transición G2."""
        process = take_process(process_id=self.process.pk, reviewer=self.gbp)

        self.assertEqual(process.status, GbpDocumentProcess.Status.UNDER_REVIEW)
        self.assertEqual(process.reviewed_by, self.gbp)

    def test_no_se_toma_dos_veces(self):
        take_process(process_id=self.process.pk, reviewer=self.gbp)
        with self.assertRaises(StateTransitionError) as ctx:
            take_process(process_id=self.process.pk, reviewer=self.gbp)
        self.assertEqual(ctx.exception.code, "process_not_submitted")

    def test_aprobar(self):
        """Transición G3."""
        take_process(process_id=self.process.pk, reviewer=self.gbp)
        process = resolve_process(
            process_id=self.process.pk, reviewer=self.gbp, approved=True
        )

        self.assertEqual(process.status, GbpDocumentProcess.Status.APPROVED)
        self.assertIsNotNone(process.reviewed_at)

    def test_rechazar_exige_feedback(self):
        """RN-5."""
        take_process(process_id=self.process.pk, reviewer=self.gbp)

        for vacio in ["", "   ", None]:
            with self.assertRaises(BusinessRuleViolation) as ctx:
                resolve_process(
                    process_id=self.process.pk,
                    reviewer=self.gbp,
                    approved=False,
                    feedback=vacio,
                )
            self.assertEqual(ctx.exception.code, "rejection_feedback_required")

    def test_rechazar_con_feedback(self):
        """Transición G4."""
        take_process(process_id=self.process.pk, reviewer=self.gbp)
        process = resolve_process(
            process_id=self.process.pk,
            reviewer=self.gbp,
            approved=False,
            feedback="Falta la firma del presidente en la página 2.",
        )

        self.assertEqual(process.status, GbpDocumentProcess.Status.REJECTED)
        self.assertIn("firma", process.review_feedback)

    def test_la_base_rechaza_una_negativa_sin_justificacion(self):
        """RN-5 defendida por CHECK."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GbpDocumentProcess.objects.filter(pk=self.process.pk).update(
                    status=GbpDocumentProcess.Status.REJECTED, review_feedback=""
                )

    def test_un_rechazo_reabre_la_via_para_enviar_otro(self):
        """El club corrige y vuelve a enviar."""
        take_process(process_id=self.process.pk, reviewer=self.gbp)
        resolve_process(
            process_id=self.process.pk,
            reviewer=self.gbp,
            approved=False,
            feedback="Falta la firma.",
        )

        corregido = self.submit()
        self.assertEqual(corregido.status, GbpDocumentProcess.Status.SUBMITTED)
        self.assertEqual(GbpDocumentProcess.objects.count(), 2)

    def test_no_se_resuelve_dos_veces(self):
        take_process(process_id=self.process.pk, reviewer=self.gbp)
        resolve_process(
            process_id=self.process.pk, reviewer=self.gbp, approved=True
        )

        with self.assertRaises(StateTransitionError):
            resolve_process(
                process_id=self.process.pk, reviewer=self.gbp, approved=True
            )


class InboxTests(GbpTestCase):
    def test_filtra_por_estado(self):
        primero = self.submit("Nómina de Miembros")
        self.submit("Estatutos")
        take_process(process_id=primero.pk, reviewer=self.gbp)

        pendientes = selectors.get_inbox(
            status=GbpDocumentProcess.Status.SUBMITTED
        )
        self.assertEqual(pendientes.count(), 1)
        self.assertEqual(selectors.count_pending_review(), 1)

    def test_filtra_por_periodo(self):
        self.submit()
        create_pao(
            pao_period="2026-II",
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2027, 2, 28),
        )
        self.submit(pao="2026-II")

        self.assertEqual(selectors.get_inbox(pao_period="2026-I").count(), 1)


class HistoryTests(GbpTestCase):
    """RF-49 — el histórico por período."""

    def test_reconstruye_el_estado_del_periodo(self):
        historico = get_history_by_pao("2026-I")

        self.assertEqual(len(historico), 1)
        entrada = historico[0]
        self.assertEqual(entrada["acronym"], "KOKOA")
        self.assertEqual(entrada["leader"]["enrollment"], "201899001")
        self.assertEqual(entrada["members_count"], 2)

    def test_un_periodo_sin_actividad_devuelve_vacio(self):
        create_pao(
            pao_period="2025-II",
            start_date=datetime.date(2025, 10, 13),
            end_date=datetime.date(2026, 2, 27),
        )
        self.assertEqual(get_history_by_pao("2025-II"), [])

    def test_el_historico_sobrevive_a_los_cambios_posteriores(self):
        """
        Es consultable porque las membresías no se borran: se congelan (P-4).

        Tras revocar el liderazgo, el histórico del período debe seguir
        mostrando cuántas personas hubo, aunque el club ya no tenga líder.
        """
        revoke_leader(club_id=self.club.pk)

        entrada = get_history_by_pao("2026-I")[0]
        self.assertEqual(entrada["members_count"], 2)
        self.assertEqual(entrada["active_members"], 1)
