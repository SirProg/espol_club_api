"""Rutas de solicitudes de membresía."""

from django.urls import path, re_path

from api.v1.applications.views import (
    ApplicationResolutionView,
    CanApplyView,
    ClubApplicationsView,
    MyApplicationsView,
)

club_application_urlpatterns = [
    path(
        "<int:club_id>/applications/",
        ClubApplicationsView.as_view(),
        name="list-create",
    ),
    path(
        "<int:club_id>/applications/can-apply/",
        CanApplyView.as_view(),
        name="can-apply",
    ),
]

application_urlpatterns = [
    # La acción va en la URL y se restringe a las dos válidas: con un str libre,
    # una ruta como /applications/1/borrar/ llegaría a la vista y caería en la
    # rama de rechazo por descarte.
    re_path(
        r"^(?P<application_id>\d+)/(?P<action>approve|reject)/$",
        ApplicationResolutionView.as_view(),
        name="resolve",
    ),
]

student_application_urlpatterns = [
    path("me/applications/", MyApplicationsView.as_view(), name="my-applications"),
]
