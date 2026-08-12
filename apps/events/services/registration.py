"""Inscripción a eventos y emisión de credenciales (CU-EV7, CU-EV8)."""

from django.utils import timezone

from apps.dynamicforms.services import validate_submission
from apps.events.models import Event, EventRegistration
from apps.events.qr import issue_qr_token
from apps.events.services.events import can_register
from core.events import emit
from core.exceptions import BusinessRuleViolation
from core.services import CLEAN_WITHOUT_UNIQUENESS, command


@command
def register_for_event(*, student, event_id, responses):
    """
    CU-EV7 — el estudiante se inscribe y recibe su credencial (RF-32).

    Sin tope de participantes: ``expected_participants`` es solo planificación
    (RF-33). Un evento con más gente de la prevista es un problema del líder,
    no del sistema.
    """
    event = Event.objects.select_related("club", "registration_form").get(pk=event_id)

    verdict = can_register(student, event)
    if not verdict["can_register"]:
        raise BusinessRuleViolation(verdict["reason"], code=verdict["code"])

    registration = EventRegistration(
        event=event,
        student=student,
        form=event.registration_form,
        responses=validate_submission(event.registration_form, responses),
        # Provisional: el token definitivo referencia la pk, que aún no existe.
        qr_token=f"pending-{timezone.now().timestamp()}-{student.pk}",
        qr_status=EventRegistration.QrStatus.ACTIVE,
        attendance_status=EventRegistration.AttendanceStatus.REGISTERED,
    )
    registration.full_clean(exclude=["qr_token"], **CLEAN_WITHOUT_UNIQUENESS)
    registration.save()

    # El token se emite después de tener la pk y se escribe en la misma
    # transacción: si algo fallara aquí, no queda una inscripción con token
    # provisional en la base.
    registration.qr_token = issue_qr_token(registration.pk)
    registration.save(update_fields=["qr_token", "updated_at"])

    emit("event.registered", registration=registration)
    return registration


@command
def expire_qr_tokens(*, now=None):
    """
    RF-37 — caduca las credenciales de eventos ya terminados.

    Idempotente: solo toca las que siguen ``Active``. Recibe ``now`` como
    parámetro en vez de leer el reloj, para que las pruebas sean deterministas.
    """
    now = now or timezone.now()
    return EventRegistration.objects.filter(
        qr_status=EventRegistration.QrStatus.ACTIVE,
        event__end_datetime__lt=now,
    ).update(qr_status=EventRegistration.QrStatus.EXPIRED)


@command
def mark_no_shows(*, now=None):
    """
    §5.4 — marca como ausentes a quienes no fueron escaneados.

    Alimenta la métrica de inscritos vs. asistentes (RF-38). Solo toca
    inscripciones que siguen en ``Registered``: las que ya tienen asistencia
    quedaron en ``Attended`` y no se tocan.
    """
    now = now or timezone.now()
    return EventRegistration.objects.filter(
        attendance_status=EventRegistration.AttendanceStatus.REGISTERED,
        event__end_datetime__lt=now,
    ).update(attendance_status=EventRegistration.AttendanceStatus.NO_SHOW)


def count_form_responses(form):
    """Contador que ``events`` aporta a ``dynamicforms`` para RF-24."""
    return EventRegistration.objects.filter(form=form).count()
