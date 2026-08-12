"""
Tests de la Etapa 2.

Cada regla de negocio de MASTER §6 que toca esta app tiene aquí una prueba que
verifica **que el rechazo ocurre**, no solo que el camino feliz funciona.
"""

import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.academic.models import PaoPeriod
from apps.academic.services import activate_pao, create_pao
from apps.accounts.models import AppRole, Student
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs import policies, selectors
from apps.clubs.models import Club, Membership, Role
from apps.clubs.permissions import ClubPermission
from apps.clubs.services.clubs import create_club, update_club
from apps.clubs.services.leadership import (
    activate_pending_leadership,
    assign_leader,
    revoke_leader,
)
from apps.clubs.services.memberships import (
    create_membership,
    expire_stale_memberships,
    freeze_expired_memberships,
    renew_roster,
    revoke_membership,
    set_membership_role,
)
from apps.clubs.services.roles import create_role, delete_role, update_role
from core.exceptions import BusinessRuleViolation, DomainValidationError


class ClubTestCase(TestCase):
    """Escenario común: un PAO activo, una facultad, un área y un estudiante."""

    def setUp(self):
        self.pao = create_pao(
            pao_period="2026-I",
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 9, 15),
            activate=True,
        )
        self.faculty = Faculty.objects.get(code="FIEC")
        self.area = InterestArea.objects.get(name="Tecnología")

    def make_student(self, enrollment, first_name="Nombre", last_name="Apellido"):
        return Student.objects.create_user(
            enrollment=enrollment,
            email=f"{enrollment.lower()}@espol.edu.ec",
            password="clave-de-prueba",
            first_name=first_name,
            last_name=last_name,
        )

    def make_club(self, acronym="KOKOA", leader_enrollment="", **kwargs):
        return create_club(
            name=kwargs.get("name", f"Club {acronym}"),
            acronym=acronym,
            description="Descripción del club.",
            location="FIEC 11D",
            leader_enrollment=leader_enrollment,
            faculty=self.faculty,
            interest_area_ids=[self.area.id],
        )


class ClubCreationTests(ClubTestCase):
    def test_el_club_nace_con_los_cuatro_roles(self):
        """RF-06."""
        club = self.make_club()
        nombres = set(club.roles.values_list("role_name", flat=True))
        self.assertEqual(
            nombres,
            {"Presidente/a", "Vicepresidente/a", "Secretario/a", "Miembro"},
        )
        self.assertTrue(all(club.roles.values_list("is_default", flat=True)))

    def test_exige_al_menos_un_area_de_interes(self):
        """RF-15."""
        with self.assertRaises(BusinessRuleViolation) as ctx:
            create_club(
                name="Sin áreas",
                acronym="SA",
                description="x",
                location="y",
                leader_enrollment="",
                faculty=self.faculty,
                interest_area_ids=[],
            )
        self.assertEqual(ctx.exception.code, "missing_interest_areas")

    def test_con_matricula_registrada_queda_activo(self):
        """Transición C1."""
        self.make_student("201899001", "Diego", "Ponce")
        club = self.make_club(leader_enrollment="201899001")

        self.assertEqual(club.status, Club.Status.ACTIVE)
        self.assertEqual(club.leader.enrollment, "201899001")
        self.assertTrue(
            club.memberships.filter(
                is_leadership=True, status=Membership.Status.ACTIVE
            ).exists()
        )

    def test_con_matricula_sin_cuenta_queda_pendiente_pero_recuerda_la_matricula(self):
        """
        Transición C2 y decisión D-01.

        El punto crítico: la matrícula comprometida **sobrevive** aunque no
        exista la cuenta. Si se hubiera modelado solo como FK, se perdería y
        RF-12 sería imposible de cumplir.
        """
        club = self.make_club(acronym="MECA", leader_enrollment="202099777")

        self.assertEqual(club.status, Club.Status.PENDING_LEADER)
        self.assertIsNone(club.leader)
        self.assertEqual(club.leader_enrollment, "202099777")

    def test_club_sin_lider_esta_en_solo_lectura(self):
        """RF-13 / invariante I-19."""
        club = self.make_club(acronym="MECA", leader_enrollment="202099777")

        with self.assertRaises(BusinessRuleViolation) as ctx:
            update_club(club_id=club.pk, name="Nuevo nombre")
        self.assertEqual(ctx.exception.code, "club_read_only")


