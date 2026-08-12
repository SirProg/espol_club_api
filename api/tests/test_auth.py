"""
Tests de la API de autenticación (Etapa 4).

Se prueban contra los endpoints reales, no contra los servicios: lo que se
quiere verificar aquí es el contrato HTTP —códigos de estado, formato del error,
qué se filtra y qué no—, que es justo lo que los tests de dominio no cubren.
"""

import datetime

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.academic.services import create_pao
from apps.accounts.models import Student
from apps.accounts.services import register_student
from apps.accounts.tokens import build_verification_token
from apps.catalogs.models import Faculty, InterestArea
from apps.clubs.models import Club, Membership
from apps.clubs.services.clubs import create_club


class ApiTestCase(TestCase):
    def setUp(self):
        # El throttle de DRF cuenta peticiones en la caché del proceso, que NO
        # se revierte entre tests como sí lo hace la base. Sin limpiarla, los
        # tests se agotan las cuotas entre sí y empiezan a fallar con 429 —o
        # peor, con un 401 despistante cuando el login throttled no deja
        # credenciales. El límite se prueba aparte, en ThrottlingTests.
        cache.clear()

        self.client = APIClient()
        self.pao = create_pao(
            pao_period="2026-I",
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 9, 15),
            activate=True,
        )
        self.faculty = Faculty.objects.get(code="FIEC")

    def make_verified_student(self, enrollment="201899001", password="lider123"):
        student = Student.objects.create_user(
            enrollment=enrollment,
            email=f"{enrollment.lower()}@espol.edu.ec",
            password=password,
            first_name="Diego",
            last_name="Ponce",
            is_verified=True,
        )
        return student

    def login(self, identifier, password):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"identifier": identifier, "password": password},
            format="json",
        )
        if response.status_code == 200:
            self.client.credentials(
                HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
            )
        return response


