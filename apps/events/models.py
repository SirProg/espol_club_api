"""
Eventos, inscripciones, staff y asistencia.

Es la parte del sistema con más riesgo técnico: el escaneo de un QR ocurre en
una sala llena, con varios miembros del staff escaneando a la vez, y la regla
RN-6 —una asistencia por persona y evento— tiene que sostenerse bajo esa
concurrencia. La defensa final no es el código sino
``UNIQUE(event_id, student_id)`` sobre ``EventAttendance``.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class Event(TimeStampedModel):
    """
    Un evento de un club.

    Los eventos ``MembersOnly`` son **visibles para todos** (RF-31): lo que se
    bloquea es el registro, no la existencia del evento. Ocultarlos impediría
    que un estudiante descubriera que el club hace cosas.
    """

    class Mode(models.TextChoices):
        IN_PERSON = "In-person", "Presencial"
        ONLINE = "Online", "En línea"
        VIRTUAL = "Virtual", "Virtual"

    class Visibility(models.TextChoices):
        PUBLIC = "Public", "Público"
        MEMBERS_ONLY = "MembersOnly", "Solo miembros"

    club = models.ForeignKey(
        "clubs.Club", verbose_name="club", on_delete=models.CASCADE, related_name="events"
    )
    event_name = models.CharField("nombre", max_length=150)
    mode = models.CharField("modalidad", max_length=20, choices=Mode.choices)

    # El líder los llena por separado en el formulario (F-13), y así los
    # conserva MASTER §7.2.
    planned_date = models.DateField("fecha")
    planned_hour = models.TimeField("hora")

    # Derivado de los dos anteriores pero **almacenado**, por el mismo motivo
    # que PaoPeriod.sequence: hace falta compararlo dentro de la base.
    #
    # No se usa una columna generada porque planned_date y planned_hour son
    # valores locales ingenuos (el evento es a las 14:30 en Guayaquil) mientras
    # que los DateTimeField se guardan en UTC. Un TIMESTAMP() calculado por
    # MariaDB los mezclaría y el CHECK compararía instantes desplazados cinco
    # horas. La conversión se hace en Python, donde la zona es explícita.
    start_datetime = models.DateTimeField("inicio", editable=False, db_index=True)
    end_datetime = models.DateTimeField("fin")

    planned_place = models.CharField("lugar", max_length=150)
    description = models.TextField("descripción", blank=True)
    marketing_image = models.CharField("imagen", max_length=255, blank=True)

    visibility = models.CharField(
        "visibilidad",
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )

    # Única FK entre eventos y formularios (corrección a D-02): en este sentido
    # el grafo de dependencias queda acíclico. NULL significa, literalmente,
    # "sin registro abierto".
    registration_form = models.ForeignKey(
        "dynamicforms.Form",
        verbose_name="formulario de registro",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    registration_deadline = models.DateTimeField(
        "fecha límite de registro", null=True, blank=True
    )
    blocked_message = models.CharField(
        "mensaje de bloqueo",
        max_length=255,
        blank=True,
        help_text="Texto que ve el estudiante cuando el registro está cerrado.",
    )
    expected_participants = models.PositiveIntegerField(
        "participantes esperados",
        null=True,
        blank=True,
        help_text="Solo planificación: no impone tope de inscripciones (RF-33).",
    )

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventos"
        ordering = ["-start_datetime"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_datetime__gt=models.F("start_datetime")),
                name="chk_event_end_after_start",
            ),
        ]
        indexes = [
            models.Index(fields=["club", "start_datetime"], name="idx_event_club_date"),
            models.Index(fields=["visibility"], name="idx_event_visibility"),
        ]

    def __str__(self):
        return f"{self.event_name} ({self.club.acronym})"

    def compute_start_datetime(self):
        """Combina fecha y hora locales en un instante consciente de la zona."""
        naive = timezone.datetime.combine(self.planned_date, self.planned_hour)
        return timezone.make_aware(naive, timezone.get_current_timezone())

    def clean(self):
        super().clean()
        if self.planned_date and self.planned_hour:
            self.start_datetime = self.compute_start_datetime()

        if self.end_datetime and self.start_datetime:
            if self.end_datetime <= self.start_datetime:
                raise ValidationError(
                    {"end_datetime": "El fin del evento debe ser posterior al inicio."}
                )

        if self.registration_deadline and self.start_datetime:
            if self.registration_deadline > self.start_datetime:
                raise ValidationError(
                    {
                        "registration_deadline": (
                            "La fecha límite de registro no puede ser posterior al "
                            "inicio del evento."
                        )
                    }
                )

        if self.registration_form_id and self.club_id:
            if self.registration_form.club_id != self.club_id:
                raise ValidationError(
                    {"registration_form": "El formulario debe pertenecer al mismo club."}
                )

    def save(self, *args, **kwargs):
        if self.planned_date and self.planned_hour:
            self.start_datetime = self.compute_start_datetime()
        super().save(*args, **kwargs)

    @property
    def has_finished(self):
        return timezone.now() > self.end_datetime

    @property
    def registration_is_open(self):
        """RF-34: el registro se cierra por falta de formulario o por fecha."""
        if self.registration_form_id is None:
            return False
        if self.registration_deadline and timezone.now() > self.registration_deadline:
            return False
        return not self.has_finished

    @property
    def members_only(self):
        return self.visibility == self.Visibility.MEMBERS_ONLY

    @property
    def stats(self):
        """
        Métrica de inscritos vs. asistentes (RF-38).

        Derivada, nunca almacenada (P-5). En listados se resuelve con
        anotaciones; esta propiedad es para el detalle de un solo evento.
        """
        return {
            "registered": self.registrations.count(),
            "attended": self.attendances.count(),
        }

    def scan_window(self):
        """
        Intervalo en que el escaneo es válido (decisión D-08).

        RF-35 dice que el permiso del staff vale "solo durante ese evento", sin
        definir el intervalo. Se abre antes del inicio para el registro de
        entrada y se cierra con margen tras el final, porque las colas no
        terminan cuando termina el acto.
        """
        lead = timezone.timedelta(minutes=settings.SCAN_LEAD_MINUTES)
        grace = timezone.timedelta(minutes=settings.SCAN_GRACE_MINUTES)
        return self.start_datetime - lead, self.end_datetime + grace

    def is_within_scan_window(self, moment=None):
        moment = moment or timezone.now()
        opens_at, closes_at = self.scan_window()
        return opens_at <= moment <= closes_at


class EventAdministrativeData(TimeStampedModel):
    """
    Bloque administrativo del evento (decisión D-07).

    MASTER §20.4 registra la divergencia: el README anida estos campos y los
    datos de la Fase 1 los omiten. Se modelan como tabla 1:1 **opcional** y no
    como JSON porque alimentan la reportería a GBP y deben poder filtrarse y
    exportarse. Su ausencia no impide crear el evento.
    """

    event = models.OneToOneField(
        Event,
        verbose_name="evento",
        on_delete=models.CASCADE,
        related_name="administrative_data",
    )
    objective = models.TextField("objetivo", blank=True)
    sdg = models.JSONField(
        "ODS", default=list, blank=True, help_text="Objetivos de Desarrollo Sostenible."
    )
    responsible_member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="responsable",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsible_for_events",
    )
    responsible_task = models.CharField("tarea del responsable", max_length=255, blank=True)
    allies = models.TextField("aliados", blank=True)
    resource_links = models.JSONField("enlaces de recursos", default=list, blank=True)
    impact_measure = models.TextField("medición de impacto", blank=True)

    class Meta:
        verbose_name = "datos administrativos del evento"
        verbose_name_plural = "datos administrativos de eventos"

    def __str__(self):
        return f"Datos administrativos de {self.event.event_name}"


class EventStaff(TimeStampedModel):
    """
    Asignación de staff **por evento**, no permiso permanente de rol.

    Los permisos nacen y mueren con el evento: quien escanea el taller de marzo
    no puede escanear el de abril salvo que se le asigne otra vez. Es una
    decisión deliberada de MASTER §7.2, y la razón por la que el escaneo
    comprueba la asignación y no un permiso del rol.
    """

    event = models.ForeignKey(
        Event, verbose_name="evento", on_delete=models.CASCADE, related_name="staff"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="miembro",
        on_delete=models.CASCADE,
        related_name="staff_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="asignado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_assignments_made",
    )

    class Meta:
        verbose_name = "staff del evento"
        verbose_name_plural = "staff de eventos"
        constraints = [
            models.UniqueConstraint(
                fields=["event", "student"], name="uniq_event_staff"
            ),
        ]

    def __str__(self):
        return f"{self.student.enrollment} en {self.event.event_name}"


class EventRegistration(TimeStampedModel):
    """
    Inscripción a un evento: el estudiante ya tiene credencial, aún no asistió.

    Dos ejes de estado **independientes**, no redundantes: ``qr_status``
    describe la credencial y ``attendance_status`` la participación. Un QR
    ``Expired`` con asistencia ``NoShow`` es un estado normal y esperado.
    """

    class QrStatus(models.TextChoices):
        ACTIVE = "Active", "Activa"
        USED = "Used", "Usada"
        EXPIRED = "Expired", "Expirada"

    class AttendanceStatus(models.TextChoices):
        REGISTERED = "Registered", "Inscrito"
        ATTENDED = "Attended", "Asistió"
        NO_SHOW = "NoShow", "No asistió"

    event = models.ForeignKey(
        Event,
        verbose_name="evento",
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="estudiante",
        on_delete=models.PROTECT,
        related_name="event_registrations",
    )
    form = models.ForeignKey(
        "dynamicforms.Form",
        verbose_name="formulario",
        on_delete=models.PROTECT,
        related_name="registrations",
    )
    responses = models.JSONField("respuestas", default=list)

    qr_token = models.CharField(
        "token QR",
        max_length=255,
        unique=True,
        help_text="Opaco y firmado por el servidor. Se valida contra la base, "
        "nunca descifrándolo (RNF-05).",
    )
    qr_status = models.CharField(
        "estado del QR", max_length=10, choices=QrStatus.choices, default=QrStatus.ACTIVE
    )
    attendance_status = models.CharField(
        "asistencia",
        max_length=10,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.REGISTERED,
    )

    class Meta:
        verbose_name = "inscripción"
        verbose_name_plural = "inscripciones"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "student"], name="uniq_event_registration"
            ),
        ]
        indexes = [
            models.Index(
                fields=["event", "attendance_status"], name="idx_reg_event_attendance"
            ),
            models.Index(fields=["qr_status"], name="idx_reg_qr_status"),
        ]

    def __str__(self):
        return f"{self.student.enrollment} en {self.event.event_name}"

    @property
    def registered_at(self):
        """Nombre del dominio (MASTER §7.2) para la marca de creación."""
        return self.created_at

    @property
    def is_usable(self):
        return (
            self.qr_status == self.QrStatus.ACTIVE
            and self.attendance_status != self.AttendanceStatus.ATTENDED
        )


class EventAttendance(TimeStampedModel):
    """
    Asistencia registrada. Se crea **solo** al validar un token con éxito.

    Sus datos son inmutables al momento del escaneo (RNF-12): ``scanned_at`` lo
    pone el servidor, nunca el cliente, porque es la evidencia de que alguien
    estuvo ahí.

    ``event`` y ``student`` se duplican desde la inscripción a propósito: RN-6
    se expresa como ``UNIQUE(event_id, student_id)`` **en esta tabla**, que es
    la única defensa real ante dos escaneos simultáneos.
    """

    class Status(models.TextChoices):
        ATTENDED = "Attended", "Asistió"

    registration = models.OneToOneField(
        EventRegistration,
        verbose_name="inscripción",
        on_delete=models.PROTECT,
        related_name="attendance",
    )
    event = models.ForeignKey(
        Event,
        verbose_name="evento",
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="estudiante",
        on_delete=models.PROTECT,
        related_name="event_attendances",
    )
    scanned_at = models.DateTimeField("escaneada el")
    scanned_by_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="escaneada por",
        on_delete=models.SET_NULL,
        null=True,
        related_name="scans_performed",
    )
    qr_token_validated = models.CharField("token validado", max_length=255)
    status = models.CharField(
        "estado", max_length=10, choices=Status.choices, default=Status.ATTENDED
    )

    class Meta:
        verbose_name = "asistencia"
        verbose_name_plural = "asistencias"
        ordering = ["-scanned_at"]
        constraints = [
            # RN-6. Última línea de defensa contra el reescaneo concurrente.
            models.UniqueConstraint(
                fields=["event", "student"], name="uniq_event_attendance"
            ),
        ]

    def __str__(self):
        return f"{self.student.enrollment} asistió a {self.event.event_name}"
