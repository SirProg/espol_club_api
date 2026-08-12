"""
Registro de asistencia por escaneo de QR (CU-EV9).

La operación más sensible del sistema. Ocurre en una sala llena, con varias
personas del staff escaneando a la vez, y tiene que sostener RN-6: **una
asistencia por persona y evento, nunca dos**.

La defensa se construye en tres capas, de fuera hacia dentro:

1. La cadena de guardas, que produce los mensajes que el staff lee en pantalla.
2. ``SELECT ... FOR UPDATE`` sobre la inscripción, que serializa dos escaneos
   simultáneos del mismo código. Funciona porque el proyecto corre en
   ``READ COMMITTED`` (ver ``config/settings/base.py``): con el
   ``REPEATABLE READ`` por defecto de InnoDB, la segunda transacción leería su
   propia instantánea y no vería que la primera ya marcó la credencial.
3. ``UNIQUE(event_id, student_id)`` sobre ``EventAttendance``, que es lo único
   que no se puede eludir.
"""

from django.utils import timezone

from apps.events.models import EventAttendance, EventRegistration, EventStaff
from apps.events.qr import read_qr_token
from core.events import emit
from core.exceptions import BusinessRuleViolation, PermissionDeniedError
from core.services import command

# Mensajes canónicos de MASTER §12. El staff los lee en el móvil, a veces con
# una cola esperando: tienen que decir qué pasa y qué hacer.
EMPTY_TOKEN = "Ingresa o escanea un código."
UNKNOWN_TOKEN = "Credencial no reconocida."
ALREADY_USED = "Esta credencial ya registró asistencia."
EXPIRED_TOKEN = "Esta credencial ya venció."
NOT_STAFF = "No estás asignado como staff de este evento."
OUTSIDE_WINDOW = "El escaneo solo está habilitado durante el evento."
SUCCESS = "Asistencia registrada correctamente."


@command
def register_scan(*, qr_token, staff_student, now=None):
    """
    Valida un token y registra la asistencia.

    Las guardas van en este orden exacto y no en otro: se responde primero lo
    que le sirve a quien escanea. Comprobar la ventana horaria antes que el
    duplicado, por ejemplo, haría que una credencial ya usada fuera del horario
    reportara el problema equivocado.
    """
    now = now or timezone.now()
    token = (qr_token or "").strip()

    if not token:
        raise BusinessRuleViolation(EMPTY_TOKEN, code="empty_qr_token")

    # La firma se comprueba antes de consultar: descarta basura sin gastar una
    # consulta. Pero **no** es la autorización: un token con firma perfecta y
    # sin fila en la base no vale nada.
    if read_qr_token(token) is None:
        raise BusinessRuleViolation(UNKNOWN_TOKEN, code="unknown_qr_token")

    registration = (
        EventRegistration.objects.select_for_update()
        .select_related("event", "event__club", "student")
        .filter(qr_token=token)
        .first()
    )
    if registration is None:
        raise BusinessRuleViolation(UNKNOWN_TOKEN, code="unknown_qr_token")

    if (
        registration.qr_status == EventRegistration.QrStatus.USED
        or registration.attendance_status
        == EventRegistration.AttendanceStatus.ATTENDED
    ):
        raise BusinessRuleViolation(ALREADY_USED, code="qr_already_used")

    if registration.qr_status == EventRegistration.QrStatus.EXPIRED:
        raise BusinessRuleViolation(EXPIRED_TOKEN, code="qr_expired")

    event = registration.event

    # RF-35 / divergencia §20.6 de MASTER: en la Fase 1 el escaneo aceptaba
    # cualquier identificador de staff sin comprobarlo. Aquí es obligatorio.
    if not EventStaff.objects.filter(event=event, student=staff_student).exists():
        raise PermissionDeniedError(NOT_STAFF, code="not_event_staff")

    # Decisión D-08: el permiso del staff nace y muere con el evento.
    if not event.is_within_scan_window(now):
        raise PermissionDeniedError(OUTSIDE_WINDOW, code="outside_scan_window")

    attendance = EventAttendance.objects.create(
        registration=registration,
        event=event,
        student=registration.student,
        # RNF-12: la hora la pone el servidor. Si la pusiera el cliente, la
        # evidencia de asistencia sería lo que el escáner quisiera afirmar.
        scanned_at=now,
        scanned_by_staff=staff_student,
        qr_token_validated=token,
        status=EventAttendance.Status.ATTENDED,
    )

    registration.qr_status = EventRegistration.QrStatus.USED
    registration.attendance_status = EventRegistration.AttendanceStatus.ATTENDED
    registration.save(update_fields=["qr_status", "attendance_status", "updated_at"])

    emit("attendance.registered", attendance=attendance)
    return attendance


def describe_scan_result(attendance):
    """Respuesta que ve el staff tras un escaneo válido (pantalla 13)."""
    return {
        "message": SUCCESS,
        "student_name": attendance.student.get_full_name(),
        "enrollment": attendance.student.enrollment,
        "event_name": attendance.event.event_name,
        "scanned_at": attendance.scanned_at,
    }
