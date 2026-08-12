"""
Clubes, roles internos y membresías.

Aquí vive la parte más delicada del dominio: la relación entre un estudiante, un
club, un rol y un período de vigencia. De ella dependen RN-1 (exclusividad de
liderazgo), RN-3 (privacidad de la nómina) y RN-4 (caducidad por PAO).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.clubs.permissions import ALL_PERMISSIONS, ClubPermission
from core.models import TimeStampedModel
from core.validators import validate_pdf_file, validate_social_media


class Club(TimeStampedModel):
    """
    Club o capítulo estudiantil.

    Un club nunca nace por iniciativa del estudiante: siempre lo da de alta GBP
    vinculando la matrícula de quien será su líder (RF-11).
    """

    class Status(models.TextChoices):
        ACTIVE = "Active", "Activo"
        PENDING_LEADER = "Pending Leader", "Sin líder"

    name = models.CharField("nombre", max_length=150)
    acronym = models.CharField("acrónimo", max_length=30)
    description = models.TextField("descripción")
    location = models.CharField("ubicación", max_length=120)

    faculty = models.ForeignKey(
        "catalogs.Faculty",
        verbose_name="facultad",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="clubs",
    )

    # Tabla puente en vez de un JSON con nombres sueltos. El catálogo filtrable
    # por área (RF-46) es la funcionalidad prioritaria del sistema: con JSON
    # cada filtro sería un escaneo completo de la tabla; con la relación, una
    # búsqueda por índice.
    interest_areas = models.ManyToManyField(
        "catalogs.InterestArea",
        verbose_name="áreas de interés",
        related_name="clubs",
        blank=True,
    )

    image = models.CharField("portada", max_length=255, blank=True)

    # Decisión D-01 — dos campos con papeles distintos, no redundantes:
    #
    #   leader_enrollment  la matrícula que GBP comprometió. Puede no
    #                      corresponder a ninguna cuenta todavía; es lo que
    #                      permite activar el liderazgo cuando esa persona se
    #                      registre (RF-12). Modelarlo solo como FK perdería el
    #                      dato y haría RF-12 imposible de cumplir.
    #   leader             el vínculo ya resuelto contra una cuenta real.
    leader_enrollment = models.CharField(
        "matrícula del líder",
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Matrícula designada por GBP. Puede no tener cuenta aún.",
    )
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="líder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_club",
    )

    status = models.CharField(
        "estado",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_LEADER,
    )
    social_media = models.JSONField(
        "redes sociales", default=list, blank=True, validators=[validate_social_media]
    )

    class Meta:
        verbose_name = "club"
        verbose_name_plural = "clubes"
        ordering = ["name"]
        constraints = [
            # Invariante I-23: el estado y el liderazgo no pueden divergir.
            # Un club activo tiene líder resuelto; uno sin líder está en solo
            # lectura. Sin esto, un club podría quedar 'Active' sin nadie que
            # pueda administrarlo, y ninguna pantalla lo detectaría.
            models.CheckConstraint(
                condition=(
                    models.Q(status="Active", leader__isnull=False)
                    | models.Q(status="Pending Leader", leader__isnull=True)
                ),
                name="chk_club_status_matches_leader",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="idx_club_status"),
            models.Index(fields=["faculty", "status"], name="idx_club_faculty_status"),
        ]

    def __str__(self):
        return f"{self.acronym} — {self.name}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_read_only(self):
        """
        Un club sin líder queda en solo lectura (RF-13).

        Lo consulta la policy transversal que gobierna todas las escrituras del
        club, para no repetir la comprobación en cada servicio.
        """
        return self.status == self.Status.PENDING_LEADER

    @property
    def members_count(self):
        """
        Conteo de miembros activos.

        Derivado, nunca almacenado (P-5): un contador persistido se desincroniza
        con la primera baja que no pase por el camino previsto. Para listados
        usar ``selectors.list_clubs()``, que lo resuelve con una anotación en
        vez de una consulta por fila.
        """
        return self.memberships.filter(status=Membership.Status.ACTIVE).count()


class ClubDocument(TimeStampedModel):
    """
    Documento del club.

    Promovido a tabla propia desde el JSON embebido de la Fase 1: el frontend ya
    lo trataba como colección con identidad (``setDocVisibility(docId, ...)``).
    """

    club = models.ForeignKey(
        Club, verbose_name="club", on_delete=models.CASCADE, related_name="documents"
    )
    title = models.CharField("título", max_length=150)
    file = models.FileField(
        "archivo", upload_to="clubs/docs/", validators=[validate_pdf_file]
    )
    is_public = models.BooleanField(
        "público",
        default=False,
        help_text="Público: visible para toda la comunidad. Privado: solo para "
        "los miembros del club (RF-16).",
    )

    class Meta:
        verbose_name = "documento del club"
        verbose_name_plural = "documentos del club"
        ordering = ["club", "title"]
        indexes = [
            models.Index(fields=["club", "is_public"], name="idx_doc_club_public"),
        ]

    def __str__(self):
        return self.title


class Role(TimeStampedModel):
    """
    Rol interno de un club.

    Los roles son **por club**: dos clubes pueden tener un 'Secretario/a' con
    permisos distintos y son entidades diferentes.
    """

    club = models.ForeignKey(
        Club, verbose_name="club", on_delete=models.CASCADE, related_name="roles"
    )
    role_name = models.CharField("nombre del rol", max_length=80)
    is_default = models.BooleanField(
        "predeterminado",
        default=False,
        help_text="Los cuatro roles creados con el club. No se pueden borrar.",
    )
    is_leadership = models.BooleanField(
        "directivo",
        default=False,
        help_text="Solo los roles directivos pueden asignar roles y permisos (RN-7).",
    )
    is_active = models.BooleanField(
        "vigente",
        default=True,
        help_text="Decisión D-13: un rol que ya tuvo miembros no se borra, se "
        "desactiva, para que las membresías históricas sigan siendo legibles.",
    )
    permissions = models.JSONField(
        "permisos",
        default=dict,
        blank=True,
        help_text="Diccionario {clave: bool}. Una clave ausente vale False.",
    )

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["club", "-is_leadership", "role_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "role_name"], name="uniq_role_per_club"
            ),
        ]

    def __str__(self):
        return f"{self.role_name} ({self.club.acronym})"

    def clean(self):
        super().clean()
        unknown = set(self.permissions or {}) - set(ALL_PERMISSIONS)
        if unknown:
            raise ValidationError(
                {"permissions": f"Permisos desconocidos: {', '.join(sorted(unknown))}."}
            )
        # RN-7: manage_roles es la capacidad de repartir capacidades. Otorgarla a
        # un rol no directivo permitiría que un miembro común se autoascienda.
        if self.has(ClubPermission.MANAGE_ROLES) and not self.is_leadership:
            raise ValidationError(
                {
                    "permissions": "El permiso 'manage_roles' solo puede otorgarse "
                    "a roles directivos (RN-7)."
                }
            )

    def has(self, permission):
        """Una clave ausente vale False (MASTER §3.3)."""
        return bool((self.permissions or {}).get(str(permission), False))

    @property
    def granted_permissions(self):
        return sorted(key for key, value in (self.permissions or {}).items() if value)


class Membership(TimeStampedModel):
    """
    Pertenencia de un estudiante a un club, con su rol y su vigencia por período.

    Es la entidad que materializa RF-17 (varios clubes a la vez, un solo
    liderazgo) y RF-18 (vigencia por PAO).
    """

    class Status(models.TextChoices):
        ACTIVE = "Active", "Activa"
        FROZEN = "Frozen", "Congelada"
        EXPIRED = "Expired", "Expirada"
        REVOKED = "Revoked", "Revocada"

    class Origin(models.TextChoices):
        """De dónde salió la membresía. Soporte de trazabilidad para RF-52."""

        APPLICATION = "Application", "Solicitud aprobada"
        RENEWAL = "Renewal", "Renovación de nómina"
        LEADER_ASSIGNMENT = "LeaderAssignment", "Asignación de liderazgo por GBP"
        SEED = "Seed", "Carga inicial"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="estudiante",
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    club = models.ForeignKey(
        Club, verbose_name="club", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.ForeignKey(
        Role, verbose_name="rol", on_delete=models.PROTECT, related_name="memberships"
    )
    pao_period = models.ForeignKey(
        "academic.PaoPeriod",
        verbose_name="período",
        on_delete=models.PROTECT,
        related_name="memberships",
    )

    # Copiadas del período al crear la membresía, no leídas por join. El PAO
    # puede editarse después; la vigencia pactada con el miembro, no.
    valid_from = models.DateField("vigente desde")
    valid_until = models.DateField("vigente hasta")

    status = models.CharField(
        "estado", max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    origin = models.CharField(
        "origen", max_length=20, choices=Origin.choices, default=Origin.APPLICATION
    )

    # Snapshot deliberado del rol (decisión D-05). Existe porque el invariante
    # I-09 necesita un índice único sobre (estudiante activo con rol directivo),
    # y una columna generada no puede leer otra tabla para averiguar si el rol
    # es directivo. Sin este campo, RN-1 solo podría defenderse en Python y dos
    # peticiones concurrentes podrían crear dos liderazgos.
    #
    # Se resincroniza al cambiar el rol de la membresía o el flag del rol.
    is_leadership = models.BooleanField(
        "es directiva", default=False, editable=False, db_index=True
    )

    # Invariante I-09 (RN-1): un estudiante no puede tener dos membresías
    # activas de liderazgo. Vale el id del estudiante cuando la membresía es
    # directiva y está activa; NULL en cualquier otro caso. Como MariaDB admite
    # múltiples NULL en un índice único, solo compiten las filas directivas.
    leadership_lock = models.GeneratedField(
        expression=models.Case(
            models.When(
                models.Q(status=Status.ACTIVE, is_leadership=True),
                then=models.F("student"),
            ),
            default=None,
            output_field=models.BigIntegerField(null=True),
        ),
        output_field=models.BigIntegerField(null=True),
        db_persist=True,
        verbose_name="cerrojo de liderazgo",
    )

    class Meta:
        verbose_name = "membresía"
        verbose_name_plural = "membresías"
        ordering = ["-pao_period__sequence", "club", "student"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "club", "pao_period"],
                name="uniq_membership_per_pao",
            ),
            models.UniqueConstraint(
                fields=["leadership_lock"],
                name="uniq_active_leadership_per_student",
            ),
        ]
        indexes = [
            models.Index(fields=["club", "status"], name="idx_membership_club_status"),
            models.Index(
                fields=["student", "status"], name="idx_membership_student_status"
            ),
        ]

    def __str__(self):
        return f"{self.student.enrollment} @ {self.club.acronym} ({self.pao_period_id})"

    def clean(self):
        super().clean()
        # Invariante I-11 (RF-09): el rol pertenece al mismo club. Cruza dos
        # tablas, así que ningún CHECK puede expresarlo; se valida aquí y en el
        # servicio que asigna roles.
        if self.role_id and self.club_id and self.role.club_id != self.club_id:
            raise ValidationError(
                {"role": "El rol debe pertenecer al mismo club que la membresía."}
            )

    def save(self, *args, **kwargs):
        # El snapshot se deriva del rol en cada guardado: así no puede quedar
        # desalineado por un camino que olvide actualizarlo.
        if self.role_id:
            self.is_leadership = self.role.is_leadership
        super().save(*args, **kwargs)

    @property
    def is_current(self):
        return self.status == self.Status.ACTIVE

    def has_permission(self, permission):
        """Los permisos de una membresía no vigente no cuentan."""
        return self.is_current and self.role.has(permission)
