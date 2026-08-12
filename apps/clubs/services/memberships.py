"""Comandos sobre la nómina (CU-CL9..CL12)."""

from apps.academic.models import PaoPeriod
from apps.academic.selectors import get_active_pao
from apps.clubs.models import Club, Membership, Role
from apps.clubs.permissions import BASE_ROLE_NAME
from apps.clubs.services.leadership import assert_can_lead
from core.events import emit
from core.exceptions import BusinessRuleViolation
from core.services import CLEAN_WITHOUT_UNIQUENESS, command


@command
def create_membership(
    *, student, club, role=None, pao_period=None, origin=Membership.Origin.APPLICATION
):
    """
    Alta de membresía (transición M1).

    Es el servicio que usa la aprobación de solicitudes (RF-08): sin rol
    explícito asigna 'Miembro', el rol base sin permisos administrativos.
    """
    pao = pao_period or get_active_pao()

    if role is None:
        role = Role.objects.filter(
            club=club, role_name=BASE_ROLE_NAME, is_active=True
        ).first()
        if role is None:
            raise BusinessRuleViolation(
                f"El club no tiene el rol base '{BASE_ROLE_NAME}'.",
                code="missing_base_role",
            )

    if role.club_id != club.pk:
        raise BusinessRuleViolation(
            "El rol debe pertenecer al mismo club que la membresía (RF-09).",
            code="role_club_mismatch",
            field="role",
        )

    if role.is_leadership:
        assert_can_lead(student, club)

    membership = Membership(
        student=student,
        club=club,
        role=role,
        pao_period=pao,
        valid_from=pao.start_date,
        valid_until=pao.end_date,
        status=Membership.Status.ACTIVE,
        origin=origin,
    )
    membership.full_clean(
        exclude=["leadership_lock"], **CLEAN_WITHOUT_UNIQUENESS
    )
    membership.save()

    emit("membership.created", membership=membership)
    return membership


@command
def set_membership_role(*, membership_id, role_id):
    """
    CU-CL9 — cambio de rol dentro del club (RF-09).

    Una membresía tiene exactamente un rol. Si el destino es directivo hay que
    verificar RN-1 antes, porque el estudiante podría liderar otro club.
    """
    membership = Membership.objects.select_for_update().select_related(
        "club", "student", "role"
    ).get(pk=membership_id)
    _assert_writable(membership.club)

    role = Role.objects.get(pk=role_id)
    if role.club_id != membership.club_id:
        raise BusinessRuleViolation(
            "El rol debe pertenecer al mismo club que la membresía (RF-09).",
            code="role_club_mismatch",
            field="role",
        )
    if not role.is_active:
        raise BusinessRuleViolation(
            "El rol no está vigente y no puede asignarse.", code="role_inactive"
        )

    if role.is_leadership and membership.status == Membership.Status.ACTIVE:
        assert_can_lead(membership.student, membership.club)

    membership.role = role
    # is_leadership se resincroniza dentro de save() a partir del rol.
    membership.save(update_fields=["role", "is_leadership", "updated_at"])

    emit("membership.role_changed", membership=membership)
    return membership


@command
def revoke_membership(*, membership_id):
    """
    CU-CL10 — baja lógica de un miembro (transición M4, RF-19).

    Nunca se borra la fila: la nómina histórica es evidencia auditable ante GBP.
    El liderazgo no se retira por aquí — eso es potestad de GBP (CU-CL13).
    """
    membership = Membership.objects.select_for_update().select_related(
        "club", "student"
    ).get(pk=membership_id)

    if membership.is_leadership:
        raise BusinessRuleViolation(
            "El liderazgo del club solo puede revocarlo GBP.",
            code="leadership_revocation_reserved",
        )
    if membership.status == Membership.Status.REVOKED:
        raise BusinessRuleViolation(
            "La membresía ya estaba revocada.", code="membership_already_revoked"
        )

    membership.status = Membership.Status.REVOKED
    membership.save(update_fields=["status", "is_leadership", "updated_at"])

    emit("membership.revoked", membership=membership)
    return membership


