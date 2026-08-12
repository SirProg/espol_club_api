"""
Solicitudes de membresía.

El puente entre el estudiante que descubre un club y el club que lo acepta. Es
el "núcleo irrenunciable" de MASTER §1.3: que alguien pueda postular a un club
que no conocía.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TimeStampedModel


class MembershipApplication(TimeStampedModel):
    """
    Una postulación a un club.

    Guarda las respuestas contra ``form_id`` y cada ``field_id``, nunca contra
    el texto de la pregunta: si el formulario se versiona, la solicitud sigue
    siendo legible con el esquema que el estudiante vio de verdad.
    """

    class Status(models.TextChoices):
        PENDING = "Pending", "Pendiente"
        APPROVED = "Approved", "Aprobada"
        REJECTED = "Rejected", "Rechazada"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="estudiante",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    club = models.ForeignKey(
        "clubs.Club",
        verbose_name="club",
        on_delete=models.CASCADE,
        related_name="applications",
    )
    form = models.ForeignKey(
        "dynamicforms.Form",
        verbose_name="formulario",
        on_delete=models.PROTECT,
        related_name="applications",
    )

    responses = models.JSONField(
        "respuestas",
        default=list,
        help_text="Lista [{field_id, answer}] validada contra el esquema.",
    )

    status = models.CharField(
        "estado", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    leader_feedback = models.TextField(
        "retroalimentación",
        blank=True,
        help_text="Obligatoria al rechazar (RN-5).",
    )

    # Decisión D-04: RF-52 exige registrar quién resolvió y cuándo, y el modelo
    # de MASTER no tenía dónde escribirlo. Reconstruirlo después es imposible.
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="resuelta por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_applications",
    )
    resolved_at = models.DateTimeField("resuelta el", null=True, blank=True)

    # Corrección a D-05: la decisión original ponía este enlace en Membership
    # como 'source_application', pero eso invertía el grafo de dependencias
    # (applications depende de clubs, no al revés). Vive aquí, que es el lado
    # que ya conoce a clubs.
    resulting_membership = models.OneToOneField(
        "clubs.Membership",
        verbose_name="membresía creada",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_application",
    )

    # Invariante I-10 (RN-2): una sola solicitud Pendiente por estudiante y
    # club. Es la tercera unicidad condicional del sistema, y como MySQL y
    # MariaDB no soportan índices parciales, se resuelve igual que I-08 e I-09:
    # columnas generadas que valen NULL cuando la condición no se cumple.
    #
    # Se usan dos columnas en vez de concatenar en una cadena porque un índice
    # único de MariaDB admite múltiples filas si CUALQUIER parte de la clave es
    # NULL: cuando la solicitud no está pendiente, ambas quedan nulas y la fila
    # deja de competir. Evita además depender de CAST/CONCAT, cuyo
    # comportamiento difiere entre motores.
    pending_student = models.GeneratedField(
        expression=models.Case(
            models.When(status=Status.PENDING, then=models.F("student")),
            default=None,
            output_field=models.BigIntegerField(null=True),
        ),
        output_field=models.BigIntegerField(null=True),
        db_persist=True,
        verbose_name="cerrojo de postulación (estudiante)",
    )
    pending_club = models.GeneratedField(
        expression=models.Case(
            models.When(status=Status.PENDING, then=models.F("club")),
            default=None,
            output_field=models.BigIntegerField(null=True),
        ),
        output_field=models.BigIntegerField(null=True),
        db_persist=True,
        verbose_name="cerrojo de postulación (club)",
    )

    class Meta:
        verbose_name = "solicitud de membresía"
        verbose_name_plural = "solicitudes de membresía"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["pending_student", "pending_club"],
                name="uniq_pending_application_per_club",
            ),
            # RN-5: rechazar exige justificación. Es expresable como CHECK
            # porque solo mira columnas de la propia fila.
            models.CheckConstraint(
                condition=(
                    ~models.Q(status="Rejected") | ~models.Q(leader_feedback="")
                ),
                name="chk_rejection_requires_feedback",
            ),
        ]
        indexes = [
            models.Index(
                fields=["club", "status"], name="idx_application_club_status"
            ),
            models.Index(
                fields=["student", "status"], name="idx_application_student_status"
            ),
        ]

    def __str__(self):
        return f"{self.student.enrollment} -> {self.club.acronym} ({self.status})"

    @property
    def submitted_at(self):
        """
        Nombre del dominio (MASTER §7.2) para la marca de creación.

        No se duplica como columna propia: sería el mismo instante escrito dos
        veces, con la posibilidad de que discreparan.
        """
        return self.created_at

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_resolved(self):
        return self.status in {self.Status.APPROVED, self.Status.REJECTED}

    def clean(self):
        super().clean()
        if self.status == self.Status.REJECTED and not (self.leader_feedback or "").strip():
            raise ValidationError(
                {
                    "leader_feedback": (
                        "Debes explicar el motivo del rechazo para que el "
                        "estudiante sepa qué corregir (RN-5)."
                    )
                }
            )
        if self.form_id and self.club_id and self.form.club_id != self.club_id:
            raise ValidationError(
                {"form": "El formulario debe pertenecer al club al que se postula."}
            )

    def answers_with_labels(self):
        """
        Empareja cada respuesta con la pregunta de **su** versión del formulario.

        Es lo que la bandeja del líder necesita mostrar. Resolverlo contra el
        formulario vigente en vez de contra el de la solicitud produciría
        etiquetas que no corresponden a lo que el estudiante contestó.
        """
        schema = {field["field_id"]: field for field in self.form.fields}
        resolved = []
        for entry in self.responses:
            field = schema.get(entry.get("field_id"))
            resolved.append(
                {
                    "field_id": entry.get("field_id"),
                    "label": field["label"] if field else entry.get("field_id"),
                    "type": field["type"] if field else "text",
                    "answer": entry.get("answer"),
                }
            )
        return resolved
