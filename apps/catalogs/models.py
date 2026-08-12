"""
Catálogos cerrados del sistema (MASTER §7.3).

Se modelan como tablas y no como ``TextChoices`` a propósito. PPD-01 dejó
abierta la lista oficial de facultades de ESPOL: si fuera un enum de código,
ampliarla exigiría una migración y un despliegue. Como tabla, es un alta desde
el admin.
"""

from django.db import models

from core.models import TimeStampedModel


class CatalogEntry(TimeStampedModel):
    """Comportamiento común de los catálogos: vigencia y orden de presentación."""

    name = models.CharField("nombre", max_length=120, unique=True)
    is_active = models.BooleanField(
        "vigente",
        default=True,
        help_text="Las entradas no vigentes dejan de ofrecerse en los "
        "formularios, pero siguen siendo legibles en los datos históricos.",
    )
    display_order = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        abstract = True
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class Faculty(CatalogEntry):
    """
    Facultad de ESPOL.

    Alimenta el filtro del catálogo de clubes (RF-46) y el perfil del estudiante.
    Es nula para el personal GBP, que no pertenece a ninguna facultad.
    """

    code = models.CharField(
        "sigla",
        max_length=20,
        unique=True,
        help_text="Sigla institucional, por ejemplo FIEC.",
    )

    class Meta(CatalogEntry.Meta):
        abstract = False
        verbose_name = "facultad"
        verbose_name_plural = "facultades"

    def __str__(self):
        return f"{self.code} — {self.name}"


class InterestArea(CatalogEntry):
    """
    Área de interés de un club.

    Todo club declara al menos una (RF-15) y el catálogo móvil filtra por ellas.
    """

    class Meta(CatalogEntry.Meta):
        abstract = False
        verbose_name = "área de interés"
        verbose_name_plural = "áreas de interés"
