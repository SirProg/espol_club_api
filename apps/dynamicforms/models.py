"""
Formularios dinámicos.

El líder diseña el **esquema** desde el panel web; la app móvil solo lo renderiza
y envía respuestas (RF-22, RF-23). El backend usa el mismo esquema para validar
lo que llega, así que el cliente nunca es la autoridad sobre qué es una
respuesta válida.

**Sobre la relación con los eventos.** MASTER modela la relación por duplicado
(``Form.event`` y ``Event.registration_form``), y la decisión D-02 la redujo a
una sola dejando ``Form.event``. Al construirlo apareció que esa dirección crea
un ciclo entre apps: ``dynamicforms`` necesitaría conocer ``events``, y
``events`` ya necesita conocer ``dynamicforms`` para ``EventRegistration.form``.
La única FK vive por tanto en el lado de ``events``, que es el único sentido que
mantiene el grafo acíclico. La semántica original se conserva intacta:
``Event.registration_form IS NULL`` significa "sin registro abierto".
"""

from django.core.exceptions import ValidationError
from django.db import models

from apps.dynamicforms.schema import validate_schema
from core.models import TimeStampedModel


class Form(TimeStampedModel):
    """
    Una **versión** concreta de un formulario.

    Editar un formulario que ya tiene respuestas no lo modifica: crea una
    versión nueva (RF-24). Las respuestas ya enviadas siguen apuntando a la
    versión con la que se llenaron, de modo que el histórico se lee siempre
    contra las preguntas que el estudiante vio de verdad.
    """

    class FormType(models.TextChoices):
        MEMBERSHIP = "Membership", "Membresía"
        EVENT = "Event", "Evento"

    club = models.ForeignKey(
        "clubs.Club", verbose_name="club", on_delete=models.CASCADE, related_name="forms"
    )
    form_type = models.CharField("tipo", max_length=20, choices=FormType.choices)
    title = models.CharField("título", max_length=150)

    fields = models.JSONField(
        "campos",
        default=list,
        help_text="Esquema del formulario. Ver apps.dynamicforms.schema.",
    )

    version = models.PositiveIntegerField("versión", default=1)
    is_active = models.BooleanField(
        "vigente",
        default=True,
        help_text="Solo una versión de cada familia está vigente a la vez.",
    )

    # Define la **familia**: el conjunto de versiones de un mismo formulario.
    # La primera versión tiene root nulo (es la raíz); las siguientes apuntan a
    # ella. Sin esto no habría forma de saber qué versiones son "el mismo
    # formulario" y el número de versión no tendría contra qué contarse.
    root = models.ForeignKey(
        "self",
        verbose_name="formulario original",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="versions",
    )

    class Meta:
        verbose_name = "formulario"
        verbose_name_plural = "formularios"
        ordering = ["club", "form_type", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["root", "version"], name="uniq_form_version_per_family"
            ),
        ]
        indexes = [
            models.Index(
                fields=["club", "form_type", "is_active"], name="idx_form_lookup"
            ),
        ]

    def __str__(self):
        return f"{self.title} (v{self.version})"

    @property
    def family_id(self):
        """
        Identidad estable a través de las versiones.

        Para la raíz es su propia pk; para las demás, la de la raíz.
        """
        return self.root_id or self.pk

    @property
    def field_ids(self):
        return [field["field_id"] for field in self.fields]

    def clean(self):
        super().clean()
        # El esquema se valida y normaliza aquí para que ninguna vía de entrada
        # —API, admin o shell— pueda dejar un formulario imposible de renderizar.
        try:
            self.fields = validate_schema(self.fields)
        except ValidationError as exc:
            raise ValidationError({"fields": exc.messages}) from exc

    def get_field(self, field_id):
        for field in self.fields:
            if field["field_id"] == field_id:
                return field
        return None
