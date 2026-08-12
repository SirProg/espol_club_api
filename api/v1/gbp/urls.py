"""Rutas del panel de GBP."""

from django.urls import path, re_path

from api.v1.gbp.pao_views import PaoDetailView, PaoListCreateView
from api.v1.gbp.views import (
    ClubProcessesView,
    GbpConsolidatedExportView,
    GbpHistoryView,
    GbpInboxView,
    ProcessDetailView,
    ProcessExportView,
    ProcessReviewView,
)

gbp_urlpatterns = [
    path("processes/", GbpInboxView.as_view(), name="inbox"),
    # Antes de la ruta con <int:process_id> para que 'export' no se interprete
    # como identificador.
    path(
        "processes/export/",
        GbpConsolidatedExportView.as_view(),
        name="consolidated-export",
    ),
    path("processes/<int:process_id>/", ProcessDetailView.as_view(), name="process"),
    path(
        "processes/<int:process_id>/export/",
        ProcessExportView.as_view(),
        name="process-export",
    ),
    re_path(
        r"^processes/(?P<process_id>\d+)/(?P<action>take|review)/$",
        ProcessReviewView.as_view(),
        name="review",
    ),
    path("pao/", PaoListCreateView.as_view(), name="pao-list"),
    path("pao/<str:pao_period>/", PaoDetailView.as_view(), name="pao-detail"),
    path("history/", GbpHistoryView.as_view(), name="history"),
]

club_process_urlpatterns = [
    path("<int:club_id>/processes/", ClubProcessesView.as_view(), name="processes"),
]
