"""Rutas de formularios dinámicos."""

from django.urls import path, re_path

from api.v1.dynamicforms.views import (
    ClubFormListCreateView,
    FormActivationView,
    FormDetailView,
    FormValidateView,
    FormVersionView,
    MembershipFormView,
)

# Rutas colgadas de un club concreto.
club_form_urlpatterns = [
    path("<int:club_id>/forms/", ClubFormListCreateView.as_view(), name="list-create"),
    path(
        "<int:club_id>/forms/membership/",
        MembershipFormView.as_view(),
        name="membership",
    ),
]

# Rutas sobre un formulario, sin el club en la URL: su identidad ya lo
# determina, y repetirlo abriría la puerta a incoherencias entre ambos.
form_urlpatterns = [
    path("<int:form_id>/", FormDetailView.as_view(), name="detail"),
    path("<int:form_id>/versions/", FormVersionView.as_view(), name="versions"),
    path("<int:form_id>/validate/", FormValidateView.as_view(), name="validate"),
    # La acción se restringe en la propia ruta: con un <str:action> libre,
    # /forms/1/borrar/ llegaría a la vista y caería en la rama de desactivar
    # por descarte, ejecutando algo que nadie pidió.
    re_path(
        r"^(?P<form_id>\d+)/(?P<action>activate|deactivate)/$",
        FormActivationView.as_view(),
        name="activation",
    ),
]
