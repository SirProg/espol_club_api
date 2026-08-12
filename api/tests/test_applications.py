"""
Tests de la API de solicitudes (Etapa 6).

Verifican el contrato HTTP y, sobre todo, la separación de audiencias: el mismo
recurso lo consumen el estudiante y el líder con permisos opuestos, y una fuga
en cualquiera de las dos direcciones sería una fuga de datos personales (RN-3).
"""

import datetime

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.academic.services import create_pao
from apps.accounts.models import Student
from apps.applications.models import MembershipApplication
from apps.applications.services import submit_application
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.models import Membership
from apps.clubs.services.clubs import create_club
from apps.dynamicforms.models import Form
from apps.dynamicforms.services import create_form

SCHEMA = [
    {
        "field_id": "q1",
        "label": "¿Por qué quieres unirte?",
        "type": "textarea",
        "required": True,
        "order": 1,
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


class ApplicationApiTestCase(TestCase):
    def setUp(self):
        cache.clear()
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
        self.form = create_form(
            club_id=self.club.pk,
            form_type=Form.FormType.MEMBERSHIP,
            title="Formulario de Inscripción - KOKOA",
            fields=SCHEMA,
        )
        self.kevin = self.make_student("202311346", "Kevin", "Maldonado")
        self.lucia = self.make_student("202144556", "Lucía", "Torres")

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

    def post_application(self, responses=None):
        return self.client.post(
            f"/api/v1/clubs/{self.club.pk}/applications/",
            {"responses": responses or VALID_RESPONSES},
            format="json",
        )


class StudentFlowTests(ApplicationApiTestCase):
    def setUp(self):
        super().setUp()
        self.authenticate(self.kevin)

    def test_postular_devuelve_201(self):
        response = self.post_application()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "Pending")
        self.assertEqual(response.data["status_label"], "Pendiente")
        self.assertEqual(len(response.data["answers"]), 2)

    def test_can_apply_antes_y_despues(self):
        antes = self.client.get(
            f"/api/v1/clubs/{self.club.pk}/applications/can-apply/"
        )
        self.assertTrue(antes.data["allowed"])

        self.post_application()

        despues = self.client.get(
            f"/api/v1/clubs/{self.club.pk}/applications/can-apply/"
        )
        self.assertFalse(despues.data["allowed"])
        self.assertEqual(
            despues.data["reason"], "Ya tienes una solicitud pendiente en este club."
        )

    def test_duplicar_devuelve_409(self):
        self.post_application()
        segunda = self.post_application()

        self.assertEqual(segunda.status_code, 409)
        self.assertEqual(segunda.data["error"]["code"], "already_pending")

    def test_respuestas_invalidas_devuelven_400_por_campo(self):
        response = self.post_application(responses={"q1": "Texto", "q2": "Experto"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("q2", response.data["error"]["errors"])

    def test_el_historial_propio_solo_muestra_las_suyas(self):
        self.post_application()
        submit_application(
            student=self.lucia, club_id=self.club.pk, responses=VALID_RESPONSES
        )

        response = self.client.get("/api/v1/students/me/applications/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["club_acronym"], "KOKOA")

    def test_un_estudiante_no_ve_la_bandeja_del_club(self):
        """RN-3: la bandeja trae datos personales de otros postulantes."""
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/applications/")
        self.assertEqual(response.status_code, 403)

    def test_un_estudiante_no_puede_resolver_solicitudes(self):
        application = submit_application(
            student=self.lucia, club_id=self.club.pk, responses=VALID_RESPONSES
        )
        response = self.client.post(
            f"/api/v1/applications/{application.pk}/approve/", {}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_no_puede_aprobar_su_propia_solicitud(self):
        response = self.post_application()
        application_id = response.data["id"]

        resolucion = self.client.post(
            f"/api/v1/applications/{application_id}/approve/", {}, format="json"
        )
        self.assertEqual(resolucion.status_code, 403)


class LeaderInboxTests(ApplicationApiTestCase):
    def setUp(self):
        super().setUp()
        self.application = submit_application(
            student=self.kevin, club_id=self.club.pk, responses=VALID_RESPONSES
        )
        self.authenticate(self.leader)

    def test_la_bandeja_trae_las_respuestas_emparejadas_con_su_pregunta(self):
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/applications/")

        self.assertEqual(response.status_code, 200)
        answers = response.data[0]["answers"]
        self.assertEqual(answers[0]["label"], "¿Por qué quieres unirte?")
        self.assertEqual(answers[1]["answer"], "Intermedio")

    def test_la_bandeja_muestra_los_datos_del_postulante(self):
        """Vista interna: quien lee tiene manage_members."""
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/applications/")
        student = response.data[0]["student"]

        self.assertEqual(student["enrollment"], "202311346")
        self.assertIn("email", student)

    def test_filtra_por_estado(self):
        response = self.client.get(
            f"/api/v1/clubs/{self.club.pk}/applications/?status=Approved"
        )
        self.assertEqual(len(response.data), 0)

    def test_aprobar_crea_la_membresia(self):
        response = self.client.post(
            f"/api/v1/applications/{self.application.pk}/approve/", {}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "Approved")
        self.assertIsNotNone(response.data["resulting_membership"])
        self.assertTrue(
            Membership.objects.filter(student=self.kevin, club=self.club).exists()
        )

    def test_rechazar_sin_feedback_devuelve_400(self):
        """RN-5."""
        response = self.client.post(
            f"/api/v1/applications/{self.application.pk}/reject/", {}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_rechazar_con_feedback_en_blanco_tambien_falla(self):
        response = self.client.post(
            f"/api/v1/applications/{self.application.pk}/reject/",
            {"feedback": "     "},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rechazar_con_feedback_funciona(self):
        response = self.client.post(
            f"/api/v1/applications/{self.application.pk}/reject/",
            {"feedback": "Cupo lleno este PAO; vuelve a postular el próximo período."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "Rejected")
        self.assertIn("Cupo lleno", response.data["leader_feedback"])
        self.assertEqual(response.data["resolved_by_name"], "Diego Ponce")

    def test_resolver_dos_veces_devuelve_409(self):
        self.client.post(
            f"/api/v1/applications/{self.application.pk}/approve/", {}, format="json"
        )
        segunda = self.client.post(
            f"/api/v1/applications/{self.application.pk}/approve/", {}, format="json"
        )

        self.assertEqual(segunda.status_code, 409)
        self.assertEqual(
            segunda.data["error"]["code"], "application_already_resolved"
        )

    def test_una_accion_inventada_no_llega_a_la_vista(self):
        """
        La ruta restringe la acción a approve|reject.

        Con un <str:action> libre, /applications/1/borrar/ habría entrado en la
        vista y caído en la rama de rechazo por descarte.
        """
        response = self.client.post(
            f"/api/v1/applications/{self.application.pk}/borrar/", {}, format="json"
        )
        self.assertEqual(response.status_code, 404)


class ReapplicationTests(ApplicationApiTestCase):
    """RF-29 de extremo a extremo: rechazo y reenvío inmediato."""

    def test_tras_el_rechazo_puede_volver_a_postular_sin_esperar(self):
        primera = submit_application(
            student=self.kevin, club_id=self.club.pk, responses=VALID_RESPONSES
        )

        self.authenticate(self.leader)
        self.client.post(
            f"/api/v1/applications/{primera.pk}/reject/",
            {"feedback": "Cupo lleno este PAO."},
            format="json",
        )

        self.authenticate(self.kevin)
        elegibilidad = self.client.get(
            f"/api/v1/clubs/{self.club.pk}/applications/can-apply/"
        )
        self.assertTrue(elegibilidad.data["allowed"])

        segunda = self.post_application()
        self.assertEqual(segunda.status_code, 201)
        self.assertEqual(MembershipApplication.objects.count(), 2)


class FormLockIntegrationTests(ApplicationApiTestCase):
    """RF-24 con el contador real, a través de la API."""

    def test_una_solicitud_bloquea_la_edicion_del_formulario(self):
        self.authenticate(self.leader)
        antes = self.client.patch(
            f"/api/v1/forms/{self.form.pk}/", {"title": "Editable"}, format="json"
        )
        self.assertEqual(antes.status_code, 200)

        submit_application(
            student=self.kevin, club_id=self.club.pk, responses=VALID_RESPONSES
        )

        despues = self.client.patch(
            f"/api/v1/forms/{self.form.pk}/", {"title": "Ya no"}, format="json"
        )
        self.assertEqual(despues.status_code, 409)
        self.assertEqual(despues.data["error"]["code"], "form_has_responses")