class RegistrationTests(ApiTestCase):
    payload = {
        "enrollment": "202311346",
        "first_name": "Kevin",
        "last_name": "Maldonado",
        "email": "kmaldon@espol.edu.ec",
        "password": "clave-segura-2026",
        "password_confirm": "clave-segura-2026",
        "career": "Computación",
        "semester": 6,
    }

    def test_registro_exitoso_envia_correo_y_deja_la_cuenta_sin_verificar(self):
        response = self.client.post(
            "/api/v1/auth/register/", {**self.payload, "faculty": "FIEC"}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        student = Student.objects.get(enrollment="202311346")
        self.assertFalse(student.is_verified)
        self.assertEqual(student.faculty, self.faculty)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verific", mail.outbox[0].subject.lower())

    def test_rechaza_correo_no_institucional(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {**self.payload, "email": "kevin@gmail.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("email", response.data["error"]["errors"])

    def test_rechaza_matricula_duplicada(self):
        """RF-05."""
        self.make_verified_student(enrollment="202311346")
        response = self.client.post(
            "/api/v1/auth/register/", self.payload, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("enrollment", response.data["error"]["errors"])

    def test_rechaza_contrasenas_distintas(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {**self.payload, "password_confirm": "otra-cosa-distinta"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_no_permite_autoasignarse_el_perfil_de_gbp(self):
        """
        PPD-02: el perfil institucional no se autoconcede.

        Aunque el payload traiga la bandera, el serializer no la conoce y el
        servicio no la acepta como argumento.
        """
        response = self.client.post(
            "/api/v1/auth/register/",
            {**self.payload, "is_gbp_admin": True, "is_verified": True},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        student = Student.objects.get(enrollment="202311346")
        self.assertFalse(student.is_gbp_admin)
        self.assertFalse(student.is_verified)


class LoginTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.student = self.make_verified_student()

    def test_login_con_matricula(self):
        response = self.login("201899001", "lider123")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_con_correo(self):
        """MASTER §16.4: el identificador puede ser matrícula o correo."""
        response = self.login("201899001@espol.edu.ec", "lider123")
        self.assertEqual(response.status_code, 200)

    def test_credenciales_incorrectas_devuelven_401(self):
        response = self.login("201899001", "incorrecta")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "invalid_credentials")

    def test_cuenta_inexistente_da_el_mismo_mensaje_que_contrasena_mala(self):
        """No debe servir para averiguar qué matrículas están registradas."""
        inexistente = self.login("209999999", "loquesea")
        mala_clave = self.login("201899001", "incorrecta")

        self.assertEqual(inexistente.status_code, mala_clave.status_code)
        self.assertEqual(
            inexistente.data["error"]["message"], mala_clave.data["error"]["message"]
        )

    def test_cuenta_sin_verificar_no_inicia_sesion(self):
        """RF-01."""
        Student.objects.create_user(
            enrollment="202144556",
            email="ltorres@espol.edu.ec",
            password="clave-de-prueba",
            first_name="Lucía",
            last_name="Torres",
        )
        response = self.login("202144556", "clave-de-prueba")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"]["code"], "account_not_verified")

    def test_refresh_entrega_un_access_nuevo(self):
        login = self.login("201899001", "lider123")
        response = self.client.post(
            "/api/v1/auth/refresh/", {"refresh": login.data["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)


class SessionTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.diego = self.make_verified_student()
        self.area = InterestArea.objects.get(name="Tecnología")
        self.club = create_club(
            name="Club de Software Libre KOKOA",
            acronym="KOKOA",
            description="Software libre.",
            location="FIEC 11D",
            leader_enrollment="201899001",
            faculty=self.faculty,
            interest_area_ids=[self.area.id],
        )

    def test_sin_token_devuelve_401_con_el_formato_de_error(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.data)
        self.assertIn("code", response.data["error"])

    def test_devuelve_el_rol_derivado_y_los_permisos_del_club(self):
        self.login("201899001", "lider123")
        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["app_role"], "Club Leader")
        self.assertEqual(response.data["led_club_id"], self.club.pk)

        membership = response.data["memberships"][0]
        self.assertEqual(membership["club_acronym"], "KOKOA")
        self.assertIn("manage_members", membership["permissions"])

    def test_el_rol_se_recalcula_tras_revocar_el_liderazgo(self):
        """
        El rol sale del estado actual, no del token.

        Con el rol congelado en el JWT, alguien a quien acaban de revocar
        seguiría viéndose como líder hasta que caducara su token.
        """
        login = self.login("201899001", "lider123")
        token = login.data["access"]

        from apps.clubs.services.leadership import revoke_leader

        revoke_leader(club_id=self.club.pk)

        # Mismo token de antes de la revocación.
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.data["app_role"], "Student")
        self.assertIsNone(response.data["led_club_id"])


class ProfileTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.make_verified_student()
        self.login("201899001", "lider123")

    def test_edita_solo_los_campos_permitidos(self):
        """F-07."""
        response = self.client.patch(
            "/api/v1/students/me/",
            {
                "description": "Enfocado en software libre.",
                "skills": ["Python", "SQL"],
                "enrollment": "999999999",
                "email": "otro@espol.edu.ec",
                "semester": 99,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        student = Student.objects.get(pk=response.data["id"])
        self.assertEqual(student.description, "Enfocado en software libre.")
        self.assertEqual(student.skills, ["Python", "SQL"])
        # Los datos institucionales no se movieron.
        self.assertEqual(student.enrollment, "201899001")
        self.assertEqual(student.email, "201899001@espol.edu.ec")

    def test_rechaza_una_red_social_con_enlace_invalido(self):
        response = self.client.patch(
            "/api/v1/students/me/",
            {"social_media": [{"network": "GitHub", "link": "no-es-url"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class EmailVerificationTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.student = register_student(
            enrollment="202144556",
            first_name="Lucía",
            last_name="Torres",
            email="ltorres@espol.edu.ec",
            password="clave-segura-2026",
        )
        mail.outbox.clear()

    def test_verifica_con_un_token_valido(self):
        token = build_verification_token(self.student)
        response = self.client.post(
            "/api/v1/auth/verify/", {"token": token}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_verified)

    def test_token_manipulado_es_rechazado(self):
        response = self.client.post(
            "/api/v1/auth/verify/", {"token": "esto-no-es-un-token"}, format="json"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["error"]["code"], "invalid_verification_token"
        )

    def test_verificar_dos_veces_no_falla(self):
        token = build_verification_token(self.student)
        self.client.post("/api/v1/auth/verify/", {"token": token}, format="json")
        segunda = self.client.post(
            "/api/v1/auth/verify/", {"token": token}, format="json"
        )
        self.assertEqual(segunda.status_code, 200)

    def test_el_reenvio_no_revela_si_el_correo_existe(self):
        conocido = self.client.post(
            "/api/v1/auth/verify/resend/",
            {"email": "ltorres@espol.edu.ec"},
            format="json",
        )
        desconocido = self.client.post(
            "/api/v1/auth/verify/resend/",
            {"email": "nadie@espol.edu.ec"},
            format="json",
        )

        self.assertEqual(conocido.status_code, desconocido.status_code)
        self.assertEqual(conocido.data, desconocido.data)


class DeferredLeadershipOnVerificationTests(ApiTestCase):
    """
    RF-12 de extremo a extremo, a través del bus de eventos.

    Es el primer consumidor real de ``core.events``: verificar la cuenta emite
    ``student.verified`` y ``clubs`` reacciona activando el club que esperaba
    esa matrícula.
    """

    def setUp(self):
        super().setUp()
        self.club = create_club(
            name="Club de Mecatrónica",
            acronym="MECATRÓNICA",
            description="Robótica.",
            location="FIMCP 22A",
            leader_enrollment="202099777",
            faculty=self.faculty,
            interest_area_ids=[InterestArea.objects.get(name="Tecnología").id],
        )
        self.assertEqual(self.club.status, Club.Status.PENDING_LEADER)

    def test_al_verificarse_la_matricula_el_club_se_activa(self):
        student = register_student(
            enrollment="202099777",
            first_name="Ana",
            last_name="Vera",
            email="avera@espol.edu.ec",
            password="clave-segura-2026",
        )
        token = build_verification_token(student)

        # Sin capturar los callbacks de commit, el handler no correría y este
        # test pasaría en verde sin haber probado nada.
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/v1/auth/verify/", {"token": token}, format="json")

        self.club.refresh_from_db()
        self.assertEqual(self.club.status, Club.Status.ACTIVE)
        self.assertEqual(self.club.leader, student)
        self.assertTrue(
            Membership.objects.filter(
                student=student,
                club=self.club,
                is_leadership=True,
                status=Membership.Status.ACTIVE,
            ).exists()
        )

    def test_el_club_sigue_pendiente_para_otra_matricula(self):
        student = register_student(
            enrollment="202311346",
            first_name="Kevin",
            last_name="Maldonado",
            email="kmaldon@espol.edu.ec",
            password="clave-segura-2026",
        )
        token = build_verification_token(student)

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/v1/auth/verify/", {"token": token}, format="json")

        self.club.refresh_from_db()
        self.assertEqual(self.club.status, Club.Status.PENDING_LEADER)


class PasswordResetTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.student = self.make_verified_student()
        mail.outbox.clear()

    def test_solicitud_envia_correo_y_no_revela_si_existe(self):
        conocido = self.client.post(
            "/api/v1/auth/password-reset/",
            {"email": "201899001@espol.edu.ec"},
            format="json",
        )
        self.assertEqual(conocido.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        desconocido = self.client.post(
            "/api/v1/auth/password-reset/",
            {"email": "nadie@espol.edu.ec"},
            format="json",
        )
        self.assertEqual(conocido.data, desconocido.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_confirma_y_cambia_la_contrasena(self):
        from apps.accounts.tokens import build_password_reset_pair

        uid, token = build_password_reset_pair(self.student)
        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": uid,
                "token": token,
                "password": "nueva-clave-2026",
                "password_confirm": "nueva-clave-2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.login("201899001", "nueva-clave-2026").status_code, 200)

    def test_el_enlace_no_sirve_dos_veces(self):
        from apps.accounts.tokens import build_password_reset_pair

        uid, token = build_password_reset_pair(self.student)
        payload = {
            "uid": uid,
            "token": token,
            "password": "nueva-clave-2026",
            "password_confirm": "nueva-clave-2026",
        }
        self.client.post(
            "/api/v1/auth/password-reset/confirm/", payload, format="json"
        )
        segunda = self.client.post(
            "/api/v1/auth/password-reset/confirm/", payload, format="json"
        )

        self.assertEqual(segunda.status_code, 409)
        self.assertEqual(segunda.data["error"]["code"], "invalid_reset_token")


class CatalogsTests(ApiTestCase):
    def test_los_catalogos_son_publicos(self):
        """El formulario de registro los necesita antes de existir la cuenta."""
        response = self.client.get("/api/v1/catalogs/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["faculties"]), 7)
        self.assertEqual(len(response.data["interest_areas"]), 8)
        self.assertEqual(response.data["active_pao"], "2026-I")


class ThrottlingTests(ApiTestCase):
    """
    Los puntos de entrada anónimos están limitados.

    El registro y el login son lo que un atacante prueba en masa: uno para
    enumerar matrículas, el otro para adivinar contraseñas.
    """

    def test_el_login_se_bloquea_tras_agotar_la_cuota(self):
        """
        Se prueba contra la cuota **real** de settings, no contra una inventada.

        ``override_settings(REST_FRAMEWORK=...)`` no serviría aquí: DRF enlaza
        ``SimpleRateThrottle.THROTTLE_RATES`` como atributo de clase al importar
        el módulo, así que cambiar el setting después no altera el límite y el
        test pasaría en verde sin haber probado nada.
        """
        from rest_framework.throttling import SimpleRateThrottle

        # SimpleRateThrottle no se puede instanciar sin scope, así que la cuota
        # se lee de la configuración tal cual: "10/min" -> 10.
        limite = int(SimpleRateThrottle.THROTTLE_RATES["auth_login"].split("/")[0])
        self.make_verified_student()

        for _ in range(limite):
            self.login("201899001", "incorrecta")

        bloqueado = self.login("201899001", "lider123")

        self.assertEqual(bloqueado.status_code, 429)
        self.assertEqual(bloqueado.data["error"]["code"], "throttled")
        self.assertIn("Retry-After", bloqueado.headers)


class ApiRootTests(TestCase):
    """
    El índice del servicio.

    Existe porque un 404 en la raíz se lee como "el servicio está caído" aunque
    la API funcione perfectamente. Los tests valen sobre todo como red de
    seguridad: el índice construye sus enlaces con ``reverse()``, así que si
    alguien renombra una ruta, esto falla en vez de devolver una URL rota.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_la_raiz_identifica_el_servicio(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["service"], "ESPOLCLUB API")
        self.assertEqual(response.data["status"], "ok")

    def test_la_raiz_es_publica(self):
        """Sin autenticar: es una tarjeta de presentación, no un recurso."""
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/").status_code, 200)

    def test_el_indice_resuelve_todas_sus_rutas(self):
        response = self.client.get("/api/v1/")

        self.assertEqual(response.status_code, 200)
        for grupo in ["auth", "student", "discovery", "gbp"]:
            self.assertIn(grupo, response.data)
        self.assertTrue(response.data["auth"]["login"].endswith("/api/v1/auth/login/"))

    def test_el_indice_solo_contiene_urls_propias(self):
        """
        El índice publica rutas, no datos.

        Comprobar que no aparezca la palabra "password" sería un mal test:
        ``password_reset`` es un nombre de endpoint legítimo. Lo que sí importa
        es que todo valor enlazable apunte a este mismo servicio y que ninguno
        traiga datos de la base.
        """
        response = self.client.get("/api/v1/")

        def urls(nodo):
            if isinstance(nodo, dict):
                for valor in nodo.values():
                    yield from urls(valor)
            elif isinstance(nodo, str) and nodo.startswith("http"):
                yield nodo

        encontradas = list(urls(response.data))
        self.assertGreater(len(encontradas), 10)
        for url in encontradas:
            self.assertTrue(
                url.startswith("http://testserver/api/v1/"),
                f"El índice enlaza fuera del servicio: {url}",
            )