class LeadershipExclusivityTests(ClubTestCase):
    """RN-1 — la regla que MASTER §20.16 señala como nunca validada en Fase 1."""

    def setUp(self):
        super().setUp()
        self.diego = self.make_student("201899001", "Diego", "Ponce")
        self.kokoa = self.make_club(acronym="KOKOA", leader_enrollment="201899001")
        self.otro = self.make_club(acronym="OTRO", leader_enrollment="")

    def test_no_puede_liderar_dos_clubes(self):
        with self.assertRaises(BusinessRuleViolation) as ctx:
            assign_leader(club_id=self.otro.pk, enrollment="201899001")
        self.assertEqual(ctx.exception.code, "leadership_exclusivity")
        self.assertIn("KOKOA", ctx.exception.message)

    def test_la_base_rechaza_el_segundo_liderazgo(self):
        """
        Prueba decisiva de I-09: se salta los servicios por completo.

        La validación en Python puede pasar bajo concurrencia; el índice único
        sobre la columna generada es la defensa que no se puede eludir.
        """
        presidente_otro = Role.objects.get(club=self.otro, role_name="Presidente/a")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(
                    student=self.diego,
                    club=self.otro,
                    role=presidente_otro,
                    pao_period=self.pao,
                    valid_from=self.pao.start_date,
                    valid_until=self.pao.end_date,
                    status=Membership.Status.ACTIVE,
                )

    def test_si_puede_ser_miembro_comun_de_otro_club(self):
        """RF-17: varios clubes como miembro, uno solo como líder."""
        membership = create_membership(student=self.diego, club=self.otro)

        self.assertEqual(membership.status, Membership.Status.ACTIVE)
        self.assertFalse(membership.is_leadership)
        self.assertIsNone(membership.leadership_lock)

    def test_revocar_el_liderazgo_libera_la_regla(self):
        """Transición C5: tras revocar, puede liderar otro club."""
        revoke_leader(club_id=self.kokoa.pk)

        self.kokoa.refresh_from_db()
        self.assertEqual(self.kokoa.status, Club.Status.PENDING_LEADER)
        self.assertIsNone(self.kokoa.leader)

        club = assign_leader(club_id=self.otro.pk, enrollment="201899001")
        self.assertEqual(club.status, Club.Status.ACTIVE)

    def test_revocar_deja_la_membresia_como_revocada_no_la_borra(self):
        """P-4: nada se borra físicamente."""
        revoke_leader(club_id=self.kokoa.pk)
        membership = Membership.objects.get(student=self.diego, club=self.kokoa)
        self.assertEqual(membership.status, Membership.Status.REVOKED)


