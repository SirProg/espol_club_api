"""
Ciclo de vida del liderazgo (CU-CL13, CU-CL14 — transiciones C1..C5).

Es el servicio que hace cumplir RN-1: un estudiante lidera un solo club a la
vez. La regla cruza clubes distintos, así que no cabe en el agregado Club; vive
aquí, y la base la respalda con el índice único ``uniq_active_leadership_per_student``.
"""

from django.contrib.auth import get_user_model

from apps.academic.selectors import get_active_pao
from apps.clubs.models import Club, Membership, Role
from apps.clubs.permissions import PRESIDENT_ROLE_NAME
from core.events import emit
from core.exceptions import BusinessRuleViolation
from core.services import command

Student = get_user_model()


def assert_can_lead(student, club):
    """
    RN-1 — verificación previa, con mensaje legible.

    El índice único es la defensa real ante concurrencia; esto existe para que
    el caso normal produzca un error que explique qué pasó y en qué club.
    """
    conflict = (
        Membership.objects.filter(
            student=student,
            status=Membership.Status.ACTIVE,
            is_leadership=True,
        )
        .exclude(club=club)
        .select_related("club")
        .first()
    )
    if conflict:
        raise BusinessRuleViolation(
            f"{student.get_full_name()} ya lidera {conflict.club.acronym}. "
            "Un líder administra un solo club a la vez (RN-1).",
            code="leadership_exclusivity",
            field="leader_enrollment",
        )


@command
def assign_leader(*, club_id, enrollment):
    """
    CU-CL14 — GBP designa (o redesigna) al líder de un club.

    Transición C1/C4 si la matrícula tiene cuenta; C2 si no, y entonces el club
    queda en ``Pending Leader`` esperando que esa persona se registre (RF-12).
    """
    club = Club.objects.select_for_update().get(pk=club_id)
    enrollment = (enrollment or "").strip().upper()
    if not enrollment:
        raise BusinessRuleViolation(
            "Debes indicar la matrícula del líder.",
            code="missing_leader_enrollment",
            field="leader_enrollment",
        )

    club.leader_enrollment = enrollment
    student = Student.objects.filter(enrollment=enrollment).first()

    if student is None:
        # C2: la matrícula queda comprometida pero sin cuenta. El club espera
        # en solo lectura; activate_pending_leadership lo despertará.
        _revoke_current_leadership(club)
        club.leader = None
        club.status = Club.Status.PENDING_LEADER
        club.save(
            update_fields=["leader_enrollment", "leader", "status", "updated_at"]
        )
        emit("club.leader_pending", club=club, enrollment=enrollment)
        return club

    assert_can_lead(student, club)

    _revoke_current_leadership(club, keep_student=student)
    membership = _grant_leadership(club, student)

    club.leader = student
    club.status = Club.Status.ACTIVE
    club.save(update_fields=["leader_enrollment", "leader", "status", "updated_at"])

    emit("club.leader_assigned", club=club, student=student, membership=membership)
    return club


@command
def revoke_leader(*, club_id):
    """
    CU-CL13 — GBP retira el liderazgo (RF-13, transición C5).

    La membresía directiva pasa a ``Revoked``, con lo que se libera RN-1 y esa
    persona puede liderar otro club. El club queda en solo lectura.
    """
    club = Club.objects.select_for_update().get(pk=club_id)
    if club.leader_id is None:
        raise BusinessRuleViolation(
            "El club no tiene un líder asignado.", code="club_without_leader"
        )

    former_leader = club.leader
    _revoke_current_leadership(club)

    club.leader = None
    club.status = Club.Status.PENDING_LEADER
    club.save(update_fields=["leader", "status", "updated_at"])

    emit("club.leader_revoked", club=club, student=former_leader)
    return club


@command
def activate_pending_leadership(student):
    """
    RF-12 / transición C3 — activación diferida.

    Se dispara cuando alguien completa su registro: si GBP había comprometido su
    matrícula como líder de un club sin resolver, el vínculo se materializa
    ahora. Este es el consumidor del evento ``student.verified``.
    """
    clubs = Club.objects.select_for_update().filter(
        leader_enrollment=student.enrollment,
        status=Club.Status.PENDING_LEADER,
    )

    activated = []
    for club in clubs:
        try:
            assert_can_lead(student, club)
        except BusinessRuleViolation:
            # Si ya lidera otro club, el compromiso pendiente no puede
            # materializarse solo; queda para que GBP lo resuelva a mano.
            continue

        membership = _grant_leadership(club, student)
        club.leader = student
        club.status = Club.Status.ACTIVE
        club.save(update_fields=["leader", "status", "updated_at"])
        emit("club.leader_assigned", club=club, student=student, membership=membership)
        activated.append(club)

    return activated


def _grant_leadership(club, student):
    """Crea o reactiva la membresía de Presidente/a para ``student`` en ``club``."""
    role = Role.objects.filter(
        club=club, role_name=PRESIDENT_ROLE_NAME
    ).first()
    if role is None:
        raise BusinessRuleViolation(
            f"El club no tiene el rol '{PRESIDENT_ROLE_NAME}'. Debió crearse al "
            "dar de alta el club.",
            code="missing_president_role",
        )

    pao = get_active_pao()

    membership, _ = Membership.objects.update_or_create(
        student=student,
        club=club,
        pao_period=pao,
        defaults={
            "role": role,
            "valid_from": pao.start_date,
            "valid_until": pao.end_date,
            "status": Membership.Status.ACTIVE,
            "origin": Membership.Origin.LEADER_ASSIGNMENT,
        },
    )
    return membership


def _revoke_current_leadership(club, keep_student=None):
    """
    Revoca las membresías directivas vigentes del club.

    Se ejecuta **antes** de conceder el nuevo liderazgo: de lo contrario el
    índice único de RN-1 dispararía contra el líder saliente. Es el mismo orden
    que exige ``activate_pao`` al cerrar los períodos.
    """
    current = club.memberships.filter(
        status=Membership.Status.ACTIVE, is_leadership=True
    )
    if keep_student is not None:
        current = current.exclude(student=keep_student)

    for membership in current:
        membership.status = Membership.Status.REVOKED
        membership.save(update_fields=["status", "updated_at"])
        emit("membership.revoked", membership=membership)
