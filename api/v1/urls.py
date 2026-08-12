"""
Rutas de la versión 1 de la API.

La versión va en la URL y no en una cabecera para que sea evidente en cualquier
log, en cualquier captura del navegador y en el código del cliente. Cuando haya
una v2, ambas conviven sin que la app móvil publicada deje de funcionar.

Las rutas se agrupan por **recurso**, no por app: ``/clubs/{id}/forms/`` y
``/clubs/{id}/applications/`` viven en apps distintas pero cuelgan del mismo
club, y así es como las consume el cliente.
"""

from django.urls import include, path

from api.v1.accounts.urls import auth_urlpatterns, student_urlpatterns
from api.v1.applications.urls import (
    application_urlpatterns,
    club_application_urlpatterns,
    student_application_urlpatterns,
)
from api.v1.clubs.urls import club_document_urlpatterns, club_urlpatterns as club_base_urlpatterns
from api.v1.clubs.urls import membership_urlpatterns, role_urlpatterns
from api.v1.dynamicforms.urls import club_form_urlpatterns, form_urlpatterns
from api.v1.notifications.urls import notification_urlpatterns
from api.v1.gbp.urls import club_process_urlpatterns, gbp_urlpatterns
from api.v1.events.urls import (
    attendance_urlpatterns,
    club_event_urlpatterns,
    event_urlpatterns,
    student_event_urlpatterns,
)

app_name = "v1"

club_urlpatterns = (
    club_base_urlpatterns
    + club_form_urlpatterns
    + club_application_urlpatterns
    + club_event_urlpatterns
    + club_process_urlpatterns
)
me_urlpatterns = (
    student_urlpatterns + student_application_urlpatterns + student_event_urlpatterns
)

urlpatterns = [
    path("auth/", include((auth_urlpatterns, "auth"))),
    path("students/", include((me_urlpatterns, "students"))),
    path("catalogs/", include("api.v1.catalogs.urls")),
    path("clubs/", include((club_urlpatterns, "clubs"))),
    path("forms/", include((form_urlpatterns, "forms"))),
    path("applications/", include((application_urlpatterns, "applications"))),
    path("events/", include((event_urlpatterns, "events"))),
    path("attendance/", include((attendance_urlpatterns, "attendance"))),
    path("roles/", include((role_urlpatterns, "roles"))),
    path("memberships/", include((membership_urlpatterns, "memberships"))),
    path("club-documents/", include((club_document_urlpatterns, "club-documents"))),
    path("gbp/", include((gbp_urlpatterns, "gbp"))),
    path("notifications/", include((notification_urlpatterns, "notifications"))),
]
