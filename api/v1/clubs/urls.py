"""Rutas de clubes, roles, nómina y documentos."""

from django.urls import path, re_path

from api.v1.clubs.views import (
    ClubDetailView,
    ClubDocumentDetailView,
    ClubDocumentsView,
    ClubLeaderView,
    ClubListCreateView,
    ClubMembersView,
    ClubRolesView,
    ClubRosterView,
    MembershipDetailView,
    RoleDetailView,
)

club_urlpatterns = [
    path("", ClubListCreateView.as_view(), name="list-create"),
    path("<int:club_id>/", ClubDetailView.as_view(), name="detail"),
    path("<int:club_id>/members/", ClubMembersView.as_view(), name="members"),
    path("<int:club_id>/nomina/", ClubRosterView.as_view(), name="roster"),
    path("<int:club_id>/roles/", ClubRolesView.as_view(), name="roles"),
    path("<int:club_id>/documents/", ClubDocumentsView.as_view(), name="documents"),
    re_path(
        r"^(?P<club_id>\d+)/leader/(?P<action>assign|revoke)/$",
        ClubLeaderView.as_view(),
        name="leader",
    ),
]

role_urlpatterns = [
    path("<int:role_id>/", RoleDetailView.as_view(), name="detail"),
]

membership_urlpatterns = [
    path("<int:membership_id>/", MembershipDetailView.as_view(), name="detail"),
    path("<int:membership_id>/revoke/", MembershipDetailView.as_view(), name="revoke"),
]

club_document_urlpatterns = [
    path("<int:document_id>/", ClubDocumentDetailView.as_view(), name="detail"),
]
