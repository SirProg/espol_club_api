"""
Consultas sobre clubes y nóminas.

Ninguna muta estado. Las que alimentan listados resuelven los conteos con
anotaciones y traen las relaciones por adelantado: la pantalla de catálogo
muestra decenas de clubes y la de nómina decenas de miembros, y sin esto cada
fila dispararía consultas adicionales.
"""

from django.db.models import Count, Prefetch, Q

from apps.clubs.models import Club, ClubDocument, Membership, Role


def _with_member_count(queryset):
    """Anota el conteo de miembros activos (RF-47: el número, no las identidades)."""
    return queryset.annotate(
        active_members=Count(
            "memberships",
            filter=Q(memberships__status=Membership.Status.ACTIVE),
            distinct=True,
        )
    )


def list_clubs(*, search=None, faculty_id=None, interest_area_id=None):
    """
    CU-CL15 — catálogo filtrable (RF-46).

    Es la consulta más frecuente del sistema y la funcionalidad que MASTER §1.3
    declara prioritaria, así que los tres filtros se apoyan en índices: ``status``
    y ``faculty`` tienen índice propio, y el área resuelve por la tabla puente
    en vez de escanear un JSON.
    """
    queryset = (
        Club.objects.select_related("faculty", "leader")
        .prefetch_related("interest_areas")
        .order_by("name")
    )

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(acronym__icontains=search)
        )
    if faculty_id:
        queryset = queryset.filter(faculty_id=faculty_id)
    if interest_area_id:
        queryset = queryset.filter(interest_areas__id=interest_area_id)

    return _with_member_count(queryset).distinct()


def get_club(club_id):
    return (
        _with_member_count(
            Club.objects.select_related("faculty", "leader").prefetch_related(
                "interest_areas"
            )
        )
        .filter(pk=club_id)
        .first()
    )


def get_global_catalog():
    """CU-CL7 de GBP — clubes con líder resuelto y conteo (RF-49)."""
    return _with_member_count(
        Club.objects.select_related("faculty", "leader").order_by("name")
    )


def get_club_roles(club_id, *, only_active=True):
    queryset = Role.objects.filter(club_id=club_id)
    if only_active:
        queryset = queryset.filter(is_active=True)
    return queryset.order_by("-is_leadership", "role_name")


def get_club_members(club_id, *, only_active=True, pao_period=None):
    """
    CU-CL11 — nómina detallada (RF-48).

    **Quién puede llamarla se decide arriba**, con ``can_see_roster``. Este
    selector no filtra por privacidad: devuelve la nómina completa. Envolverlo
    en una comprobación de permisos aquí escondería la decisión y haría fácil
    olvidarla en la siguiente pantalla que lo use.
    """
    queryset = Membership.objects.filter(club_id=club_id).select_related(
        "student", "student__faculty", "role", "pao_period"
    )
    if only_active:
        queryset = queryset.filter(status=Membership.Status.ACTIVE)
    if pao_period:
        queryset = queryset.filter(pao_period_id=pao_period)
    return queryset.order_by("-role__is_leadership", "student__last_name")


def get_roster(club_id, pao_period):
    """CU-CL11 — nómina consolidada de un período concreto (RF-39)."""
    return get_club_members(club_id, only_active=False, pao_period=pao_period)


def get_membership(student, club_id):
    """Membresía vigente del estudiante en el club, si la tiene."""
    if not student or not student.is_authenticated:
        return None
    return (
        Membership.objects.filter(
            student=student, club_id=club_id, status=Membership.Status.ACTIVE
        )
        .select_related("role", "club")
        .first()
    )


def get_active_memberships(student):
    """Todas las membresías vigentes del estudiante, con rol y club resueltos."""
    if not student or not student.is_authenticated:
        return Membership.objects.none()
    return Membership.objects.filter(
        student=student, status=Membership.Status.ACTIVE
    ).select_related("role", "club")


def is_active_member(student, club_id):
    return get_membership(student, club_id) is not None


def get_club_documents(club_id, *, include_private=False):
    """
    RF-16 — los documentos privados son exclusivos de los miembros del club.

    Por defecto devuelve solo los públicos: si quien llama olvida pasar el flag,
    el error es de menos información, no de fuga de datos.
    """
    queryset = ClubDocument.objects.filter(club_id=club_id)
    if not include_private:
        queryset = queryset.filter(is_public=True)
    return queryset.order_by("title")


def get_led_club(student):
    """Club que lidera el estudiante, o None. RN-1 garantiza que sea uno solo."""
    membership = (
        Membership.objects.filter(
            student=student, status=Membership.Status.ACTIVE, is_leadership=True
        )
        .select_related("club")
        .first()
    )
    return membership.club if membership else None


def clubs_pending_for_enrollment(enrollment):
    """Clubes que esperan a que esa matrícula se registre (soporte de RF-12)."""
    return Club.objects.filter(
        leader_enrollment=enrollment, status=Club.Status.PENDING_LEADER
    )
