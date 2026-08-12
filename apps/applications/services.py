"""
Comandos de postulación (CU-AP1..AP5).

Dos reglas gobiernan esta app:

* **RN-2** — ni dos solicitudes pendientes al mismo club, ni postular donde ya
  se es miembro. Pero una solicitud rechazada puede reenviarse **de inmediato**,
  sin tiempo de espera (RF-29).
* **RN-5** — rechazar exige justificación no vacía.
"""

from django.utils import timezone

from apps.academic.selectors import get_active_pao
from apps.applications.models import MembershipApplication
from apps.clubs.models import Club, Membership
from apps.clubs.selectors import is_active_member
from apps.clubs.services.memberships import create_membership
from apps.dynamicforms.selectors import get_active_membership_form
from apps.dynamicforms.services import validate_submission
from core.events import emit
from core.exceptions import BusinessRuleViolation, StateTransitionError
from core.services import CLEAN_WITHOUT_UNIQUENESS, command

# Mensajes de bloqueo canónicos de MASTER §12. Se reproducen literalmente para
# que la Fase 1 y la app móvil sigan mostrando exactamente el mismo texto.
ALREADY_MEMBER = "Ya eres miembro activo de este club."
ALREADY_PENDING = "Ya tienes una solicitud pendiente en este club."
CLUB_NOT_ACTIVE = "Este club no está recibiendo postulaciones en este momento."
NO_FORM = "Este club todavía no ha publicado un formulario de postulación."


def can_apply(student, club_id):
    """
    CU-AP2 — ``{allowed, reason}`` para que la app decida si habilita el botón.

    La comprobación se repite dentro de ``submit_application``: esto es una
    conveniencia de interfaz, no la autorización. Entre consultar y enviar puede
    pasar cualquier cosa.
    """
    club = Club.objects.filter(pk=club_id).first()
    if club is None:
        return {"allowed": False, "reason": "El club no existe.", "code": "not_found"}

    if not club.is_active:
        return {"allowed": False, "reason": CLUB_NOT_ACTIVE, "code": "club_not_active"}

    if is_active_member(student, club_id):
        return {"allowed": False, "reason": ALREADY_MEMBER, "code": "already_member"}

    if _has_pending(student, club_id):
        return {"allowed": False, "reason": ALREADY_PENDING, "code": "already_pending"}

    if get_active_membership_form(club_id) is None:
        return {"allowed": False, "reason": NO_FORM, "code": "no_membership_form"}

    return {"allowed": True, "reason": None, "code": None}


@command
def submit_application(*, student, club_id, responses):
    """
    CU-AP1 — el estudiante postula (RF-25, transición A1).

    Las respuestas pasan por CU-FO6 antes de tocar la base: el formulario lo
    diseñó el líder, pero quien envía las respuestas es un cliente no confiable.
    """
    verdict = can_apply(student, club_id)
    if not verdict["allowed"]:
        raise BusinessRuleViolation(verdict["reason"], code=verdict["code"])

    club = Club.objects.get(pk=club_id)
    form = get_active_membership_form(club_id)

    application = MembershipApplication(
        student=student,
        club=club,
        form=form,
        responses=validate_submission(form, responses),
        status=MembershipApplication.Status.PENDING,
    )
    application.full_clean(
        exclude=["pending_student", "pending_club"], **CLEAN_WITHOUT_UNIQUENESS
    )
    application.save()

    emit("application.submitted", application=application)
    return application


@command
def approve_application(*, application_id, resolved_by):
    """
    CU-AP4 — el líder acepta (RF-08, RF-27, transición A2).

    **Transaccionalmente crítico:** resolver la solicitud y crear la membresía
    ocurren en el mismo commit. Una solicitud aprobada sin membresía es un
    estado corrupto que ningún proceso podría reparar solo, porque no habría
    forma de distinguirlo de una aprobación legítima ya revocada.
    """
    application = (
        MembershipApplication.objects.select_for_update()
        .select_related("club", "student")
        .get(pk=application_id)
    )
    _assert_pending(application)
    _assert_club_writable(application.club)

    # Se comprueba de nuevo aquí: entre postular y aprobar, el estudiante pudo
    # haber entrado al club por otra vía (renovación, asignación de GBP).
    if is_active_member(application.student, application.club_id):
        raise BusinessRuleViolation(
            f"{application.student.get_full_name()} ya es miembro activo del club.",
            code="already_member",
        )

    get_active_pao()  # falla con ConfigurationError si GBP no activó ninguno

    membership = create_membership(
        student=application.student,
        club=application.club,
        origin=Membership.Origin.APPLICATION,
    )

    application.status = MembershipApplication.Status.APPROVED
    application.resolved_by = resolved_by
    application.resolved_at = timezone.now()
    application.resulting_membership = membership
    application.save(
        update_fields=[
            "status",
            "resolved_by",
            "resolved_at",
            "resulting_membership",
            "updated_at",
        ]
    )

    emit("application.approved", application=application, membership=membership)
    return application


@command
def reject_application(*, application_id, resolved_by, feedback):
    """
    CU-AP5 — el líder niega (transición A3, **RN-5**).

    El feedback es obligatorio porque RF-29 permite reenviar de inmediato: sin
    saber qué falló, el estudiante reenviaría lo mismo.
    """
    application = (
        MembershipApplication.objects.select_for_update()
        .select_related("club", "student")
        .get(pk=application_id)
    )
    _assert_pending(application)
    _assert_club_writable(application.club)

    feedback = (feedback or "").strip()
    if not feedback:
        raise BusinessRuleViolation(
            "Debes explicar el motivo del rechazo para que el estudiante sepa "
            "qué corregir (RN-5).",
            code="rejection_feedback_required",
            field="leader_feedback",
        )

    application.status = MembershipApplication.Status.REJECTED
    application.leader_feedback = feedback
    application.resolved_by = resolved_by
    application.resolved_at = timezone.now()
    application.save(
        update_fields=[
            "status",
            "leader_feedback",
            "resolved_by",
            "resolved_at",
            "updated_at",
        ]
    )

    emit("application.rejected", application=application)
    return application


def count_form_responses(form):
    """
    Contador que ``applications`` aporta a ``dynamicforms`` (RF-24).

    Cuenta **todas** las solicitudes de esa versión, no solo las pendientes: una
    solicitud resuelta sigue siendo una respuesta que quedó ligada a ese
    esquema, y editarlo la volvería ilegible.
    """
    return MembershipApplication.objects.filter(form=form).count()


def _has_pending(student, club_id):
    if not student or not student.is_authenticated:
        return False
    return MembershipApplication.objects.filter(
        student=student,
        club_id=club_id,
        status=MembershipApplication.Status.PENDING,
    ).exists()


def _assert_pending(application):
    if not application.is_pending:
        raise StateTransitionError(
            f"La solicitud ya fue resuelta ({application.get_status_display()}) y "
            "no admite cambios.",
            code="application_already_resolved",
        )


def _assert_club_writable(club):
    if club.is_read_only:
        raise BusinessRuleViolation(
            "El club está sin líder asignado y permanece en solo lectura.",
            code="club_read_only",
        )