@command
def renew_roster(*, club_id, membership_ids, pao_period=None):
    """
    CU-CL12 — renovación de la nómina para el nuevo PAO (RF-21, transición M5).

    Crea membresías **nuevas** en el período vigente copiando estudiante y rol.
    No reactiva las anteriores: la membresía del PAO cerrado permanece
    ``Frozen`` como evidencia de ese período, que es justamente lo que hace
    consultable el histórico de RF-49.

    Idempotente: reejecutarla con los mismos ids no duplica, porque la unicidad
    (estudiante, club, período) lo impide y las ya renovadas se omiten.
    """
    club = Club.objects.get(pk=club_id)
    _assert_writable(club)

    target = pao_period or get_active_pao()

    if not membership_ids:
        raise BusinessRuleViolation(
            "Selecciona al menos un miembro para renovar.",
            code="empty_renewal",
            field="membership_ids",
        )

    source = (
        Membership.objects.filter(pk__in=membership_ids, club=club)
        .select_related("student", "role", "pao_period")
        .order_by("pk")
    )

    renewed, skipped = [], []
    for membership in source:
        if membership.pao_period_id == target.pk:
            skipped.append(membership)
            continue
        if membership.status == Membership.Status.REVOKED:
            # Una membresía revocada no se arrastra al período siguiente: la
            # baja fue una decisión, no un vencimiento.
            skipped.append(membership)
            continue

        already = Membership.objects.filter(
            student=membership.student, club=club, pao_period=target
        ).first()
        if already:
            skipped.append(membership)
            continue

        role = membership.role if membership.role.is_active else None
        new_membership = create_membership(
            student=membership.student,
            club=club,
            role=role,
            pao_period=target,
            origin=Membership.Origin.RENEWAL,
        )
        renewed.append(new_membership)

    emit("membership.renewed", club=club, pao_period=target, memberships=renewed)
    return {"renewed": renewed, "skipped": skipped}


@command
def freeze_expired_memberships(*, today, notify=True):
    """
    Transición M2 (RF-20, RN-4) — congelamiento al cerrar el PAO.

    Idempotente: solo toca membresías ``Active`` ya vencidas, así que ejecutarla
    dos veces no produce efectos adicionales. Recibe ``today`` como parámetro en
    vez de leer el reloj, para que las pruebas sean deterministas.

    Los ids se recogen **antes** del UPDATE porque después ya no cumplen el
    filtro y no habría forma de saber a quién avisar. ``notify=False`` permite
    congelar sin emitir avisos, que es lo que necesita el sembrado de datos
    históricos: nadie debe recibir una notificación de 2025.
    """
    expired = Membership.objects.filter(
        status=Membership.Status.ACTIVE, valid_until__lt=today
    )
    affected_ids = list(expired.values_list("pk", flat=True))
    count = expired.update(status=Membership.Status.FROZEN)

    if notify and affected_ids:
        for membership in Membership.objects.filter(
            pk__in=affected_ids
        ).select_related("student", "club"):
            emit("membership.frozen", membership=membership)

    return count


@command
def expire_stale_memberships(*, today=None):
    """
    Transición M3 (RF-19) — cierre definitivo de las no renovadas.

    Una membresía congelada expira cuando su período está cerrado y el
    estudiante no tiene membresía en ningún período posterior de ese club.
    """
    frozen = Membership.objects.filter(
        status=Membership.Status.FROZEN,
        pao_period__status=PaoPeriod.Status.CLOSED,
    ).select_related("pao_period")

    expired_ids = []
    for membership in frozen:
        renewed_later = Membership.objects.filter(
            student_id=membership.student_id,
            club_id=membership.club_id,
            pao_period__sequence__gt=membership.pao_period.sequence,
        ).exists()
        if not renewed_later:
            expired_ids.append(membership.pk)

    if expired_ids:
        Membership.objects.filter(pk__in=expired_ids).update(
            status=Membership.Status.EXPIRED
        )
    return len(expired_ids)


def _assert_writable(club):
    if club.is_read_only:
        raise BusinessRuleViolation(
            "El club está sin líder asignado y permanece en solo lectura.",
            code="club_read_only",
        )
