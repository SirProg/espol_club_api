"""Consultas sobre solicitudes de membresía."""

from apps.applications.models import MembershipApplication


def _base_queryset():
    # Cada fila de la bandeja muestra estudiante, club, formulario y quién
    # resolvió: sin esto, una bandeja de 30 solicitudes dispara 120 consultas.
    return MembershipApplication.objects.select_related(
        "student", "student__faculty", "club", "form", "resolved_by"
    )


def get_club_applications(club_id, *, status=None):
    """CU-AP3 — bandeja del líder (RF-26)."""
    queryset = _base_queryset().filter(club_id=club_id)
    if status:
        queryset = queryset.filter(status=status)
    return queryset.order_by("-created_at")


def get_application(application_id):
    return _base_queryset().filter(pk=application_id).first()


def get_student_applications(student):
    """Historial de postulaciones del estudiante (RF-50)."""
    if not student or not student.is_authenticated:
        return MembershipApplication.objects.none()
    return _base_queryset().filter(student=student).order_by("-created_at")


def get_pending_application(student, club_id):
    if not student or not student.is_authenticated:
        return None
    return (
        MembershipApplication.objects.filter(
            student=student,
            club_id=club_id,
            status=MembershipApplication.Status.PENDING,
        )
        .select_related("form")
        .first()
    )


def count_pending(club_id):
    """Contador para el panel del líder."""
    return MembershipApplication.objects.filter(
        club_id=club_id, status=MembershipApplication.Status.PENDING
    ).count()
