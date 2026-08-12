"""Rutas de eventos, credenciales y asistencia."""

from django.urls import path

from api.v1.events.views import (
    AttendanceScanView,
    CanRegisterView,
    ClubEventsView,
    EventDetailView,
    EventListView,
    EventRegistrationLogView,
    EventRegistrationView,
    EventStaffView,
    MyCredentialsView,
)

event_urlpatterns = [
    path("", EventListView.as_view(), name="list"),
    path("<int:event_id>/", EventDetailView.as_view(), name="detail"),
    path("<int:event_id>/staff/", EventStaffView.as_view(), name="staff"),
    path("<int:event_id>/register/", EventRegistrationView.as_view(), name="register"),
    path(
        "<int:event_id>/can-register/", CanRegisterView.as_view(), name="can-register"
    ),
    path(
        "<int:event_id>/registrations/",
        EventRegistrationLogView.as_view(),
        name="registrations",
    ),
]

club_event_urlpatterns = [
    path("<int:club_id>/events/", ClubEventsView.as_view(), name="club-events"),
]

student_event_urlpatterns = [
    path("me/registrations/", MyCredentialsView.as_view(), name="my-credentials"),
]

attendance_urlpatterns = [
    path("scan/", AttendanceScanView.as_view(), name="scan"),
]