class DeferredLeaderActivationTests(ClubTestCase):
    """RF-12 / transición C3 — el club despierta cuando la matrícula se registra."""

    def test_activacion_diferida(self):
        club = self.make_club(acronym="MECA", leader_enrollment="202099777")
        self.assertEqual(club.status, Club.Status.PENDING_LEADER)

        nuevo = self.make_student("202099777", "Ana", "Vera")
        activados = activate_pending_leadership(nuevo)

        club.refresh_from_db()
        self.assertEqual([c.pk for c in activados], [club.pk])
        self.assertEqual(club.status, Club.Status.ACTIVE)
        self.assertEqual(club.leader, nuevo)
        self.assertEqual(nuevo.app_role, AppRole.CLUB_LEADER)

    def test_dos_clubes_pendientes_de_la_misma_matricula_solo_activan_uno(self):
        """
        RN-1 tiene prioridad sobre el compromiso pendiente.

        Caso real: GBP comprometió la misma matrícula como líder de dos clubes
        mientras esa persona no tenía cuenta —nada lo impide, porque sin cuenta
        no hay membresía que verificar—. Al registrarse, solo uno puede
        activarse; el otro sigue esperando a que GBP lo resuelva.
        """
        primero = self.make_club(acronym="MECA", leader_enrollment="202099777")
        segundo = self.make_club(acronym="ROBOT", leader_enrollment="202099777")

        nuevo = self.make_student("202099777", "Ana", "Vera")
        activados = activate_pending_leadership(nuevo)

        primero.refresh_from_db()
        segundo.refresh_from_db()

        self.assertEqual(len(activados), 1)
        estados = {primero.status, segundo.status}
        self.assertEqual(estados, {Club.Status.ACTIVE, Club.Status.PENDING_LEADER})
        self.assertEqual(
            Membership.objects.filter(
                student=nuevo, is_leadership=True, status=Membership.Status.ACTIVE
            ).count(),
            1,
        )

    def test_no_se_puede_dar_de_alta_un_club_con_un_lider_ya_ocupado(self):
        """
        El alta falla completa en vez de crear un club condenado.

        Crear el club en 'Pending Leader' silenciosamente lo dejaría esperando
        para siempre a alguien que nunca podrá tomar el cargo, sin que nadie
        sepa por qué. Es preferible que GBP reciba el error y corrija.
        """
        self.make_student("201899001", "Diego", "Ponce")
        self.make_club(acronym="KOKOA", leader_enrollment="201899001")

        with self.assertRaises(BusinessRuleViolation) as ctx:
            self.make_club(acronym="MECA", leader_enrollment="201899001")
        self.assertEqual(ctx.exception.code, "leadership_exclusivity")
        self.assertFalse(Club.objects.filter(acronym="MECA").exists())


class RolePermissionTests(ClubTestCase):
    def setUp(self):
        super().setUp()
        self.make_student("201899001", "Diego", "Ponce")
        self.club = self.make_club(leader_enrollment="201899001")

    def test_manage_roles_solo_para_roles_directivos(self):
        """RN-7 — MASTER §20.17: documentada pero nunca aplicada en Fase 1."""
        with self.assertRaises(DomainValidationError):
            create_role(
                club_id=self.club.pk,
                role_name="Falso directivo",
                is_leadership=False,
                permissions={ClubPermission.MANAGE_ROLES: True},
            )

    def test_rol_directivo_si_puede_recibir_manage_roles(self):
        role = create_role(
            club_id=self.club.pk,
            role_name="Vicepresidencia delegada",
            is_leadership=True,
            permissions={ClubPermission.MANAGE_ROLES: True},
        )
        self.assertTrue(role.has(ClubPermission.MANAGE_ROLES))

    def test_permiso_desconocido_es_rechazado(self):
        with self.assertRaises(DomainValidationError):
            create_role(
                club_id=self.club.pk,
                role_name="Raro",
                permissions={"volar": True},
            )

    def test_clave_ausente_vale_false(self):
        role = Role.objects.get(club=self.club, role_name="Miembro")
        self.assertFalse(role.has(ClubPermission.MANAGE_MEMBERS))
        self.assertFalse(role.has(ClubPermission.ACCESS_WEB_PANEL))

    def test_nombre_de_rol_unico_por_club(self):
        with self.assertRaises(BusinessRuleViolation) as ctx:
            create_role(club_id=self.club.pk, role_name="Miembro")
        self.assertEqual(ctx.exception.code, "duplicate_role_name")

    def test_los_roles_por_defecto_no_se_borran(self):
        role = Role.objects.get(club=self.club, role_name="Miembro")
        with self.assertRaises(BusinessRuleViolation) as ctx:
            delete_role(role_id=role.pk)
        self.assertEqual(ctx.exception.code, "default_role_protected")

    def test_rol_en_uso_no_se_borra(self):
        """D-13: se desactiva para no dejar ilegible la nómina histórica."""
        estudiante = self.make_student("202144556", "Lucía", "Torres")
        role = create_role(club_id=self.club.pk, role_name="Encargado de Documentos")
        create_membership(student=estudiante, club=self.club, role=role)

        with self.assertRaises(BusinessRuleViolation) as ctx:
            delete_role(role_id=role.pk)
        self.assertEqual(ctx.exception.code, "role_in_use")

    def test_cambiar_el_flag_directivo_resincroniza_los_snapshots(self):
        """
        Decisión D-05: el snapshot no puede quedar desalineado del rol.

        Si se desalineara, el índice de RN-1 vigilaría un dato obsoleto.
        """
        estudiante = self.make_student("202144556", "Lucía", "Torres")
        role = create_role(club_id=self.club.pk, role_name="Coordinación")
        membership = create_membership(student=estudiante, club=self.club, role=role)
        self.assertFalse(membership.is_leadership)

        update_role(role_id=role.pk, is_leadership=True)

        membership.refresh_from_db()
        self.assertTrue(membership.is_leadership)
        self.assertEqual(membership.leadership_lock, estudiante.pk)


