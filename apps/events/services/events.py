"""Comandos sobre eventos y su staff (CU-EV1..EV6)."""

from apps.clubs.models import Club, Membership
from apps.clubs.selectors import is_active_member
from apps.dynamicforms.models import Form
from apps.events.models import Event, EventStaff
from core.events import emit
from core.exceptions import BusinessRuleViolation
from core.services import CLEAN_WITHOUT_UNIQUENESS, command


@command
def create_event(
    *,
    club_id,
    event_name,
    mode,
    planned_date,
    planned_hour,
    end_datetime,
    planned_place,
    description="",
    marketing_image="",
    visibility=Event.Visibility.PUBLIC,
    registration_form_id=None,
    registration_deadline=None,
    blocked_message="",
    expected_participants=None,
):
    """CU-EV1 — alta de evento (RF-30)."""
    club = Club.objects.get(pk=club_id)
    _assert_writable(club)

    event = Event(
        club=club,
        event_name=event_name.strip(),
        mode=mode,
        planned_date=planned_date,
        planned_hour=planned_hour,
        end_datetime=end_datetime,
        planned_place=planned_place.strip(),
        description=description,
        marketing_image=marketing_image,
        visibility=visibility,
        registration_form=_resolve_form(club, registration_form_id),
        registration_deadline=registration_deadline,
        blocked_message=blocked_message,
        expected_participants=expected_participants,
    )
    event.full_clean(exclude=["start_datetime"], **CLEAN_WITHOUT_UNIQUENESS)
    event.save()

    emit("event.created", event=event)
    return event


@command
def update_event(*, event_id, registration_form_id=..., **fields):
    """CU-EV2 — edición del evento."""
    event = Event.objects.select_related("club").get(pk=event_id)
    _assert_writable(event.club)

    for name, value in fields.items():
        if value is not None:
            setattr(event, name, value)

    if registration_form_id is not ...:
        event.registration_form = _resolve_form(event.club, registration_form_id)

    event.full_clean(exclude=["start_datetime"], **CLEAN_WITHOUT_UNIQUENESS)
    event.save()
    return event


@command
def delete_event(*, event_id):
    """
    CU-EV3 — borrado, admitido solo sin inscripciones.

    Con inscripciones hay credenciales emitidas y posiblemente asistencias
    registradas: es evidencia, y P-4 la protege.
    """
    event = Event.objects.select_related("club").get(pk=event_id)
    _assert_writable(event.club)

    if event.registrations.exists():
        raise BusinessRuleViolation(
            "El evento ya tiene inscripciones y no puede eliminarse.",
            code="event_has_registrations",
        )

    event.delete()


@command
def set_event_staff(*, event_id, student_ids, assigned_by=None):
    """
    CU-EV6 — reemplaza la asignación completa de staff (RF-35).

    Reemplaza en vez de acumular porque así lo usa la pantalla 25: el líder ve
    la lista y confirma quiénes quedan. Añadir de a uno obligaría a un endpoint
    de baja aparte y a que la interfaz llevara la cuenta.
    """
    event = Event.objects.select_related("club").get(pk=event_id)
    _assert_writable(event.club)

    student_ids = list(dict.fromkeys(student_ids))  # sin duplicados, en orden

    # Invariante I-20: el staff sale de la nómina del club del evento. Alguien
    # ajeno escaneando credenciales no tendría por qué estar ahí.
    valid_ids = set(
        Membership.objects.filter(
            club=event.club,
            student_id__in=student_ids,
            status=Membership.Status.ACTIVE,
        ).values_list("student_id", flat=True)
    )
    invalid = [sid for sid in student_ids if sid not in valid_ids]
    if invalid:
        raise BusinessRuleViolation(
            "Solo los miembros activos del club pueden ser staff del evento.",
            code="staff_must_be_active_member",
            field="student_ids",
        )

    event.staff.exclude(student_id__in=student_ids).delete()
    for student_id in student_ids:
        EventStaff.objects.get_or_create(
            event=event,
            student_id=student_id,
            defaults={"assigned_by": assigned_by},
        )

    emit("event.staff_changed", event=event)
    return event.staff.select_related("student").all()


def can_register(student, event):
    """
    CU-EV5 — cadena de validación en el orden exacto de MASTER §14.

    El orden importa: si se comprobara la fecha límite antes que la inscripción
    previa, alguien ya inscrito vería "el registro está cerrado" en vez de "ya
    estás inscrito", que es la información útil.
    """
    from apps.events.models import EventRegistration

    if EventRegistration.objects.filter(event=event, student=student).exists():
        return {
            "can_register": False,
            "reason": "Ya estás inscrito en este evento.",
            "code": "already_registered",
        }

    if event.registration_form_id is None:
        return {
            "can_register": False,
            "reason": "Este evento no tiene registro abierto.",
            "code": "no_registration_form",
        }

    if event.members_only and not is_active_member(student, event.club_id):
        return {
            "can_register": False,
            "reason": event.blocked_message or "Evento exclusivo para miembros.",
            "code": "members_only",
        }

    if not event.registration_is_open:
        return {
            "can_register": False,
            "reason": event.blocked_message or "El registro está cerrado.",
            "code": "registration_closed",
        }

    return {"can_register": True, "reason": None, "code": None}


def _resolve_form(club, form_id):
    if form_id is None:
        return None
    form = Form.objects.filter(pk=form_id).first()
    if form is None:
        raise BusinessRuleViolation(
            "El formulario indicado no existe.", code="form_not_found"
        )
    if form.club_id != club.pk:
        raise BusinessRuleViolation(
            "El formulario debe pertenecer al mismo club que el evento.",
            code="form_club_mismatch",
            field="registration_form",
        )
    return form


def _assert_writable(club):
    if club.is_read_only:
        raise BusinessRuleViolation(
            "El club está sin líder asignado y permanece en solo lectura.",
            code="club_read_only",
        )
