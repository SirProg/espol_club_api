"""
Tests de la API del constructor de formularios (Etapa 5).

Verifican el contrato HTTP: quién puede tocar qué, y que la inmutabilidad de
RF-24 se manifieste como un 409 con la salida indicada, no como un 500 ni como
una edición silenciosa.
"""

import datetime

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.academic.services import create_pao
from apps.accounts.models import Student
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.models import Role
from apps.clubs.services.clubs import create_club
from apps.clubs.services.memberships import create_membership, set_membership_role
from apps.dynamicforms import responses as response_registry
from apps.dynamicforms.models import Form
from apps.dynamicforms.services import create_form

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


class FormApiTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(
            response_registry.restore_response_counters,
            response_registry.snapshot_response_counters(),
        )
        self.client = APIClient()

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
        self.outsider = self.make_student("202311346", "Kevin", "Maldonado")

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

    def create_membership_form(self):
        return create_form(
            club_id=self.club.pk,
            form_type=Form.FormType.MEMBERSHIP,
            title="Formulario de Inscripción - KOKOA",
            fields=SCHEMA,
        )

    def pretend_has_responses(self, form):
        response_registry.register_response_counter(
            "prueba", lambda candidate: 1 if candidate.pk == form.pk else 0
        )


class FormPermissionTests(FormApiTestCase):
    """RF-53: el constructor es exclusivo del panel del líder."""

    def test_el_lider_puede_crear(self):
        self.authenticate(self.leader)
        response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/forms/",
            {"form_type": "Membership", "title": "Postulación", "fields": SCHEMA},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["version"], 1)

    def test_un_miembro_sin_permiso_no_puede_crear(self):
        self.authenticate(self.member)
        response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/forms/",
            {"form_type": "Membership", "title": "Postulación", "fields": SCHEMA},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_alguien_ajeno_al_club_no_puede_listar(self):
        self.authenticate(self.outsider)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/forms/")
        self.assertEqual(response.status_code, 403)

    def test_sin_autenticar_no_se_accede(self):
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/forms/")
        self.assertEqual(response.status_code, 401)

    def test_un_rol_con_manage_forms_delegado_si_puede(self):
        """El permiso sale del rol, no de ser el líder."""
        vicepresidencia = Role.objects.get(
            club=self.club, role_name="Vicepresidente/a"
        )
        membership = self.member.memberships.get(club=self.club)
        set_membership_role(membership_id=membership.pk, role_id=vicepresidencia.pk)

        self.authenticate(self.member)
        response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/forms/",
            {"form_type": "Membership", "title": "Postulación", "fields": SCHEMA},
            format="json",
        )
        self.assertEqual(response.status_code, 201)