class MembershipTests(ClubTestCase):
    def setUp(self):
        super().setUp()
        self.make_student("201899001", "Diego", "Ponce")
        self.club = self.make_club(leader_enrollment="201899001")
        self.maria = self.make_student("202055789", "María", "Cevallos")

    def test_alta_asigna_el_rol_base(self):
        """RF-08."""
        membership = create_membership(student=self.maria, club=self.club)
        self.assertEqual(membership.role.role_name, "Miembro")
        self.assertEqual(membership.valid_from, self.pao.start_date)
        self.assertEqual(membership.valid_until, self.pao.end_date)

    def test_una_membresia_por_club_y_periodo(self):
        """Invariante I-06."""
        create_membership(student=self.maria, club=self.club)
        with self.assertRaises(BusinessRuleViolation) as ctx:
            create_membership(student=self.maria, club=self.club)
        self.assertEqual(ctx.exception.code, "duplicate_membership")

    def test_el_rol_debe_ser_del_mismo_club(self):
        """Invariante I-11 / RF-09."""
        otro = self.make_club(acronym="OTRO")
        role_ajeno = Role.objects.get(club=otro, role_name="Miembro")

        with self.assertRaises(BusinessRuleViolation) as ctx:
            create_membership(student=self.maria, club=self.club, role=role_ajeno)
        self.assertEqual(ctx.exception.code, "role_club_mismatch")

    def test_baja_logica_no_borra(self):
        """RF-19."""
        membership = create_membership(student=self.maria, club=self.club)
        revoke_membership(membership_id=membership.pk)

        membership.refresh_from_db()
        self.assertEqual(membership.status, Membership.Status.REVOKED)

    def test_el_liderazgo_no_se_revoca_desde_la_nomina(self):
        """Solo GBP retira el liderazgo (CU-CL13)."""
        lider = Membership.objects.get(club=self.club, is_leadership=True)
        with self.assertRaises(BusinessRuleViolation) as ctx:
            revoke_membership(membership_id=lider.pk)
        self.assertEqual(ctx.exception.code, "leadership_revocation_reserved")

    def test_cambio_de_rol_a_directivo_verifica_rn1(self):
        otro = self.make_club(acronym="OTRO", leader_enrollment="202055789")
        membership = create_membership(student=self.maria, club=self.club)
        presidencia = Role.objects.get(club=self.club, role_name="Presidente/a")

        with self.assertRaises(BusinessRuleViolation) as ctx:
            set_membership_role(membership_id=membership.pk, role_id=presidencia.pk)
        self.assertEqual(ctx.exception.code, "leadership_exclusivity")
        self.assertEqual(otro.leader, self.maria)


