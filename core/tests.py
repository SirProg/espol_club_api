"""Tests de los contratos compartidos y del sembrado de datos."""

import io
import re
import shutil
import tempfile

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase, override_settings

from core import events
from core.exceptions import BusinessRuleViolation, DomainError
from core.management.commands.seed_demo_data import build_minimal_pdf
from core.services import command, extract_constraint_name, translate_integrity_error


class ConstraintNameExtractionTests(TestCase):
    """
    Los nombres se extraen con precisión, no por subcadena.

    Este test existe porque la primera versión buscaba el nombre registrado
    dentro del texto del error y nunca acertaba: MariaDB nombra el índice de un
    campo unique=True según la columna, no según tabla_columna. El fallo era
    silencioso — el usuario recibía el mensaje genérico.
    """

    def test_duplicado_mariadb(self):
        exc = IntegrityError(1062, "Duplicate entry 'GBP-000' for key 'enrollment'")
        self.assertEqual(extract_constraint_name(exc), "enrollment")

    def test_duplicado_mysql8_con_prefijo_de_tabla(self):
        exc = IntegrityError(
            1062, "Duplicate entry '1' for key 'academic_paoperiod.uniq_single_active_pao'"
        )
        self.assertEqual(extract_constraint_name(exc), "uniq_single_active_pao")

    def test_check_mariadb(self):
        exc = IntegrityError(
            4025,
            "CONSTRAINT `chk_pao_end_after_start` failed for `espolclub`.`academic_paoperiod`",
        )
        self.assertEqual(extract_constraint_name(exc), "chk_pao_end_after_start")

    def test_check_mysql8(self):
        exc = IntegrityError(
            3819, "Check constraint 'chk_pao_end_after_start' is violated."
        )
        self.assertEqual(extract_constraint_name(exc), "chk_pao_end_after_start")

    def test_error_no_reconocido_devuelve_none(self):
        self.assertIsNone(extract_constraint_name(IntegrityError("algo raro")))

    def test_constraint_desconocido_cae_en_mensaje_generico(self):
        exc = IntegrityError(1062, "Duplicate entry 'x' for key 'indice_no_registrado'")
        traducido = translate_integrity_error(exc)
        self.assertIsInstance(traducido, BusinessRuleViolation)
        self.assertEqual(traducido.code, "integrity_error")


class CommandDecoratorTests(TestCase):
    def test_traduce_integrity_error(self):
        @command
        def romper():
            raise IntegrityError(1062, "Duplicate entry 'GBP-000' for key 'enrollment'")

        with self.assertRaises(BusinessRuleViolation) as ctx:
            romper()
        self.assertEqual(ctx.exception.code, "duplicate_enrollment")

    def test_deja_pasar_los_errores_de_dominio(self):
        @command
        def romper():
            raise BusinessRuleViolation("mensaje propio", code="mio")

        with self.assertRaises(DomainError) as ctx:
            romper()
        self.assertEqual(ctx.exception.code, "mio")


class DomainEventTests(TestCase):
    """
    OJO al escribir tests que dependan de eventos.

    ``TestCase`` envuelve cada test en una transacción que se revierte y nunca
    se confirma, así que los callbacks de ``transaction.on_commit`` —y con ellos
    todo el bus de eventos— **no se ejecutan solos**. Hay que envolverlos en
    ``captureOnCommitCallbacks(execute=True)``.

    Es la misma trampa que hará invisibles las notificaciones de la Etapa 10 si
    se olvida: los tests pasarían en verde sin que ningún handler haya corrido.
    """

    def setUp(self):
        # Se restaura el registro en vez de dejarlo vacío: los handlers reales
        # —como el que activa el liderazgo diferido de RF-12— los registran las
        # apps al arrancar, y borrarlos dejaría al resto de la suite corriendo
        # sin ellos. El fallo aparecería lejos de aquí y solo según el orden.
        self.addCleanup(events.restore_handlers, events.snapshot_handlers())
        events.clear_handlers()

    def test_el_despacho_espera_al_commit(self):
        recibidos = []

        @events.on("prueba.evento")
        def handler(**payload):
            recibidos.append(payload)

        with self.captureOnCommitCallbacks(execute=True):
            events.emit("prueba.evento", valor=1)
            # Todavía sin confirmar: nada debe haberse despachado.
            self.assertEqual(recibidos, [])

        self.assertEqual(recibidos, [{"valor": 1}])

    def test_un_handler_que_falla_no_detiene_a_los_demas(self):
        recibidos = []

        @events.on("prueba.evento")
        def revienta(**payload):
            raise RuntimeError("fallo del handler")

        @events.on("prueba.evento")
        def funciona(**payload):
            recibidos.append(payload)

        with self.assertLogs("core.events", level="ERROR"):
            with self.captureOnCommitCallbacks(execute=True):
                events.emit("prueba.evento", valor=2)

        self.assertEqual(recibidos, [{"valor": 2}])

    def test_evento_sin_suscriptores_no_falla(self):
        with self.captureOnCommitCallbacks(execute=True):
            events.emit("evento.sin.nadie", valor=3)


