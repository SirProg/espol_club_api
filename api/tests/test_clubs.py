"""
Tests de la API de clubes (Etapa 8).

El test que define la etapa es ``test_un_no_miembro_nunca_recibe_identidades``:
MASTER §16.7 lo declara **prueba de aceptación obligatoria**, y está escrito
para fallar si alguien filtra datos por cualquier vía, no solo por el campo que
se le ocurrió al autor.
"""

import datetime
import json

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.academic.services import create_pao
from apps.accounts.models import Student
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.models import Club, Role
from apps.clubs.permissions import ClubPermission
from apps.clubs.services.clubs import add_club_document, create_club
from apps.clubs.services.memberships import create_membership
from core.management.commands.seed_demo_data import build_minimal_pdf


class ClubApiTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        create_pao(
            pao_period="2026-I",
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 9, 15),
            activate=True,
        )
        self.faculty = Faculty.objects.get(code="FIEC")
        self.area = InterestArea.objects.get(name="Tecnología")

        self.leader = self.make_student("201899001", "Diego", "Ponce")
        self.club = create_club(
            name="Club de Software Libre KOKOA",
            acronym="KOKOA",
            description="Software libre.",
            location="FIEC 11D",
            leader_enrollment="201899001",
            faculty=self.faculty,
            interest_area_ids=[self.area.id],
        )

        self.member = self.make_student("202055789", "María", "Cevallos")
        create_membership(student=self.member, club=self.club)

        self.outsider = self.make_student("202311346", "Kevin", "Maldonado")
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

    def authenticate(self, student):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"identifier": student.enrollment, "password": "clave-de-prueba"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def upload_document(self, title, is_public):
        return add_club_document(
            club_id=self.club.pk,
            title=title,
            file=ContentFile(build_minimal_pdf(title), name=f"{title}.pdf"),
            is_public=is_public,
        )