class RosterLifecycleTests(ClubTestCase):
    """Vigencia por PAO: transiciones M2, M3 y M5."""

    def setUp(self):
        super().setUp()
        self.make_student("201899001", "Diego", "Ponce")
        self.club = self.make_club(leader_enrollment="201899001")
        self.maria = self.make_student("202055789", "María", "Cevallos")
        self.membership = create_membership(student=self.maria, club=self.club)

    def test_congelamiento_al_vencer_el_periodo(self):
        """RF-20 / RN-4."""
        tocadas = freeze_expired_memberships(today=datetime.date(2026, 9, 16))
        self.membership.refresh_from_db()

        self.assertGreaterEqual(tocadas, 1)
        self.assertEqual(self.membership.status, Membership.Status.FROZEN)

    def test_el_congelamiento_es_idempotente(self):
        freeze_expired_memberships(today=datetime.date(2026, 9, 16))
        segunda = freeze_expired_memberships(today=datetime.date(2026, 9, 16))
        self.assertEqual(segunda, 0)

    def test_renovar_crea_una_membresia_nueva_y_conserva_la_congelada(self):
        """
        Transición M5 — la regla más fácil de implementar mal.

        Renovar NO reactiva la membresía anterior: la histórica permanece
        congelada como evidencia del período, que es lo que hace consultable el
        histórico de RF-49.
        """
        freeze_expired_memberships(today=datetime.date(2026, 9, 16))

        siguiente = create_pao(
            pao_period="2026-II",
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2027, 2, 28),
            activate=True,
        )
        resultado = renew_roster(
            club_id=self.club.pk, membership_ids=[self.membership.pk]
        )

        self.membership.refresh_from_db()
        self.assertEqual(self.membership.status, Membership.Status.FROZEN)
        self.assertEqual(self.membership.pao_period_id, "2026-I")

        nueva = resultado["renewed"][0]
        self.assertEqual(nueva.pao_period_id, siguiente.pk)
        self.assertEqual(nueva.status, Membership.Status.ACTIVE)
        self.assertEqual(nueva.origin, Membership.Origin.RENEWAL)
        self.assertEqual(nueva.role, self.membership.role)

    def test_renovar_dos_veces_no_duplica(self):
        freeze_expired_memberships(today=datetime.date(2026, 9, 16))
        create_pao(
            pao_period="2026-II",
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2027, 2, 28),
            activate=True,
        )
        renew_roster(club_id=self.club.pk, membership_ids=[self.membership.pk])
        segunda = renew_roster(
            club_id=self.club.pk, membership_ids=[self.membership.pk]
        )

        self.assertEqual(segunda["renewed"], [])
        self.assertEqual(len(segunda["skipped"]), 1)

    def test_expiracion_de_las_no_renovadas(self):
        """Transición M3."""
        freeze_expired_memberships(today=datetime.date(2026, 9, 16))
        create_pao(
            pao_period="2026-II",
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2027, 2, 28),
            activate=True,
        )

        expiradas = expire_stale_memberships()
        self.membership.refresh_from_db()

        self.assertGreaterEqual(expiradas, 1)
        self.assertEqual(self.membership.status, Membership.Status.EXPIRED)

    def test_la_renovada_no_expira(self):
        freeze_expired_memberships(today=datetime.date(2026, 9, 16))
        create_pao(
            pao_period="2026-II",
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2027, 2, 28),
            activate=True,
        )
        renew_roster(club_id=self.club.pk, membership_ids=[self.membership.pk])

        expire_stale_memberships()
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.status, Membership.Status.FROZEN)


