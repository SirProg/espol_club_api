"""
Trámites documentales ante la Gerencia de Bienestar Politécnico.

La rendición de cuentas del club hacia la institución. Es el flujo que MASTER
§1.1 describe como "burocracia analógica": nóminas, estatutos y reportes por PAO
que hoy circulan sin trazabilidad.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimeStampedModel
from core.validators import validate_pdf_file


class GbpDocumentProcess(TimeStampedModel):
    """
    Un envío documental de un club a GBP, con su ciclo de aprobación.

    Una vez enviado queda **congelado para el club** (RF-41): la evidencia que
    GBP audita no puede cambiar bajo sus pies mientras la revisa.
    """

    class Status(models.TextChoices):
        SUBMITTED = "Submitted", "Enviado"
        UNDER_REVIEW = "Under Review", "En revisión"
        APPROVED = "Approved", "Aprobado"
        REJECTED = "Rejected", "Rechazado"

    club = models.ForeignKey(
        "clubs.Club",
        verbose_name="club",
        on_delete=models.CASCADE,
        related_name="gbp_processes",
    )
    pao_period = models.ForeignKey(
        "academic.PaoPeriod",
        verbose_name="período",
        on_delete=models.PROTECT,
        related_name="gbp_processes",
    )
    document_type = models.CharField(
        "tipo de documento",
        max_length=120,
        help_text="Por ejemplo: Nómina de Miembros.",
    )
    file = models.FileField(
        "archivo", upload_to="gbp/processes/", validators=[validate_pdf_file]
    )

    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.SUBMITTED
    )
    review_feedback = models.TextField(
        "observaciones", blank=True, help_text="Obligatorias al rechazar (RN-5)."
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="enviado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_processes",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="revisado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_processes",
    )
    reviewed_at = models.DateTimeField("revisado el", null=True, blank=True)

    # Decisión D-09. La nómina que respalda el trámite es una consulta viva: si
    # un miembro se revoca al día siguiente, el PDF aprobado dejaría de
    # corresponder a los datos del sistema y la auditoría no tendría contra qué
    # contrastar. El snapshot congela la nómina al momento del envío, y es lo
    # que se exporta después (RF-42), no los datos actuales.
    roster_snapshot = models.JSONField(
        "nómina congelada",
        default=list,
        blank=True,
        help_text="Evidencia inmutable de la nómina al momento del envío.",
    )

    class Meta:
        verbose_name = "trámite GBP"
        verbose_name_plural = "trámites GBP"
        ordering = ["-created_at"]
        constraints = [
            # RN-5: rechazar exige justificación. Expresable como CHECK porque
            # solo mira columnas de la propia fila.
            models.CheckConstraint(
                condition=(
                    ~models.Q(status="Rejected") | ~models.Q(review_feedback="")
                ),
                name="chk_process_rejection_requires_feedback",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="idx_process_status"),
            models.Index(fields=["club", "pao_period"], name="idx_process_club_pao"),
        ]

    def __str__(self):
        return f"{self.document_type} — {self.club.acronym} ({self.pao_period_id})"

    @property
    def uploaded_at(self):
        """Nombre del dominio (MASTER §7.2) para la marca de creación."""
        return self.created_at

    @property
    def is_editable_by_club(self):
        """RF-41: enviado es enviado. El club ya no lo toca."""
        return False

    @property
    def is_resolved(self):
        return self.status in {self.Status.APPROVED, self.Status.REJECTED}

    @property
    def snapshot_size(self):
        return len(self.roster_snapshot or [])

    def clean(self):
        super().clean()
        if self.status == self.Status.REJECTED and not (self.review_feedback or "").strip():
            raise ValidationError(
                {
                    "review_feedback": (
                        "Debes explicar el motivo del rechazo para que el club "
                        "sepa qué corregir (RN-5)."
                    )
                }
            )
