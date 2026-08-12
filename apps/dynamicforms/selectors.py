"""Consultas sobre formularios. No mutan estado."""

from django.db.models import Q

from apps.dynamicforms.models import Form


def get_club_forms(club_id, *, form_type=None, only_active=False):
    queryset = Form.objects.filter(club_id=club_id).select_related("club")
    if form_type:
        queryset = queryset.filter(form_type=form_type)
    if only_active:
        queryset = queryset.filter(is_active=True)
    return queryset.order_by("form_type", "-version")


def get_form(form_id):
    return Form.objects.select_related("club").filter(pk=form_id).first()


def get_active_membership_form(club_id):
    """
    RF-25 — el formulario que la app móvil renderiza para postular.

    Se toma la versión vigente más alta: si por algún camino quedaran dos
    activas, la más nueva es la respuesta correcta y no un error que deba
    bloquear al estudiante.
    """
    return (
        Form.objects.filter(
            club_id=club_id,
            form_type=Form.FormType.MEMBERSHIP,
            is_active=True,
        )
        .order_by("-version")
        .first()
    )


def get_form_family(form):
    """Todas las versiones del formulario, de la más reciente a la más antigua."""
    root_id = form.family_id
    return Form.objects.filter(Q(pk=root_id) | Q(root_id=root_id)).order_by("-version")