class FormSchemaValidationTests(FormApiTestCase):
    def setUp(self):
        super().setUp()
        self.authenticate(self.leader)

    def post_form(self, fields):
        return self.client.post(
            f"/api/v1/clubs/{self.club.pk}/forms/",
            {"form_type": "Membership", "title": "Postulación", "fields": fields},
            format="json",
        )

    def test_rechaza_un_formulario_sin_campos(self):
        response = self.post_form([])
        self.assertEqual(response.status_code, 400)

    def test_rechaza_un_select_con_una_sola_opcion(self):
        response = self.post_form(
            [
                {
                    "field_id": "q",
                    "label": "Nivel",
                    "type": "select",
                    "options": ["Única"],
                }
            ]
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")

    def test_rechaza_un_tipo_de_campo_inventado(self):
        response = self.post_form(
            [{"field_id": "q", "label": "Firma", "type": "firma_digital"}]
        )
        self.assertEqual(response.status_code, 400)


class FormImmutabilityApiTests(FormApiTestCase):
    """
    La verificación que define la etapa: editar un formulario con respuestas
    devuelve 409 y ofrece versionar (RF-24).
    """

    def setUp(self):
        super().setUp()
        self.form = self.create_membership_form()
        self.authenticate(self.leader)

    def test_sin_respuestas_la_edicion_funciona(self):
        response = self.client.patch(
            f"/api/v1/forms/{self.form.pk}/", {"title": "Nuevo título"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Nuevo título")
        self.assertEqual(response.data["version"], 1)

    def test_con_respuestas_devuelve_409(self):
        self.pretend_has_responses(self.form)

        response = self.client.patch(
            f"/api/v1/forms/{self.form.pk}/", {"title": "No debería"}, format="json"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "form_has_responses")
        self.assertIn("versión nueva", response.data["error"]["message"])

    def test_la_salida_al_409_es_crear_una_version(self):
        self.pretend_has_responses(self.form)

        response = self.client.post(
            f"/api/v1/forms/{self.form.pk}/versions/",
            {"title": "Formulario 2026"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["version"], 2)
        self.assertEqual(response.data["family_id"], self.form.pk)

        self.form.refresh_from_db()
        self.assertFalse(self.form.is_active)

    def test_is_editable_le_dice_al_panel_que_boton_pintar(self):
        sin_respuestas = self.client.get(f"/api/v1/forms/{self.form.pk}/")
        self.assertTrue(sin_respuestas.data["is_editable"])

        self.pretend_has_responses(self.form)
        con_respuestas = self.client.get(f"/api/v1/forms/{self.form.pk}/")
        self.assertFalse(con_respuestas.data["is_editable"])
        self.assertEqual(con_respuestas.data["response_count"], 1)


class MembershipFormAccessTests(FormApiTestCase):
    """RF-25: el formulario de postulación lo ve quien todavía NO es miembro."""

    def setUp(self):
        super().setUp()
        self.form = self.create_membership_form()

    def test_un_estudiante_ajeno_puede_verlo_para_postular(self):
        self.authenticate(self.outsider)
        response = self.client.get(
            f"/api/v1/clubs/{self.club.pk}/forms/membership/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["fields"]), 2)

    def test_no_expone_los_datos_de_gestion(self):
        """
        Quien va a postular no necesita saber cuántas respuestas lleva el
        formulario ni si el líder puede editarlo.
        """
        self.authenticate(self.outsider)
        response = self.client.get(
            f"/api/v1/clubs/{self.club.pk}/forms/membership/"
        )

        self.assertNotIn("response_count", response.data)
        self.assertNotIn("is_editable", response.data)

    def test_sin_formulario_publicado_devuelve_404_explicativo(self):
        Form.objects.all().delete()
        self.authenticate(self.outsider)
        response = self.client.get(
            f"/api/v1/clubs/{self.club.pk}/forms/membership/"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "no_membership_form")

    def test_el_detalle_de_un_formulario_da_solo_el_esquema_a_los_ajenos(self):
        self.authenticate(self.outsider)
        response = self.client.get(f"/api/v1/forms/{self.form.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("fields", response.data)
        self.assertNotIn("response_count", response.data)


class SubmissionValidationApiTests(FormApiTestCase):
    """CU-FO6 expuesto: el cliente puede validar antes de confirmar."""

    def setUp(self):
        super().setUp()
        self.form = self.create_membership_form()
        self.authenticate(self.outsider)

    def test_respuestas_validas(self):
        response = self.client.post(
            f"/api/v1/forms/{self.form.pk}/validate/",
            {"responses": {"q1": "Me interesa el software libre.", "q2": "Intermedio"}},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["valid"])
        self.assertEqual(len(response.data["responses"]), 2)

    def test_falta_un_campo_obligatorio(self):
        response = self.client.post(
            f"/api/v1/forms/{self.form.pk}/validate/",
            {"responses": {"q2": "Intermedio"}},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("q1", response.data["error"]["errors"])

    def test_una_opcion_inventada_es_rechazada(self):
        """El catálogo de opciones no es una sugerencia para el cliente."""
        response = self.client.post(
            f"/api/v1/forms/{self.form.pk}/validate/",
            {"responses": {"q1": "Texto", "q2": "Experto"}},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("q2", response.data["error"]["errors"])
