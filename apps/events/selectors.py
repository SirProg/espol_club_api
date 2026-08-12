"""Consultas sobre eventos, inscripciones y asistencia."""

from django.db.models import Count, Q

from apps.events.models import Event, EventAttendance, EventRegistration, EventStaff


def _with_stats(queryset):
    """
    Anota inscritos y asistentes (RF-38).

    Se resuelve con anotaciones y no con la propiedad ``stats`` del modelo: la
    tabla de eventos del panel muestra ambas cifras por fila, y una consulta por
    fila multiplicaría el coste por el número de eventos del club.
    """
    return queryset.annotate(
        registered_count=Count("registrations", distinct=True),
        attended_count=Count("attendances", distinct=True),
    )


def get_visible_events(student=None, *, club_id=None, upcoming_only=False):
    """
    CU-EV4 — eventos visibles (RF-31).

    Devuelve **todos**, incluidos los ``MembersOnly``. No es un descuido: MASTER
    §20.7 lo confirma como diseño. Lo que se bloquea es el registro, no la
    existencia del evento; ocultarlos impediría descubrir que el club hace
    cosas.
    """
    queryset = Event.objects.select_related("club", "registration_form").order_by(
        "-start_datetime"
    )
    if club_id:
        queryset = queryset.filter(club_id=club_id)
    if upcoming_only:
        from django.utils import timezone

        queryset = queryset.filter(end_datetime__gte=timezone.now())
    return _with_stats(queryset)


def get_event(event_id):
    return (
        _with_stats(Event.objects.select_related("club", "registration_form"))
        .filter(pk=event_id)
        .first()
    )


def get_club_events(club_id):
    """CU-EV11 — histórico del club con sus métricas."""
    return _with_stats(
        Event.objects.filter(club_id=club_id).select_related("registration_form")
    ).order_by("-start_datetime")


def get_event_staff(event_id):
    return EventStaff.objects.filter(event_id=event_id).select_related(
        "student", "assigned_by"
    )


def is_event_staff(student, event_id):
    if not student or not student.is_authenticated:
        return False
    return EventStaff.objects.filter(event_id=event_id, student=student).exists()


def get_event_registrations(event_id):
    """
    CU-EV10 — bitácora de inscritos (pantalla 34).

    Resuelve PPD-04: la bitácora es la lista de inscritos de **un evento
    seleccionable**, con su estado de asistencia. La deuda de MASTER §20.10 era
    que la Fase 1 mostraba siempre el primer evento del club, sin selector.
    """
    return (
        EventRegistration.objects.filter(event_id=event_id)
        .select_related("student", "student__faculty")
        .order_by("created_at")
    )


def get_student_registrations(student, *, only_usable=False):
    """Credenciales del estudiante (pantalla 12)."""
    if not student or not student.is_authenticated:
        return EventRegistration.objects.none()

    queryset = EventRegistration.objects.filter(student=student).select_related(
        "event", "event__club"
    )
    if only_usable:
        queryset = queryset.filter(qr_status=EventRegistration.QrStatus.ACTIVE)
    return queryset.order_by("-event__start_datetime")


def get_student_attendances(student):
    """Historial de asistencias del estudiante (RF-50)."""
    if not student or not student.is_authenticated:
        return EventAttendance.objects.none()
    return EventAttendance.objects.filter(student=student).select_related(
        "event", "event__club"
    )


def get_registration_by_token(token):
    return (
        EventRegistration.objects.select_related("event", "student")
        .filter(qr_token=token)
        .first()
    )


def eligible_staff_candidates(event):
    """
    Miembros activos del club que pueden asignarse como staff (F-14).

    Alimenta la pantalla 25, que muestra disponibles frente a asignados.
    """
    from apps.clubs.models import Membership

    return Membership.objects.filter(
        club_id=event.club_id, status=Membership.Status.ACTIVE
    ).select_related("student", "role")


def event_attendance_summary(event_id):
    """Resumen para el detalle de un evento (V-17)."""
    registrations = EventRegistration.objects.filter(event_id=event_id)
    return {
        "registered": registrations.count(),
        "attended": registrations.filter(
            attendance_status=EventRegistration.AttendanceStatus.ATTENDED
        ).count(),
        "no_show": registrations.filter(
            attendance_status=EventRegistration.AttendanceStatus.NO_SHOW
        ).count(),
        "pending": registrations.filter(
            attendance_status=EventRegistration.AttendanceStatus.REGISTERED
        ).count(),
    }
