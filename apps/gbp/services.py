"""
Comandos de trámites ante GBP (CU-GB1..GB8).

La máquina de estados §5.5 completa: ``Submitted → Under Review → Approved |
Rejected``. El salto directo de ``Submitted`` a ``Approved`` **no existe**, y no
es un descuido: obligar a pasar por ``Under Review`` garantiza que siempre haya
un administrador identificable como responsable de la resolución (RF-52).
"""

from django.utils import timezone

from apps.academic.models import PaoPeriod
from apps.clubs.models import Club, Membership
from apps.clubs.selectors import get_roster
from apps.gbp.models import GbpDocumentProcess
from core.events import emit
from core.exceptions import BusinessRuleViolation, StateTransitionError
from core.services import CLEAN_WITHOUT_UNIQUENESS, command


def build_roster_snapshot(club_id, pao_period):
    """
    Congela la nómina del período (decisión D-09).

    Se guardan los datos ya resueltos —nombre, matrícula, rol— y no
    identificadores: dentro de dos años, una exportación de este trámite debe
    poder leerse aunque el rol se haya renombrado o el estudiante ya no exista
    como usuario activo.
    """
    snapshot = []
    for membership in get_roster(club_id, pao_period):
        snapshot.append(
            {
                "enrollment": membership.student.enrollment,
                "full_name": membership.student.get_full_name(),
                "email": membership.student.email,
                "faculty": (
                    membership.student.faculty.code
                    if membership.student.faculty_id
                    else None
                ),
                "career": membership.student.career,
                "role": membership.role.role_name,
                "is_leadership": membership.is_leadership,
                "status": membership.status,
                "valid_from": membership.valid_from.isoformat(),
                "valid_until": membership.valid_until.isoformat(),
            }
        )
    return snapshot


@command
def submit_process(*, club_id, pao_period, document_type, file, submitted_by):
    """
    CU-GB1 — el club envía un trámite (RF-40, transición G1).

    El snapshot se fija aquí, en el mismo commit: tomarlo después dejaría una
    ventana en la que la nómina podría cambiar y la evidencia ya no
    correspondería al momento del envío.
    """
    club = Club.objects.get(pk=club_id)
    if club.is_read_only:
        raise BusinessRuleViolation(
            "El club está sin líder asignado y permanece en solo lectura.",
            code="club_read_only",
        )

    period = PaoPeriod.objects.get(pk=pao_period)

    process = GbpDocumentProcess(
        club=club,
        pao_period=period,
        document_type=document_type.strip(),
        file=file,
        status=GbpDocumentProcess.Status.SUBMITTED,
        submitted_by=submitted_by,
        roster_snapshot=build_roster_snapshot(club_id, period.pk),
    )
    process.full_clean(**CLEAN_WITHOUT_UNIQUENESS)
    process.save()

    emit("process.submitted", process=process)
    return process


@command
def take_process(*, process_id, reviewer):
    """
    CU-GB3 — GBP toma el trámite para revisarlo (transición G2).

    **Resuelve PPD-05.** ``Under Review`` se marca por acción explícita y no al
    abrir el PDF, por dos motivos: deja registrado quién asumió la revisión, y
    evita que una simple descarga cambie el estado del negocio.
    """
    process = GbpDocumentProcess.objects.select_for_update().get(pk=process_id)

    if process.status != GbpDocumentProcess.Status.SUBMITTED:
        raise StateTransitionError(
            f"El trámite está en '{process.get_status_display()}' y no puede "
            "tomarse para revisión.",
            code="process_not_submitted",
        )

    process.status = GbpDocumentProcess.Status.UNDER_REVIEW
    process.reviewed_by = reviewer
    process.save(update_fields=["status", "reviewed_by", "updated_at"])

    emit("process.under_review", process=process)
    return process


@command
def resolve_process(*, process_id, reviewer, approved, feedback=""):
    """
    CU-GB4 / CU-GB5 — resolución del trámite (RF-43, transiciones G3 y G4).

    Un rechazo **reabre** el trámite para el club: puede enviar uno corregido.
    Por eso el feedback es obligatorio (RN-5): sin saber qué falló, el club
    reenviaría lo mismo.
    """
    process = GbpDocumentProcess.objects.select_for_update().select_related(
        "club"
    ).get(pk=process_id)

    if process.status != GbpDocumentProcess.Status.UNDER_REVIEW:
        raise StateTransitionError(
            "Antes de resolver, el trámite debe estar en revisión. Tómalo para "
            "revisión primero.",
            code="process_not_under_review",
        )

    feedback = (feedback or "").strip()
    if not approved and not feedback:
        raise BusinessRuleViolation(
            "Debes explicar el motivo del rechazo para que el club sepa qué "
            "corregir (RN-5).",
            code="rejection_feedback_required",
            field="review_feedback",
        )

    process.status = (
        GbpDocumentProcess.Status.APPROVED
        if approved
        else GbpDocumentProcess.Status.REJECTED
    )
    process.review_feedback = feedback
    process.reviewed_by = reviewer
    process.reviewed_at = timezone.now()
    process.save(
        update_fields=[
            "status",
            "review_feedback",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )

    emit(
        "process.approved" if approved else "process.rejected",
        process=process,
    )
    return process


def get_history_by_pao(pao_period):
    """
    CU-GB8 — histórico institucional de un período (RF-49).

    Reconstruye qué clubes existían, quién los lideraba y cuántos miembros
    tenían **en ese período**, no ahora. Es posible porque las membresías nunca
    se borran: se congelan (P-4).
    """
    clubs = []
    for club in Club.objects.select_related("faculty").order_by("name"):
        memberships = (
            Membership.objects.filter(club=club, pao_period=pao_period)
            .select_related("student", "role")
            .order_by("-is_leadership", "student__last_name")
        )
        if not memberships.exists():
            continue

        leader = next((m for m in memberships if m.is_leadership), None)
        clubs.append(
            {
                "club_id": club.pk,
                "name": club.name,
                "acronym": club.acronym,
                "faculty": club.faculty.code if club.faculty_id else None,
                "leader": (
                    {
                        "enrollment": leader.student.enrollment,
                        "full_name": leader.student.get_full_name(),
                        "role": leader.role.role_name,
                    }
                    if leader
                    else None
                ),
                "members_count": memberships.count(),
                "active_members": memberships.filter(
                    status=Membership.Status.ACTIVE
                ).count(),
            }
        )
    return clubs
