"""
Tests de la API de eventos (Etapa 7).

Verifican el contrato HTTP de las tres audiencias —estudiante, líder y staff— y
que el escaneo devuelva códigos distinguibles: la app del staff necesita saber
si mostrar "ya registró asistencia" o "no estás autorizado", y ambos no pueden
ser el mismo 400 genérico.
"""

import datetime

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academic.services import create_pao
from apps.accounts.models import Student
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.services.clubs import create_club
from apps.clubs.services.memberships import create_membership
from apps.dynamicforms.models import Form
from apps.dynamicforms.services import create_form
from apps.events.models import Event, EventAttendance
from apps.events.services.events import create_event, set_event_staff
from apps.events.services.registration import register_for_event

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


class EventApiTestCase(TestCase):
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
            form_type=Form.FormType.EVENT,
            title="Registro - Taller de Git",
            fields=EVENT_SCHEMA,
        )

        now = timezone.localtime()
        self.event = create_event(
            club_id=self.club.pk,
            event_name="CLI - Comandos Básicos Parte #1",
            mode=Event.Mode.ONLINE,
            planned_date=now.date(),
            planned_hour=now.time().replace(microsecond=0),
            end_datetime=now + datetime.timedelta(hours=2),
            planned_place="Aula virtual",
            registration_form_id=self.form.pk,
        )

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

    def authenticate(self, student):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"identifier": student.enrollment, "password": "clave-de-prueba"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def register(self, student):
        return register_for_event(
            student=student, event_id=self.event.pk, responses={"f1": "Intermedio"}
        )

    def assign_staff(self, student):
        set_event_staff(
            event_id=self.event.pk, student_ids=[student.pk], assigned_by=self.leader
        )


