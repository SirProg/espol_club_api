"""Consultas sobre trámites GBP."""

from apps.gbp.models import GbpDocumentProcess


def _base():
    return GbpDocumentProcess.objects.select_related(
        "club", "pao_period", "submitted_by", "reviewed_by"
    )


def get_inbox(*, status=None, pao_period=None, club_id=None):
    """CU-GB2 — buzón de GBP (V-23)."""
    queryset = _base()
    if status:
        queryset = queryset.filter(status=status)
    if pao_period:
        queryset = queryset.filter(pao_period_id=pao_period)
    if club_id:
        queryset = queryset.filter(club_id=club_id)
    return queryset.order_by("-created_at")


def get_club_processes(club_id):
    """Trámites de un club, para su propia pantalla de rendición (V-20)."""
    return _base().filter(club_id=club_id).order_by("-created_at")


def get_process(process_id):
    return _base().filter(pk=process_id).first()


def count_pending_review():
    """Contador del panel de GBP."""
    return GbpDocumentProcess.objects.filter(
        status=GbpDocumentProcess.Status.SUBMITTED
    ).count()
