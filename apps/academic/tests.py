"""Tests del calendario académico. El foco está en el invariante I-08."""

import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.academic.models import PaoPeriod
from apps.academic.selectors import get_active_pao, get_periods_after
from apps.academic.services import activate_pao, close_pao, create_pao
from core.exceptions import (
    BusinessRuleViolation,
    ConfigurationError,
    DomainValidationError,
)


def make_period(pao_period, *, start, end, status=PaoPeriod.Status.CLOSED):
    return PaoPeriod.objects.create(
        pao_period=pao_period,
        start_date=datetime.date.fromisoformat(start),
        end_date=datetime.date.fromisoformat(end),
        status=status,
    )


class PaoPeriodModelTests(TestCase):
    def test_sequence_se_deriva_del_identificador(self):
        period = make_period("2026-I", start="2026-05-01", end="2026-09-15")
        self.assertEqual(period.sequence, 20261)

    def test_orden_cronologico_no_alfabetico(self):
        """
        '2026-I' vs '2026-II': alfabéticamente 'I' < 'II', y en ese caso el orden
        coincide. El caso que delata el problema es comparar años distintos.
        """
        primero = make_period("2025-II", start="2025-10-13", end="2026-02-27")
        segundo = make_period("2026-I", start="2026-05-01", end="2026-09-15")

        self.assertTrue(segundo.is_later_than(primero))
        self.assertFalse(primero.is_later_than(segundo))
        self.assertEqual(
            list(get_periods_after(primero).values_list("pk", flat=True)),
            ["2026-I"],
        )

    def test_formato_invalido_es_rechazado(self):
        with self.assertRaises(ValidationError):
            PaoPeriod.compute_sequence("2026-III")
        with self.assertRaises(ValidationError):
            PaoPeriod.compute_sequence("semestre-1")

    def test_fin_debe_ser_posterior_al_inicio(self):
        # Los comandos fallan siempre con la familia DomainError, aunque quien
        # detecte el problema sea full_clean() y no la base.
        with self.assertRaises(DomainValidationError):
            create_pao(
                pao_period="2026-I",
                start_date=datetime.date(2026, 9, 15),
                end_date=datetime.date(2026, 5, 1),
            )

    def test_check_constraint_de_fechas_actua_en_la_base(self):
        """La validación de Python no es la única defensa: el CHECK existe."""
        make_period("2026-I", start="2026-05-01", end="2026-09-15")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PaoPeriod.objects.filter(pk="2026-I").update(
                    end_date=datetime.date(2026, 1, 1)
                )


class SingleActivePaoTests(TestCase):
    """Invariante I-08 — el corazón de este bloque."""

    def setUp(self):
        self.anterior = make_period("2025-II", start="2025-10-13", end="2026-02-27")
        self.actual = make_period("2026-I", start="2026-05-01", end="2026-09-15")

    def test_activar_cierra_los_demas(self):
        activate_pao("2025-II")
        activate_pao("2026-I")

        self.assertEqual(
            PaoPeriod.objects.filter(status=PaoPeriod.Status.ACTIVE).count(), 1
        )
        self.anterior.refresh_from_db()
        self.actual.refresh_from_db()
        self.assertEqual(self.anterior.status, PaoPeriod.Status.CLOSED)
        self.assertEqual(self.actual.status, PaoPeriod.Status.ACTIVE)

    def test_la_base_rechaza_dos_periodos_activos(self):
        """
        La prueba decisiva: saltarse los servicios y escribir directo contra la
        base. Si esto NO falla, la columna generada no se creó y el mismo patrón
        tampoco defenderá RN-1 (un solo liderazgo) en la Etapa 2.
        """
        activate_pao("2026-I")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PaoPeriod.objects.filter(pk="2025-II").update(
                    status=PaoPeriod.Status.ACTIVE
                )

    def test_activar_es_idempotente(self):
        activate_pao("2026-I")
        activate_pao("2026-I")
        self.assertEqual(
            PaoPeriod.objects.filter(status=PaoPeriod.Status.ACTIVE).count(), 1
        )

    def test_cerrar_un_periodo_ya_cerrado_es_error_de_negocio(self):
        with self.assertRaises(BusinessRuleViolation):
            close_pao("2026-I")


class ActivePaoSelectorTests(TestCase):
    def test_sin_periodo_activo_falla_explicitamente(self):
        make_period("2026-I", start="2026-05-01", end="2026-09-15")
        with self.assertRaises(ConfigurationError):
            get_active_pao()

    def test_devuelve_el_periodo_vigente(self):
        make_period("2026-I", start="2026-05-01", end="2026-09-15")
        activate_pao("2026-I")
        self.assertEqual(get_active_pao().pk, "2026-I")


class CreatePaoServiceTests(TestCase):
    def test_crear_y_activar_en_un_paso(self):
        period = create_pao(
            pao_period="2026-i",
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 9, 15),
            activate=True,
        )
        # El identificador se normaliza a mayúsculas.
        self.assertEqual(period.pk, "2026-I")
        self.assertEqual(period.status, PaoPeriod.Status.ACTIVE)

    def test_crear_deja_el_periodo_cerrado_por_defecto(self):
        period = create_pao(
            pao_period="2026-I",
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 9, 15),
        )
        self.assertEqual(period.status, PaoPeriod.Status.CLOSED)