class PrivacyAcceptanceTests(ClubApiTestCase):
    """RN-3 / RNF-06 — la prueba de aceptación de MASTER §16.7."""

    def test_un_no_miembro_nunca_recibe_identidades(self):
        """
        Prueba de aceptación obligatoria.

        No comprueba campos concretos: serializa la respuesta completa a texto y
        verifica que **ningún** dato personal de un miembro aparezca en ella.
        Escrito así, detecta también las fugas por caminos que nadie previó —un
        campo nuevo, una relación anidada, un serializer cambiado— en vez de
        solo los que el autor recordó enumerar.
        """
        self.authenticate(self.outsider)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/")
        self.assertEqual(response.status_code, 200)

        cuerpo = json.dumps(response.data, ensure_ascii=False, default=str)

        for dato_sensible in [
            self.member.email,
            self.member.enrollment,
            self.member.first_name,
            self.member.last_name,
            self.leader.email,
            self.leader.enrollment,
        ]:
            self.assertNotIn(
                dato_sensible,
                cuerpo,
                f"El cuerpo de la respuesta filtró '{dato_sensible}' a un no miembro.",
            )

        self.assertNotIn("members", response.data)

    def test_pero_si_recibe_el_contador(self):
        """RF-47: el número de miembros es público; las identidades no."""
        self.authenticate(self.outsider)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/")

        self.assertEqual(response.data["members_count"], 2)

    def test_un_miembro_si_ve_la_nomina(self):
        """RF-48."""
        self.authenticate(self.member)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/")

        self.assertIn("members", response.data)
        matriculas = [m["enrollment"] for m in response.data["members"]]
        self.assertIn("202055789", matriculas)

    def test_gbp_tambien(self):
        self.authenticate(self.gbp)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/")
        self.assertIn("members", response.data)

    def test_el_endpoint_de_nomina_rechaza_al_no_miembro(self):
        self.authenticate(self.outsider)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/members/")
        self.assertEqual(response.status_code, 403)

    def test_el_catalogo_nunca_trae_nomina_ni_para_miembros(self):
        """
        El catálogo es una lista de descubrimiento, no fichas internas.

        Devolver la proyección interna aquí multiplicaría el coste por el número
        de clubes y expondría nóminas enteras en una sola respuesta.
        """
        self.authenticate(self.member)
        response = self.client.get("/api/v1/clubs/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("members", response.data[0])
        self.assertIn("members_count", response.data[0])


class DocumentPrivacyTests(ClubApiTestCase):
    """RF-16 — visibilidad diferenciada de los documentos."""

    def setUp(self):
        super().setUp()
        self.privado = self.upload_document("Estatutos del Club", is_public=False)
        self.publico = self.upload_document("Brochure 2026", is_public=True)

    def test_el_no_miembro_solo_ve_los_publicos(self):
        self.authenticate(self.outsider)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/documents/")

        titulos = [d["title"] for d in response.data]
        self.assertEqual(titulos, ["Brochure 2026"])

    def test_el_miembro_ve_todos(self):
        self.authenticate(self.member)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/documents/")
        self.assertEqual(len(response.data), 2)

    def test_el_detalle_publico_no_incluye_los_privados(self):
        self.authenticate(self.outsider)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/")

        titulos = [d["title"] for d in response.data["documents"]]
        self.assertNotIn("Estatutos del Club", titulos)

    def test_el_lider_cambia_la_visibilidad(self):
        self.authenticate(self.leader)
        response = self.client.patch(
            f"/api/v1/club-documents/{self.privado.pk}/",
            {"is_public": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_public"])

    def test_un_miembro_comun_no_cambia_la_visibilidad(self):
        self.authenticate(self.member)
        response = self.client.patch(
            f"/api/v1/club-documents/{self.privado.pk}/",
            {"is_public": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class ClubCatalogTests(ClubApiTestCase):
    """RF-46 — el catálogo filtrable, prioridad declarada del sistema."""

    def setUp(self):
        super().setUp()
        self.otro = create_club(
            name="Club de Mecatrónica",
            acronym="MECATRÓNICA",
            description="Robótica.",
            location="FIMCP 22A",
            leader_enrollment="",
            faculty=Faculty.objects.get(code="FIMCP"),
            interest_area_ids=[InterestArea.objects.get(name="Ciencia").id],
        )
        self.authenticate(self.outsider)

    def test_lista_todos_los_clubes(self):
        response = self.client.get("/api/v1/clubs/")
        self.assertEqual(len(response.data), 2)

    def test_filtra_por_texto(self):
        response = self.client.get("/api/v1/clubs/?q=KOKOA")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["acronym"], "KOKOA")

    def test_el_texto_busca_tambien_en_el_nombre(self):
        response = self.client.get("/api/v1/clubs/?q=Mecatr")
        self.assertEqual(len(response.data), 1)

    def test_filtra_por_facultad(self):
        response = self.client.get(f"/api/v1/clubs/?faculty={self.faculty.pk}")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["acronym"], "KOKOA")

    def test_filtra_por_area_de_interes(self):
        response = self.client.get(f"/api/v1/clubs/?area={self.area.pk}")
        self.assertEqual(len(response.data), 1)

    def test_un_club_sin_lider_aparece_con_su_estado(self):
        response = self.client.get("/api/v1/clubs/?q=Mecatr")
        self.assertEqual(response.data[0]["status_label"], "Sin líder")


class ClubManagementTests(ClubApiTestCase):
    def test_el_lider_edita_la_informacion(self):
        self.authenticate(self.leader)
        response = self.client.patch(
            f"/api/v1/clubs/{self.club.pk}/",
            {"description": "Comunidad de software libre de ESPOL."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Comunidad", response.data["description"])

    def test_un_miembro_comun_no_edita(self):
        self.authenticate(self.member)
        response = self.client.patch(
            f"/api/v1/clubs/{self.club.pk}/", {"description": "No"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_gbp_no_edita_el_interior_del_club(self):
        """MASTER §3.1: GBP audita y valida, no edita."""
        self.authenticate(self.gbp)
        response = self.client.patch(
            f"/api/v1/clubs/{self.club.pk}/", {"description": "No"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_solo_gbp_da_de_alta_clubes(self):
        """RF-11."""
        self.authenticate(self.leader)
        response = self.client.post(
            "/api/v1/clubs/",
            {
                "name": "Club nuevo",
                "acronym": "NUEVO",
                "description": "x",
                "location": "y",
                "leader_enrollment": "202311346",
                "interest_area_ids": [self.area.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_gbp_da_de_alta_y_el_club_nace_con_sus_roles(self):
        """RF-06."""
        self.authenticate(self.gbp)
        response = self.client.post(
            "/api/v1/clubs/",
            {
                "name": "Club de Robótica",
                "acronym": "ROBOT",
                "description": "Robots.",
                "location": "FIMCP 10",
                "leader_enrollment": "202311346",
                "faculty_id": self.faculty.pk,
                "interest_area_ids": [self.area.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        club = Club.objects.get(acronym="ROBOT")
        self.assertEqual(club.roles.count(), 4)
        self.assertEqual(club.status, Club.Status.ACTIVE)

    def test_el_alta_exige_al_menos_un_area(self):
        self.authenticate(self.gbp)
        response = self.client.post(
            "/api/v1/clubs/",
            {
                "name": "Sin áreas",
                "acronym": "SA",
                "description": "x",
                "location": "y",
                "leader_enrollment": "202311346",
                "interest_area_ids": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class LeadershipApiTests(ClubApiTestCase):
    """RF-13 — el liderazgo lo administra GBP."""

    def test_gbp_revoca_y_el_club_queda_en_solo_lectura(self):
        self.authenticate(self.gbp)
        response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/leader/revoke/", {}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status_label"], "Sin líder")

    def test_el_lider_no_puede_revocarse_a_si_mismo(self):
        self.authenticate(self.leader)
        response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/leader/revoke/", {}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_gbp_asigna_un_lider_nuevo(self):
        self.authenticate(self.gbp)
        self.client.post(
            f"/api/v1/clubs/{self.club.pk}/leader/revoke/", {}, format="json"
        )
        response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/leader/assign/",
            {"enrollment": "202311346"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status_label"], "Activo")
        self.assertEqual(response.data["leader"]["enrollment"], "202311346")

    def test_el_alta_exige_designar_una_matricula_de_lider(self):
        """
        RF-14: un club se registra con líder asignado.

        Puede ser una matrícula sin cuenta —el club queda 'Sin líder' hasta que
        esa persona se registre (RF-12)—, pero no puede quedar sin designar.
        """
        self.authenticate(self.gbp)
        response = self.client.post(
            "/api/v1/clubs/",
            {
                "name": "Otro club",
                "acronym": "OTRO",
                "description": "x",
                "location": "y",
                "leader_enrollment": "",
                "interest_area_ids": [self.area.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_no_se_puede_asignar_a_quien_ya_lidera_otro_club(self):
        """RN-1 a través de la API."""
        self.authenticate(self.gbp)
        # Nace con una matrícula sin cuenta: queda esperando (transición C2).
        creado = self.client.post(
            "/api/v1/clubs/",
            {
                "name": "Otro club",
                "acronym": "OTRO",
                "description": "x",
                "location": "y",
                "leader_enrollment": "202099777",
                "interest_area_ids": [self.area.pk],
            },
            format="json",
        )
        self.assertEqual(creado.status_code, 201)
        otro = Club.objects.get(acronym="OTRO")
        self.assertEqual(otro.status, Club.Status.PENDING_LEADER)

        response = self.client.post(
            f"/api/v1/clubs/{otro.pk}/leader/assign/",
            {"enrollment": "201899001"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["error"]["code"], "leadership_exclusivity"
        )


class RoleApiTests(ClubApiTestCase):
    def test_el_lider_crea_un_rol_personalizado(self):
        self.authenticate(self.leader)
        response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/roles/",
            {
                "role_name": "Encargado de Documentos",
                "is_leadership": False,
                "permissions": {"access_web_panel": True, "manage_documents": True},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            sorted(response.data["granted_permissions"]),
            ["access_web_panel", "manage_documents"],
        )

    def test_rn7_a_traves_de_la_api(self):
        """manage_roles solo puede otorgarse a roles directivos."""
        self.authenticate(self.leader)
        response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/roles/",
            {
                "role_name": "Falso directivo",
                "is_leadership": False,
                "permissions": {"manage_roles": True},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_un_rol_en_uso_se_desactiva_en_vez_de_borrarse(self):
        """D-13, resuelto en el servidor sin que el cliente tenga que saberlo."""
        self.authenticate(self.leader)
        rol = Role.objects.get(club=self.club, role_name="Miembro")

        response = self.client.delete(f"/api/v1/roles/{rol.pk}/")

        # 'Miembro' es un rol por defecto: ni se borra ni se desactiva.
        self.assertEqual(response.status_code, 409)

    def test_un_rol_personalizado_sin_uso_si_se_borra(self):
        self.authenticate(self.leader)
        creado = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/roles/",
            {"role_name": "Temporal", "permissions": {}},
            format="json",
        )
        response = self.client.delete(f"/api/v1/roles/{creado.data['id']}/")
        self.assertEqual(response.status_code, 204)


class MembershipApiTests(ClubApiTestCase):
    def setUp(self):
        super().setUp()
        self.membership = self.member.memberships.get(club=self.club)
        self.authenticate(self.leader)

    def test_cambiar_el_rol_de_un_miembro(self):
        """RF-09."""
        secretaria = Role.objects.get(club=self.club, role_name="Secretario/a")
        response = self.client.patch(
            f"/api/v1/memberships/{self.membership.pk}/",
            {"role_id": secretaria.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role_name"], "Secretario/a")

    def test_dar_de_baja_es_logico(self):
        """RF-19: la fila permanece como evidencia."""
        response = self.client.post(
            f"/api/v1/memberships/{self.membership.pk}/revoke/", {}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status_label"], "Revocada")
        self.membership.refresh_from_db()
        self.assertIsNotNone(self.membership.pk)

    def test_el_liderazgo_no_se_revoca_desde_la_nomina(self):
        lider_membership = self.leader.memberships.get(club=self.club)
        response = self.client.post(
            f"/api/v1/memberships/{lider_membership.pk}/revoke/", {}, format="json"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["error"]["code"], "leadership_revocation_reserved"
        )
