"""
Emisión y verificación del token QR (RNF-05, MASTER §16.9).

**Puntos no negociables:**

* El token no contiene ``student_id`` ni ``event_id`` legibles. Solo referencia
  la inscripción, y va firmado.
* La validación se hace **contra la base de datos**, no descifrando el token.
  La firma sirve para descartar basura antes de consultar; la autoridad es la
  fila. Un token con firma perfecta pero sin fila en la base no vale nada.
* ``scanned_at`` lo pone el servidor. Si lo pusiera el cliente, la evidencia de
  asistencia sería lo que el escáner quisiera afirmar.
"""

from django.conf import settings
from django.core import signing

QR_SALT = "espolclub.qr"


def issue_qr_token(registration_id):
    """
    Emite el token de una inscripción.

    ``signing.dumps`` firma pero **no cifra**: el contenido es legible. Por eso
    el payload lleva únicamente el identificador de la inscripción, que por sí
    solo no revela ni quién es la persona ni a qué evento va.
    """
    return signing.dumps({"r": registration_id}, salt=QR_SALT)


def read_qr_token(token):
    """
    Devuelve el id de inscripción si la firma es válida, o ``None``.

    No comprueba caducidad por tiempo: la vigencia de una credencial la marca
    ``qr_status`` en la base, que es lo que el proceso horario actualiza cuando
    el evento termina. Poner aquí un ``max_age`` duplicaría esa regla en dos
    sitios que podrían discrepar.
    """
    if not token:
        return None
    try:
        payload = signing.loads(token, salt=QR_SALT)
    except signing.BadSignature:
        return None
    return payload.get("r")


def qr_payload(registration):
    """
    Lo que se pinta en el código QR de la app (pantalla 12).

    Solo el token. Los datos del evento se muestran alrededor, en la tarjeta,
    pero no viajan dentro del código: cuanto menos lleve, menos revela una foto
    del QR compartida por descuido.
    """
    return {
        "token": registration.qr_token,
        "event_name": registration.event.event_name,
        "starts_at": registration.event.start_datetime,
        "place": registration.event.planned_place,
        "status": registration.qr_status,
        "status_label": registration.get_qr_status_display(),
    }


def scan_window_settings():
    """Ventana de escaneo configurada (decisión D-08)."""
    return {
        "lead_minutes": settings.SCAN_LEAD_MINUTES,
        "grace_minutes": settings.SCAN_GRACE_MINUTES,
    }
