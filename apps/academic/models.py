"""
Calendario académico: el reloj del negocio.

La vigencia de casi todo el sistema —membresías, nóminas, trámites, histórico—
se ancla a un PAO. Por eso vive en su propio contexto y no dentro de ``gbp``:
GBP lo administra, pero el negocio entero lo consume, y modelarlo dentro de GBP
produciría la dependencia circular ``clubs ⇄ gbp`` (LOGICA_NEGOCIO.md §2.1).
"""

import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from core.models import TimeStampedModel

PAO_PATTERN = r"^\d{4}-(I|II)$"

validate_pao_format = RegexValidator(
    regex=PAO_PATTERN,
    message="El identificador debe tener la forma AAAA-I o AAAA-II (por ejemplo 2026-I).",
    code="invalid_pao_format",
)

#: Término académico -> dígito de orden dentro del año.
_TERM_ORDER = {"I": 1, "II": 2}


class PaoPeriod(TimeStampedModel):
    """
    Período Académico Ordinario (semestre de ESPOL).

    La llave primaria es el identificador natural (``2026-I``) en vez de un
    entero autoincremental. Es una tabla-dimensión de dos filas por año, no una
    tabla OLTP de escritura, así que el ancho de la clave foránea no tiene
    consecuencias medibles; a cambio, las fixtures, las consultas del histórico
    (``?pao=2026-I``) y la depuración quedan legibles sin un join.
    """

    class Status(models.TextChoices):
        # RNF-10: valor en inglés hacia la base, etiqueta en español hacia la UI.
        ACTIVE = "Active", "Activo"
        CLOSED = "Closed", "Cerrado"

    pao_period = models.CharField(
        "período",
        max_length=10,
        primary_key=True,
        validators=[validate_pao_format],
        help_text="Identificador del período, por ejemplo 2026-I.",
    )

    # Ordenar por el identificador como texto es incorrecto en cuanto convivan
    # '2026-I' y '2026-II': alfabéticamente 'I' precede a 'II', pero el orden
    # cronológico depende del año primero. La regla de expiración (M3) necesita
    # comparar "PAO posterior", así que el orden se materializa aquí (D-14).
    sequence = models.PositiveIntegerField(
        "orden cronológico",
        unique=True,
        editable=False,
        help_text="Derivado del identificador. 2026-I → 20261.",
    )

    start_date = models.DateField("inicio")
    end_date = models.DateField("fin")

    status = models.CharField(
        "estado",
        max_length=10,
        choices=Status.choices,
        default=Status.CLOSED,
    )

    # Invariante I-08: solo un período activo.
    #
    # No se puede expresar como UniqueConstraint(condition=...): el backend
    # MySQL/MariaDB de Django declara supports_partial_indexes = False, así que
    # esa condición se ignora en silencio y el constraint no se crea. El patrón
    # portable es una columna generada que vale 1 cuando la condición se cumple
    # y NULL cuando no, con un índice único encima: MariaDB admite múltiples
    # NULL en un índice único, de modo que los períodos cerrados no compiten.
    active_lock = models.GeneratedField(
        expression=models.Case(
            models.When(status=Status.ACTIVE, then=models.Value(1)),
            default=None,
            output_field=models.PositiveSmallIntegerField(null=True),
        ),
        output_field=models.PositiveSmallIntegerField(null=True),
        db_persist=True,
        verbose_name="cerrojo de período activo",
    )

    class Meta:
        verbose_name = "período académico"
        verbose_name_plural = "períodos académicos"
        ordering = ["-sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["active_lock"],
                name="uniq_single_active_pao",
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F("start_date")),
                name="chk_pao_end_after_start",
            ),
        ]

    def __str__(self):
        return self.pao_period

    @staticmethod
    def compute_sequence(pao_period):
        """``'2026-I'`` -> ``20261``. Lanza ValidationError si el formato no calza."""
        match = re.match(PAO_PATTERN, pao_period or "")
        if not match:
            raise ValidationError(
                {"pao_period": validate_pao_format.message},
                code="invalid_pao_format",
            )
        year, term = pao_period.split("-")
        return int(year) * 10 + _TERM_ORDER[term]

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError(
                {"end_date": "La fecha de fin debe ser posterior a la de inicio."},
                code="invalid_pao_dates",
            )

    def save(self, *args, **kwargs):
        # La PK es inmutable, así que basta con derivarlo una vez; se recalcula
        # siempre de todos modos para que una fixture cargada con loaddata (que
        # no pasa por full_clean) no quede con un sequence inconsistente.
        self.sequence = self.compute_sequence(self.pao_period)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def is_later_than(self, other):
        """¿Este período es cronológicamente posterior a ``other``?"""
        return self.sequence > other.sequence