class EventDiscoveryTests(EventApiTestCase):
    def test_el_catalogo_incluye_los_members_only(self):
        """RF-31."""
        self.event.visibility = Event.Visibility.MEMBERS_ONLY
        self.event.save(update_fields=["visibility"])

        self.authenticate(self.kevin)
        response = self.client.get("/api/v1/events/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["visibility_label"], "Solo miembros")

    def test_el_detalle_trae_el_veredicto_de_registro(self):
        self.authenticate(self.kevin)
        response = self.client.get(f"/api/v1/events/{self.event.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_register"]["can_register"])

    def test_el_estudiante_no_ve_la_tabla_de_metricas_del_club(self):
        self.authenticate(self.kevin)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/events/")
        self.assertEqual(response.status_code, 403)

    def test_el_lider_si_ve_las_metricas(self):
        """RF-38."""
        self.register(self.kevin)
        self.authenticate(self.leader)
        response = self.client.get(f"/api/v1/clubs/{self.club.pk}/events/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["stats"], {"registered": 1, "attended": 0})


class EventRegistrationApiTests(EventApiTestCase):
    def setUp(self):
        super().setUp()
        self.authenticate(self.kevin)

    def test_inscribirse_devuelve_la_credencial(self):
        response = self.client.post(
            f"/api/v1/events/{self.event.pk}/register/",
            {"responses": {"f1": "Intermedio"}},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["qr_token"])
        self.assertEqual(response.data["qr_status_label"], "Activa")

    def test_inscribirse_dos_veces_devuelve_409(self):
        self.client.post(
            f"/api/v1/events/{self.event.pk}/register/",
            {"responses": {"f1": "Intermedio"}},
            format="json",
        )
        segunda = self.client.post(
            f"/api/v1/events/{self.event.pk}/register/",
            {"responses": {"f1": "Avanzado"}},
            format="json",
        )

        self.assertEqual(segunda.status_code, 409)
        self.assertEqual(segunda.data["error"]["code"], "already_registered")

    def test_respuestas_invalidas_devuelven_400(self):
        response = self.client.post(
            f"/api/v1/events/{self.event.pk}/register/",
            {"responses": {"f1": "Experto"}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("f1", response.data["error"]["errors"])

    def test_las_credenciales_propias_incluyen_el_token(self):
        self.client.post(
            f"/api/v1/events/{self.event.pk}/register/",
            {"responses": {"f1": "Intermedio"}},
            format="json",
        )
        response = self.client.get("/api/v1/students/me/registrations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]["qr_token"])

    def test_solo_se_ven_las_credenciales_propias(self):
        self.register(self.maria)
        response = self.client.get("/api/v1/students/me/registrations/")
        self.assertEqual(len(response.data), 0)


class StaffApiTests(EventApiTestCase):
    def test_el_lider_asigna_staff(self):
        self.authenticate(self.leader)
        response = self.client.put(
            f"/api/v1/events/{self.event.pk}/staff/",
            {"student_ids": [self.maria.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["enrollment"], "202055789")

    def test_no_se_puede_asignar_a_alguien_ajeno_al_club(self):
        self.authenticate(self.leader)
        response = self.client.put(
            f"/api/v1/events/{self.event.pk}/staff/",
            {"student_ids": [self.kevin.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["error"]["code"], "staff_must_be_active_member"
        )

    def test_un_miembro_comun_no_asigna_staff(self):
        self.authenticate(self.maria)
        response = self.client.put(
            f"/api/v1/events/{self.event.pk}/staff/",
            {"student_ids": [self.maria.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class ScanApiTests(EventApiTestCase):
    """
    El escaneo desde la app del staff (pantalla 13).

    Cada motivo de rechazo tiene su propio código: la app decide con él si
    ofrece reintentar, avisar al líder o pasar a la siguiente persona.
    """

    def setUp(self):
        super().setUp()
        self.registration = self.register(self.kevin)
        self.assign_staff(self.maria)

    def scan(self, token=None):
        return self.client.post(
            "/api/v1/attendance/scan/",
            {"qr_token": token if token is not None else self.registration.qr_token},
            format="json",
        )

    def test_escaneo_valido(self):
        self.authenticate(self.maria)
        response = self.scan()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Asistencia registrada correctamente.")
        self.assertEqual(response.data["student_name"], "Kevin Maldonado")
        self.assertEqual(EventAttendance.objects.count(), 1)

    def test_reescaneo_devuelve_409_con_su_codigo(self):
        self.authenticate(self.maria)
        self.scan()
        segunda = self.scan()

        self.assertEqual(segunda.status_code, 409)
        self.assertEqual(segunda.data["error"]["code"], "qr_already_used")
        self.assertEqual(
            segunda.data["error"]["message"], "Esta credencial ya registró asistencia."
        )

    def test_token_vacio_devuelve_su_propio_mensaje(self):
        self.authenticate(self.maria)
        response = self.scan(token="")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["error"]["message"], "Ingresa o escanea un código."
        )

    def test_token_desconocido(self):
        self.authenticate(self.maria)
        response = self.scan(token="qr-falsificado")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "unknown_qr_token")

    def test_quien_no_es_staff_recibe_403(self):
        """RF-35: el motivo debe distinguirse de una credencial inválida."""
        andres = self.make_student("201977882", "Andrés", "Vera")
        create_membership(student=andres, club=self.club)
        self.authenticate(andres)

        response = self.scan()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"]["code"], "not_event_staff")
        self.assertEqual(EventAttendance.objects.count(), 0)

    def test_el_propio_estudiante_no_puede_autoescanearse(self):
        self.authenticate(self.kevin)
        response = self.scan()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(EventAttendance.objects.count(), 0)


class RegistrationLogTests(EventApiTestCase):
    """Bitácora del club (pantalla 34, PPD-04)."""

    def setUp(self):
        super().setUp()
        self.register(self.kevin)
        self.register(self.maria)

    def test_el_lider_ve_la_bitacora_del_evento_indicado(self):
        self.authenticate(self.leader)
        response = self.client.get(
            f"/api/v1/events/{self.event.pk}/registrations/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["event"]["id"], self.event.pk)
        self.assertEqual(len(response.data["registrations"]), 2)
        self.assertEqual(response.data["summary"]["registered"], 2)

    def test_la_bitacora_trae_matricula_y_fecha_de_registro(self):
        self.authenticate(self.leader)
        response = self.client.get(
            f"/api/v1/events/{self.event.pk}/registrations/"
        )
        fila = response.data["registrations"][0]

        self.assertIn("enrollment", fila)
        self.assertIn("registered_at", fila)
        self.assertEqual(fila["attendance_status_label"], "Inscrito")

    def test_las_respuestas_solo_si_se_piden(self):
        """La bitácora se usa para pasar lista, no para leer formularios."""
        self.authenticate(self.leader)

        sin = self.client.get(f"/api/v1/events/{self.event.pk}/registrations/")
        self.assertNotIn("responses", sin.data["registrations"][0])

        con = self.client.get(
            f"/api/v1/events/{self.event.pk}/registrations/?responses=true"
        )
        self.assertIn("responses", con.data["registrations"][0])

    def test_un_estudiante_no_ve_la_bitacora(self):
        """Trae matrículas de otros: es la vista interna (RN-3)."""
        self.authenticate(self.kevin)
        response = self.client.get(
            f"/api/v1/events/{self.event.pk}/registrations/"
        )
        self.assertEqual(response.status_code, 403)
