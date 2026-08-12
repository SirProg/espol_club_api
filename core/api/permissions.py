"""
Clases de permiso de DRF.

Son envoltorios delgados sobre ``apps.clubs.policies``: la decisión de
autorización vive allí, en funciones puras que también usan el admin y los
management commands. Aquí solo se traduce a la interfaz que espera DRF.

Esa separación importa porque el sistema tiene tres entradas (API, admin,
comandos) y una regla que solo viviera en una clase de permiso de DRF no
protegería a las otras dos.
"""

from rest_framework.permissions import BasePermission

from apps.clubs import policies


class IsGbpAdmin(BasePermission):
    """Perfil institucional. Audita y valida; no edita el interior de un club."""

    message = "Esta acción está reservada a la Gerencia de Bienestar Politécnico."

    def has_permission(self, request, view):
        return policies.is_gbp_admin(request.user)


class IsClubMember(BasePermission):
    """Membresía vigente en el club de la ruta."""

    message = "Debes ser miembro del club para ver esta información."

    def has_permission(self, request, view):
        club_id = view.get_club_id()
        return policies.is_club_member(request.user, club_id)


class CanSeeRoster(BasePermission):
    """RN-3 / RF-48 — la nómina detallada es de los miembros y de GBP."""

    message = "La lista de miembros solo está disponible para el club y para GBP."

    def has_permission(self, request, view):
        return policies.can_see_roster(request.user, view.get_club_id())


class HasClubPermission(BasePermission):
    """
    Exige un permiso granular del rol dentro del club (§8.2).

    La vista declara cuál necesita::

        class FormListCreateView(ClubScopedView):
            required_club_permission = ClubPermission.MANAGE_FORMS

    Las lecturas seguras (GET, HEAD, OPTIONS) pueden eximirse con
    ``club_permission_on_write_only = True``, para vistas que cualquiera del
    club puede leer pero solo la directiva puede modificar.
    """

    message = "Tu rol en el club no incluye el permiso necesario para esta acción."

    def has_permission(self, request, view):
        required = getattr(view, "required_club_permission", None)
        if required is None:
            return True

        if (
            getattr(view, "club_permission_on_write_only", False)
            and request.method in ("GET", "HEAD", "OPTIONS")
        ):
            return True

        return policies.has_club_permission(request.user, view.get_club_id(), required)


class IsSelf(BasePermission):
    """F-07 — cada quien edita solo su propio perfil."""

    message = "Solo puedes modificar tu propio perfil."

    def has_object_permission(self, request, view, obj):
        return policies.is_self(request.user, getattr(obj, "pk", None))
