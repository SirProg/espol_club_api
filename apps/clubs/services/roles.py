"""Comandos sobre los roles internos del club (CU-CL6..CL8)."""

from apps.clubs.models import Club, Membership, Role
from apps.clubs.permissions import ClubPermission
from core.exceptions import BusinessRuleViolation
from core.services import CLEAN_WITHOUT_UNIQUENESS, command


@command
def create_role(*, club_id, role_name, is_leadership=False, permissions=None):
    """
    CU-CL6 — rol personalizado (RF-07).

    RN-7 se valida en ``Role.clean()``: ``manage_roles`` solo puede otorgarse a
    roles directivos, porque es la capacidad de repartir capacidades.
    """
    club = Club.objects.get(pk=club_id)
    _assert_writable(club)

    role = Role(
        club=club,
        role_name=role_name.strip(),
        is_default=False,
        is_leadership=is_leadership,
        permissions=permissions or {},
    )
    role.full_clean(**CLEAN_WITHOUT_UNIQUENESS)
    role.save()
    return role


@command
def update_role(*, role_id, role_name=None, is_leadership=None, permissions=None):
    """
    CU-CL7 — edición de un rol.

    Los cuatro roles por defecto no admiten cambios estructurales (nombre ni
    condición de directivo): 'Miembro' es el destino de toda solicitud aprobada
    y 'Presidente/a' el del liderazgo, así que renombrarlos rompería RF-08 y la
    asignación de líder. Sus permisos sí son ajustables.
    """
    role = Role.objects.select_related("club").get(pk=role_id)
    _assert_writable(role.club)

    if role.is_default and (role_name is not None or is_leadership is not None):
        raise BusinessRuleViolation(
            "Los roles predeterminados no se pueden renombrar ni cambiar de "
            "condición directiva. Sus permisos sí son editables.",
            code="default_role_is_structural",
        )

    if role_name is not None:
        role.role_name = role_name.strip()
    if permissions is not None:
        role.permissions = permissions

    leadership_changed = False
    if is_leadership is not None and is_leadership != role.is_leadership:
        role.is_leadership = is_leadership
        leadership_changed = True

    role.full_clean(**CLEAN_WITHOUT_UNIQUENESS)
    role.save()

    if leadership_changed:
        _resync_leadership_snapshots(role)

    return role


@command
def deactivate_role(*, role_id):
    """CU-CL8 (variante) — retira un rol de circulación sin borrarlo (D-13)."""
    role = Role.objects.select_related("club").get(pk=role_id)
    _assert_writable(role.club)

    if role.is_default:
        raise BusinessRuleViolation(
            "Los roles predeterminados no se pueden desactivar.",
            code="default_role_protected",
        )

    role.is_active = False
    role.save(update_fields=["is_active", "updated_at"])
    return role


@command
def delete_role(*, role_id):
    """
    CU-CL8 — elimina un rol.

    Solo si nunca tuvo membresías: en caso contrario se desactiva, para no
    dejar ilegible la nómina histórica que lo usaba (decisión D-13).
    """
    role = Role.objects.select_related("club").get(pk=role_id)
    _assert_writable(role.club)

    if role.is_default:
        raise BusinessRuleViolation(
            "Los roles predeterminados no se pueden eliminar.",
            code="default_role_protected",
        )

    if is_role_in_use(role_id):
        raise BusinessRuleViolation(
            "El rol está asignado a membresías del club. Desactívalo en vez de "
            "eliminarlo para conservar el historial.",
            code="role_in_use",
        )

    role.delete()


def is_role_in_use(role_id):
    """¿Existe alguna membresía —vigente o histórica— con este rol?"""
    return Membership.objects.filter(role_id=role_id).exists()


def _resync_leadership_snapshots(role):
    """
    Reescribe ``Membership.is_leadership`` de las membresías del rol.

    Sin esto, cambiar el flag del rol dejaría los snapshots desalineados y el
    índice único de RN-1 estaría vigilando un dato obsoleto (decisión D-05).

    Se hace fila por fila y no con un UPDATE masivo a propósito: si el cambio
    convierte en directivo a un rol con varios miembros, y alguno de ellos ya
    lidera otro club, debe fallar el índice y abortar toda la transacción en vez
    de dejar el sistema con dos liderazgos.
    """
    for membership in role.memberships.all():
        membership.save(update_fields=["is_leadership", "updated_at"])


def _assert_writable(club):
    if club.is_read_only:
        raise BusinessRuleViolation(
            "El club está sin líder asignado y permanece en solo lectura.",
            code="club_read_only",
        )


def can_grant_manage_roles(actor_membership):
    """
    RN-7 — quién puede repartir el permiso ``manage_roles``.

    Solo quien ya lo tiene, y solo si su rol es directivo. En la práctica es el
    Presidente/a, salvo delegación explícita.
    """
    return (
        actor_membership is not None
        and actor_membership.is_current
        and actor_membership.role.is_leadership
        and actor_membership.role.has(ClubPermission.MANAGE_ROLES)
    )