class PrivacyPolicyTests(ClubTestCase):
    """RN-3 / RF-47 / RF-48 — quién ve qué."""

    def setUp(self):
        super().setUp()
        self.diego = self.make_student("201899001", "Diego", "Ponce")
        self.club = self.make_club(leader_enrollment="201899001")
        self.maria = self.make_student("202055789", "María", "Cevallos")
        create_membership(student=self.maria, club=self.club)
        self.extrano = self.make_student("202311346", "Kevin", "Maldonado")
        self.gbp = Student.objects.create_user(
            enrollment="GBP-001",
            email="arivas@espol.edu.ec",
            password="x",
            first_name="Ana",
            last_name="Rivas",
            is_gbp_admin=True,
        )

    def test_el_no_miembro_no_ve_la_nomina(self):
        self.assertFalse(policies.can_see_roster(self.extrano, self.club.pk))

    def test_el_miembro_y_gbp_si_la_ven(self):
        self.assertTrue(policies.can_see_roster(self.maria, self.club.pk))
        self.assertTrue(policies.can_see_roster(self.gbp, self.club.pk))

    def test_gbp_no_puede_editar_el_interior_del_club(self):
        """MASTER §3.1: GBP audita y valida, no edita."""
        self.assertFalse(
            policies.has_club_permission(
                self.gbp, self.club.pk, ClubPermission.MANAGE_CLUB_INFO
            )
        )

    def test_el_lider_tiene_los_permisos_de_su_rol(self):
        for permiso in ClubPermission:
            self.assertTrue(
                policies.has_club_permission(self.diego, self.club.pk, permiso),
                f"El Presidente/a debería tener {permiso}",
            )

    def test_el_miembro_base_no_tiene_permisos_administrativos(self):
        self.assertFalse(
            policies.has_club_permission(
                self.maria, self.club.pk, ClubPermission.MANAGE_MEMBERS
            )
        )

    def test_un_club_sin_lider_no_admite_escrituras_ni_de_su_lider(self):
        """Invariante I-19 embebido en el predicado."""
        revoke_leader(club_id=self.club.pk)
        self.assertFalse(
            policies.has_club_permission(
                self.diego, self.club.pk, ClubPermission.MANAGE_EVENTS
            )
        )

    def test_documentos_privados_solo_para_miembros(self):
        publicos = selectors.get_club_documents(self.club.pk)
        todos = selectors.get_club_documents(self.club.pk, include_private=True)
        self.assertEqual(publicos.count(), 0)
        self.assertEqual(todos.count(), 0)

    def test_el_catalogo_expone_el_conteo_no_las_identidades(self):
        """RF-47."""
        club = selectors.list_clubs().get(pk=self.club.pk)
        self.assertEqual(club.active_members, 2)


class AppRoleDerivationTests(ClubTestCase):
    """Decisión D-12 — precedencia del rol de aplicación."""

    def test_estudiante_sin_membresias(self):
        estudiante = self.make_student("202311346")
        self.assertEqual(estudiante.app_role, AppRole.STUDENT)

    def test_miembro_de_club(self):
        self.make_student("201899001", "Diego", "Ponce")
        club = self.make_club(leader_enrollment="201899001")
        maria = self.make_student("202055789")
        create_membership(student=maria, club=club)
        self.assertEqual(maria.app_role, AppRole.CLUB_MEMBER)

    def test_lider_tiene_precedencia_sobre_miembro(self):
        diego = self.make_student("201899001", "Diego", "Ponce")
        self.make_club(acronym="KOKOA", leader_enrollment="201899001")
        otro = self.make_club(acronym="OTRO")
        create_membership(student=diego, club=otro)
        self.assertEqual(diego.app_role, AppRole.CLUB_LEADER)

    def test_gbp_tiene_la_precedencia_maxima(self):
        gbp = Student.objects.create_user(
            enrollment="GBP-001",
            email="arivas@espol.edu.ec",
            password="x",
            first_name="Ana",
            last_name="Rivas",
            is_gbp_admin=True,
        )
        self.assertEqual(gbp.app_role, AppRole.GBP_ADMIN)


class ClubStatusConstraintTests(ClubTestCase):
    def test_la_base_rechaza_un_club_activo_sin_lider(self):
        """Invariante I-23."""
        club = self.make_club(acronym="MECA", leader_enrollment="202099777")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Club.objects.filter(pk=club.pk).update(status=Club.Status.ACTIVE)


class NoPaoTests(TestCase):
    """Sin período activo, las altas fallan con un error de configuración claro."""

    def test_alta_de_club_sin_pao_activo(self):
        from core.exceptions import ConfigurationError

        faculty = Faculty.objects.get(code="FIEC")
        area = InterestArea.objects.get(name="Tecnología")
        Student.objects.create_user(
            enrollment="201899001",
            email="d@espol.edu.ec",
            password="x",
            first_name="Diego",
            last_name="Ponce",
        )
        self.assertFalse(
            PaoPeriod.objects.filter(status=PaoPeriod.Status.ACTIVE).exists()
        )

        with self.assertRaises(ConfigurationError):
            create_club(
                name="Club",
                acronym="C",
                description="d",
                location="l",
                leader_enrollment="201899001",
                faculty=faculty,
                interest_area_ids=[area.id],
            )
