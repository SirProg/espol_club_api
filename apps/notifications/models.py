"""
Centro de notificaciones in-app (RF-51).

Cierra la divergencia §20.18 de MASTER: en la Fase 1 las notificaciones eran de
solo lectura —existían en los datos simulados pero ningún flujo las creaba—. Aquí
nacen de los eventos de dominio del §9.
"""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Notification(TimeStampedModel):
    """
    Un aviso dirigido a una persona.

    Append-only: solo ``read`` muta. Una notificación es el registro de que algo
    pasó, y editarla después sería reescribir esa historia.
    """

    class Type(models.TextChoices):
        # Los valores coinciden con los de MASTER §7.2 para que el frontend de
        # la Fase 1 siga reconociéndolos sin cambios.
        APPLICATION_PENDING = "application_pending", "Solicitud recibida"
        APPLICATION_APPROVED = "application_approved", "Solicitud aprobada"
        APPLICATION_REJECTED = "application_rejected", "Solicitud rechazada"
        MEMBERSHIP_REVOKED = "membership_revoked", "Membresía revocada"
        MEMBERSHIP_RENEWED = "membership_renewed", "Membresía renovada"
        MEMBERSHIP_FROZEN = "membership_frozen", "Membresía congelada"
        LEADER_ASSIGNED = "leader_assigned", "Liderazgo asignado"
        LEADER_REVOKED = "leader_revoked", "Liderazgo revocado"
        EVENT_REGISTERED = "event_registered", "Inscripción a evento"
        ATTENDANCE_REGISTERED = "attendance_registered", "Asistencia registrada"
        GBP_REVIEW = "gbp_review", "Trámite por revisar"
        GBP_RESOLUTION = "gbp_resolution", "Resolución de GBP"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="destinatario",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField("tipo", max_length=60, choices=Type.choices)
    message = models.TextField(
        "mensaje",
        help_text="Texto ya renderizado en español: la notificación es "
        "presentación, y ahí es donde vive la traducción (RNF-10).",
    )
    read = models.BooleanField("leída", default=False)

    # Decisión D-10: sin la referencia, el centro de notificaciones no puede
    # enlazar al objeto que cambió y el usuario tiene que buscarlo a mano.
    target_type = models.CharField("tipo de objeto", max_length=60, blank=True)
    target_id = models.PositiveBigIntegerField("id del objeto", null=True, blank=True)
    club = models.ForeignKey(
        "clubs.Club",
        verbose_name="club",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ["-created_at"]
        constraints = [
            # Idempotencia de CU-NO3: un proceso programado que corra dos veces
            # no debe duplicar el aviso. Al ser un índice de base, tampoco lo
            # duplican dos peticiones concurrentes.
            models.UniqueConstraint(
                fields=["user", "type", "target_type", "target_id"],
                name="uniq_notification_per_target",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "read"], name="idx_notification_user_read"),
        ]

    def __str__(self):
        return f"{self.get_type_display()} -> {self.user.enrollment}"

    @property
    def date(self):
        """Nombre del dominio (MASTER §7.2) para la marca de creación."""
        return self.created_at
