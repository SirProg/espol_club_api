"""Tests de identidad: matrícula como clave natural y correo institucional."""

import datetime
import io

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import AppRole, Student
from apps.catalogs.models import Faculty


class StudentManagerTests(TestCase):
    def test_crear_estudiante_normaliza_identificadores(self):
        student = Student.objects.create_user(
            enrollment=" 202311346 ",
            email="  KMaldon@espol.edu.ec ",
            password="clave-de-prueba",
            first_name="Kevin",
            last_name="Maldonado",
        )
        self.assertEqual(student.enrollment, "202311346")
        self.assertEqual(student.email, "kmaldon@espol.edu.ec")
        self.assertTrue(student.check_password("clave-de-prueba"))
        self.assertFalse(student.is_verified)

    def test_matricula_obligatoria(self):
        with self.assertRaises(ValueError):
            Student.objects.create_user(
                enrollment="", email="x@espol.edu.ec", password="x"
            )

    def test_superusuario_queda_verificado(self):
        admin = Student.objects.create_superuser(
            enrollment="GBP-000",
            email="admin@espol.edu.ec",
            password="clave",
            first_name="Ana",
            last_name="Rivas",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_verified)

    def test_username_field_es_la_matricula(self):
        self.assertEqual(Student.USERNAME_FIELD, "enrollment")


class StudentValidationTests(TestCase):
    def test_correo_no_institucional_es_rechazado(self):
        student = Student(
            enrollment="202311346",
            email="kevin@gmail.com",
            first_name="Kevin",
            last_name="Maldonado",
        )
        with self.assertRaises(ValidationError) as ctx:
            student.full_clean(exclude=["password"])
        self.assertIn("email", ctx.exception.message_dict)

    def test_correo_institucional_es_aceptado(self):
        student = Student(
            enrollment="202311346",
            email="kmaldon@espol.edu.ec",
            first_name="Kevin",
            last_name="Maldonado",
        )
        student.full_clean(exclude=["password"])

    def test_fecha_de_nacimiento_futura_es_rechazada(self):
        student = Student(
            enrollment="202311346",
            email="kmaldon@espol.edu.ec",
            first_name="Kevin",
            last_name="Maldonado",
            birth_date=timezone.localdate() + datetime.timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            student.full_clean(exclude=["password"])

    def test_redes_sociales_exigen_url_valida(self):
        student = Student(
            enrollment="202311346",
            email="kmaldon@espol.edu.ec",
            first_name="Kevin",
            last_name="Maldonado",
            social_media=[{"network": "GitHub", "link": "no-es-una-url"}],
        )
        with self.assertRaises(ValidationError):
            student.full_clean(exclude=["password"])

    def test_matricula_unica_en_la_base(self):
        """RF-05. La defensa real es el índice único, no el serializer."""
        Student.objects.create_user(
            enrollment="202311346",
            email="kmaldon@espol.edu.ec",
            password="x",
            first_name="Kevin",
            last_name="Maldonado",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Student.objects.create_user(
                    enrollment="202311346",
                    email="otro@espol.edu.ec",
                    password="x",
                    first_name="Otro",
                    last_name="Estudiante",
                )


class StudentDerivedDataTests(TestCase):
    def test_edad_se_deriva_y_no_se_almacena(self):
        hoy = timezone.localdate()
        student = Student(
            enrollment="202311346",
            email="kmaldon@espol.edu.ec",
            first_name="Kevin",
            last_name="Maldonado",
            birth_date=hoy.replace(year=hoy.year - 20),
        )
        self.assertEqual(student.age, 20)
        self.assertFalse(
            any(f.name == "age" for f in Student._meta.get_fields()),
            "La edad no debe existir como campo: se deriva de birth_date.",
        )

    def test_edad_es_none_sin_fecha_de_nacimiento(self):
        student = Student(enrollment="GBP-001", email="ana@espol.edu.ec")
        self.assertIsNone(student.age)

    def test_rol_de_aplicacion_se_deriva(self):
        estudiante = Student(enrollment="202311346", email="k@espol.edu.ec")
        admin = Student(
            enrollment="GBP-001", email="ana@espol.edu.ec", is_gbp_admin=True
        )
        self.assertEqual(estudiante.app_role, AppRole.STUDENT)
        self.assertEqual(admin.app_role, AppRole.GBP_ADMIN)


class FacultyRelationTests(TestCase):
    def test_facultad_es_opcional_para_personal_gbp(self):
        admin = Student.objects.create_user(
            enrollment="GBP-001",
            email="arivas@espol.edu.ec",
            password="x",
            first_name="Ana",
            last_name="Rivas",
            is_gbp_admin=True,
        )
        self.assertIsNone(admin.faculty)

    def test_catalogo_de_facultades_sembrado(self):
        """La migración de datos dejó las 7 facultades provisionales (PPD-01)."""
        self.assertEqual(Faculty.objects.count(), 7)
        self.assertTrue(Faculty.objects.filter(code="FIEC").exists())


class ProvisionGbpAdminCommandTests(TestCase):
    """La salida del comando se descarta para no ensuciar el reporte del runner."""

    def run_command(self, *args):
        call_command(*args, stdout=io.StringIO(), stderr=io.StringIO())

    def test_crea_administrador_gbp(self):
        self.run_command(
            "provision_gbp_admin",
            "GBP-001",
            "--email=arivas@espol.edu.ec",
            "--first-name=Ana",
            "--last-name=Rivas",
            "--password=clave-gbp",
        )
        admin = Student.objects.get(enrollment="GBP-001")
        self.assertTrue(admin.is_gbp_admin)
        self.assertTrue(admin.is_verified)
        self.assertEqual(admin.app_role, AppRole.GBP_ADMIN)

    def test_promueve_una_cuenta_existente(self):
        Student.objects.create_user(
            enrollment="201899001",
            email="dponce@espol.edu.ec",
            password="x",
            first_name="Diego",
            last_name="Ponce",
        )
        self.run_command(
            "provision_gbp_admin",
            "201899001",
            "--email=dponce@espol.edu.ec",
            "--first-name=Diego",
            "--last-name=Ponce",
        )
        self.assertTrue(Student.objects.get(enrollment="201899001").is_gbp_admin)

    def test_rechaza_correo_no_institucional(self):
        with self.assertRaises(CommandError):
            self.run_command(
                "provision_gbp_admin",
                "GBP-002",
                "--email=ana@gmail.com",
                "--first-name=Ana",
                "--last-name=Rivas",
            )
