"""
Decisiones de autorización por club (LOGICA_NEGOCIO.md §8).

Funciones puras: reciben un actor y un objeto, devuelven ``True`` o ``False``.
No consultan el request ni conocen HTTP, de modo que sirven igual a la API, al
admin y a los management commands. Las clases de permiso de DRF (Etapa 4) serán
envoltorios delgados sobre estas funciones.

Dos planos independientes:

* **Institucional** — ``is_gbp_admin``. Da acceso al panel de GBP y a la
  auditoría. **No** otorga permisos dentro de un club: GBP audita y valida, no
  edita el interior de las organizaciones (MASTER §3.1).
* **De club** — ``Membership.role.permissions``. Único origen de los permisos
  operativos, y siempre acotado a un club concreto.
"""

from apps.clubs.selectors import get_membership


def is_authenticated(user):
    return bool(user and user.is_authenticated)


def is_gbp_admin(user):
    return is_authenticated(user) and user.is_gbp_admin


def is_club_member(user, club_id):
    return get_membership(user, club_id) is not None


def has_club_permission(user, club_id, permission):
    """
    El predicado central del sistema.

    Incluye deliberadamente la comprobación de que el club esté activo: así el
    invariante I-19 (un club sin líder está en solo lectura) se cumple en todas
    las operaciones sin repetirlo en cada vista, que es exactamente donde se
    olvidaría.
    """
    membership = get_membership(user, club_id)
    if membership is None:
        return False
    if membership.club.is_read_only:
        return False
    return membership.has_permission(permission)


def can_see_roster(user, club_id):
    """
    RN-3 / RF-48 — quién ve la nómina detallada.

    Los no miembros solo reciben el contador agregado. Es la regla que separa
    ``ClubPublicSerializer`` de ``ClubInternalSerializer`` en la Etapa 4.
    """
    return is_gbp_admin(user) or is_club_member(user, club_id)


def can_see_private_documents(user, club_id):
    """RF-16 — los documentos privados son de los miembros y de GBP."""
    return can_see_roster(user, club_id)


def is_self(user, student_id):
    """F-07 — cada quien edita solo su propio perfil."""
    return is_authenticated(user) and user.pk == student_id


def can_manage_club(user, club_id, permission):
    """
    Alias explícito para las escrituras del club.

    GBP **no** entra por aquí: no puede editar el interior de un club aunque sea
    administrador institucional.
    """
    return has_club_permission(user, club_id, permission)