class MinimalPdfTests(TestCase):
    def test_el_pdf_generado_es_estructuralmente_valido(self):
        """
        Los documentos semilla son PDFs de verdad, no relleno con extensión.

        El validador solo mira extensión y content-type, así que un archivo
        cualquiera pasaría; se comprueba la estructura para que el dato semilla
        no afirme algo que no es.
        """
        data = build_minimal_pdf("Prueba")

        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))

        # startxref debe apuntar exactamente al inicio de la tabla xref.
        posicion = int(re.search(rb"startxref\s+(\d+)", data).group(1))
        self.assertEqual(data[posicion : posicion + 4], b"xref")

        # Y la primera entrada de la tabla, al primer objeto.
        offset = int(re.search(rb"\n(\d{10}) 00000 n", data).group(1))
        self.assertEqual(data[offset : offset + 7], b"1 0 obj")


@override_settings(DEBUG=True)
class SeedDemoDataTests(TestCase):
    """
    El sembrado reproduce el estado de MASTER §17.

    ``DEBUG=True`` se fuerza porque el runner de Django lo apaga y el comando se
    niega a ejecutarse fuera de desarrollo — que es justamente lo que se quiere
    de él.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def seed(self, *args):
        call_command(
            "seed_demo_data", *args, stdout=io.StringIO(), stderr=io.StringIO()
        )

    def test_reproduce_el_estado_de_la_fase_1(self):
        from apps.academic.models import PaoPeriod
        from apps.accounts.models import Student
        from apps.clubs.models import Club, ClubDocument, Membership, Role

        self.seed()

        self.assertEqual(PaoPeriod.objects.count(), 2)
        self.assertEqual(PaoPeriod.objects.get(pk="2026-I").status, "Active")
        self.assertEqual(PaoPeriod.objects.get(pk="2025-II").status, "Closed")

        self.assertEqual(Student.objects.filter(is_gbp_admin=True).count(), 1)
        self.assertEqual(Student.objects.count(), 6)

        self.assertEqual(Club.objects.count(), 2)
        self.assertEqual(Role.objects.filter(club__acronym="KOKOA").count(), 5)
        self.assertEqual(ClubDocument.objects.count(), 2)
        self.assertEqual(Membership.objects.count(), 4)

    def test_el_liderazgo_queda_realmente_armado(self):
        """
        Regresión de la trampa que motivó no usar fixtures.

        Con ``loaddata`` el snapshot ``is_leadership`` se queda en False y
        ``leadership_lock`` en NULL: el dataset cargaría sin error y RN-1 no
        vigilaría a nadie. Aquí se comprueba que el cerrojo existe de verdad.
        """
        from apps.clubs.models import Membership

        self.seed()
        lider = Membership.objects.get(
            student__enrollment="201899001", club__acronym="KOKOA"
        )

        self.assertTrue(lider.is_leadership)
        self.assertEqual(lider.leadership_lock, lider.student_id)

    def test_el_club_sin_lider_conserva_la_matricula(self):
        """RF-12 y decisión D-01."""
        from apps.clubs.models import Club

        self.seed()
        club = Club.objects.get(acronym="MECATRÓNICA")

        self.assertEqual(club.status, Club.Status.PENDING_LEADER)
        self.assertIsNone(club.leader)
        self.assertEqual(club.leader_enrollment, "202099777")

    def test_la_membresia_historica_queda_congelada(self):
        """RN-4: la nómina de 2025-II es evidencia del período cerrado."""
        from apps.clubs.models import Membership

        self.seed()
        historica = Membership.objects.get(
            student__enrollment="202055789", pao_period="2025-II"
        )
        vigente = Membership.objects.get(
            student__enrollment="202055789", pao_period="2026-I"
        )

        self.assertEqual(historica.status, Membership.Status.FROZEN)
        self.assertEqual(vigente.status, Membership.Status.ACTIVE)

    def test_no_duplica_al_ejecutarse_dos_veces(self):
        from apps.clubs.models import Club

        self.seed()
        self.seed()
        self.assertEqual(Club.objects.count(), 2)

    def test_reset_regenera_sin_duplicar(self):
        from apps.clubs.models import Club, Membership

        self.seed()
        self.seed("--reset", "--noinput")

        self.assertEqual(Club.objects.count(), 2)
        self.assertEqual(Membership.objects.count(), 4)

    def test_se_niega_a_correr_fuera_de_desarrollo(self):
        from django.core.management.base import CommandError

        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                self.seed()
