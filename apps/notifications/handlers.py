"""
Suscripciones al bus de eventos de dominio (LOGICA_NEGOCIO.md §9).

Este módulo es el único consumidor transversal del sistema, y por diseño
**nadie lo importa**: se suscribe. Esa dirección es lo que permite que
``applications``, ``events`` y ``gbp`` emitan avisos sin conocer siquiera la
existencia de las notificaciones.

Todos los handlers corren después del commit (lo garantiza ``core.events``), así
que un fallo aquí nunca revierte la aprobación, la inscripción o la resolución
que lo originó. Una notificación perdida es un incidente menor; una aprobación
deshecha a medias, no.
"""

from apps.clubs.permissions import ClubPermission
from apps.notifications.models import Notification
from apps.notifications.services import notify, notify_many
from core.events import on


def _club_managers(club, permission):
    """
    Quiénes deben enterarse de algo que le pasa al club.

    No es "el líder": es quien tenga el permiso correspondiente. Si la
    presidencia delegó ``manage_members`` en la secretaría, la bandeja de
    solicitudes le llega a la secretaría.
    """
    from apps.clubs.models import Membership

    memberships = Membership.objects.filter(
        club=club, status=Membership.Status.ACTIVE
    ).select_related("student", "role")
    return [m.student for m in memberships if m.role.has(permission)]


# --- Solicitudes de membresía ------------------------------------------------


@on("application.submitted")
def on_application_submitted(*, application, **kwargs):
    notify_many(
        users=_club_managers(application.club, ClubPermission.MANAGE_MEMBERS),
        type=Notification.Type.APPLICATION_PENDING,
        message=(
            f"{application.student.get_full_name()} postuló a "
            f"{application.club.acronym}."
        ),
        target=application,
        club=application.club,
    )


@on("application.approved")
def on_application_approved(*, application, **kwargs):
    notify(
        user=application.student,
        type=Notification.Type.APPLICATION_APPROVED,
        message=(
            f"Tu solicitud a {application.club.acronym} fue aprobada. "
            "Ya eres miembro del club."
        ),
        target=application,
        club=application.club,
    )


@on("application.rejected")
def on_application_rejected(*, application, **kwargs):
    # El feedback viaja en el mensaje: RF-29 permite reenviar de inmediato, y
    # sin saber qué falló el estudiante reenviaría lo mismo.
    notify(
        user=application.student,
        type=Notification.Type.APPLICATION_REJECTED,
        message=(
            f"Tu solicitud a {application.club.acronym} fue rechazada: "
            f"{application.leader_feedback}"
        ),
        target=application,
        club=application.club,
    )


# --- Membresías --------------------------------------------------------------


@on("membership.revoked")
def on_membership_revoked(*, membership, **kwargs):
    notify(
        user=membership.student,
        type=Notification.Type.MEMBERSHIP_REVOKED,
        message=f"Tu membresía en {membership.club.acronym} fue dada de baja.",
        target=membership,
        club=membership.club,
    )


@on("membership.renewed")
def on_membership_renewed(*, club, pao_period, memberships, **kwargs):
    for membership in memberships:
        notify(
            user=membership.student,
            type=Notification.Type.MEMBERSHIP_RENEWED,
            message=(
                f"Tu membresía en {club.acronym} fue renovada para el período "
                f"{pao_period.pao_period}."
            ),
            target=membership,
            club=club,
        )


@on("membership.frozen")
def on_membership_frozen(*, membership, **kwargs):
    notify(
        user=membership.student,
        type=Notification.Type.MEMBERSHIP_FROZEN,
        message=(
            f"Tu membresía en {membership.club.acronym} se congeló al cerrar el "
            f"período {membership.pao_period_id}."
        ),
        target=membership,
        club=membership.club,
    )


# --- Liderazgo ---------------------------------------------------------------


@on("club.leader_assigned")
def on_leader_assigned(*, club, student, **kwargs):
    notify(
        user=student,
        type=Notification.Type.LEADER_ASSIGNED,
        message=f"Fuiste designado líder de {club.acronym}.",
        target=club,
        club=club,
    )


@on("club.leader_revoked")
def on_leader_revoked(*, club, student, **kwargs):
    notify(
        user=student,
        type=Notification.Type.LEADER_REVOKED,
        message=f"Tu liderazgo en {club.acronym} fue revocado por GBP.",
        target=club,
        club=club,
    )


# --- Eventos -----------------------------------------------------------------


@on("event.registered")
def on_event_registered(*, registration, **kwargs):
    notify(
        user=registration.student,
        type=Notification.Type.EVENT_REGISTERED,
        message=(
            f"Te inscribiste en {registration.event.event_name}. "
            "Tu credencial QR ya está disponible."
        ),
        target=registration,
        club=registration.event.club,
    )


@on("attendance.registered")
def on_attendance_registered(*, attendance, **kwargs):
    notify(
        user=attendance.student,
        type=Notification.Type.ATTENDANCE_REGISTERED,
        message=f"Se registró tu asistencia a {attendance.event.event_name}.",
        target=attendance,
        club=attendance.event.club,
    )


# --- Trámites GBP ------------------------------------------------------------


@on("process.submitted")
def on_process_submitted(*, process, **kwargs):
    from django.contrib.auth import get_user_model

    Student = get_user_model()
    notify_many(
        users=Student.objects.filter(is_gbp_admin=True, is_active=True),
        type=Notification.Type.GBP_REVIEW,
        message=(
            f"{process.club.acronym} envió '{process.document_type}' "
            f"del período {process.pao_period_id}."
        ),
        target=process,
        club=process.club,
    )


@on("process.approved")
def on_process_approved(*, process, **kwargs):
    _notify_club_reporters(
        process,
        f"GBP aprobó '{process.document_type}' de {process.pao_period_id}.",
    )


@on("process.rejected")
def on_process_rejected(*, process, **kwargs):
    _notify_club_reporters(
        process,
        (
            f"GBP rechazó '{process.document_type}' de {process.pao_period_id}: "
            f"{process.review_feedback}"
        ),
    )


def _notify_club_reporters(process, message):
    notify_many(
        users=_club_managers(process.club, ClubPermission.SUBMIT_GBP_REPORTS),
        type=Notification.Type.GBP_RESOLUTION,
        message=message,
        target=process,
        club=process.club,
    )
