"""
Bus de eventos de dominio (LOGICA_NEGOCIO.md §9).

Existe para una sola razón: mantener el grafo de dependencias acíclico. La
aprobación de una solicitud debe producir una notificación, pero ``applications``
no puede importar ``notifications`` sin invertir la frontera del §2.3. En vez de
eso emite ``application.approved`` y ``notifications`` se suscribe.

Dos garantías:

1. **Se despacha después del commit.** Un handler que falle no puede deshacer la
   operación de negocio que lo originó. Una notificación perdida es un incidente
   menor; una aprobación revertida a medias, no.
2. **Un handler que revienta no arrastra a los demás.** Se registra en el log y
   el despacho continúa.
"""

import logging

from django.db import transaction

logger = logging.getLogger(__name__)

#: nombre del evento -> lista de handlers
_handlers: dict[str, list] = {}


def on(event_name):
    """
    Registra un handler para un evento.

    Uso::

        @on("application.approved")
        def notify_applicant(*, application, **kwargs):
            ...

    Los handlers reciben el payload como argumentos de palabra clave y deben
    aceptar ``**kwargs``, para que agregar un dato al payload no rompa a los
    suscriptores existentes.
    """

    def decorator(func):
        _handlers.setdefault(event_name, []).append(func)
        return func

    return decorator


def emit(event_name, **payload):
    """
    Emite un evento de dominio.

    Dentro de una transacción, el despacho queda diferido hasta el commit. Fuera
    de ella se despacha de inmediato.
    """
    transaction.on_commit(lambda: _dispatch(event_name, payload))


def _dispatch(event_name, payload):
    handlers = _handlers.get(event_name, [])
    if not handlers:
        logger.debug("Evento '%s' emitido sin suscriptores.", event_name)
        return

    for handler in handlers:
        try:
            handler(**payload)
        except Exception:
            logger.exception(
                "El handler %s falló al procesar el evento '%s'.",
                getattr(handler, "__qualname__", handler),
                event_name,
            )


def clear_handlers():
    """
    Vacía el registro por completo.

    **Casi nunca es lo que quieres en un test.** Los handlers reales los
    registran las apps en su ``ready()``, que corre una sola vez al arrancar el
    proceso: si un test los borra, no vuelven, y el resto de la suite se ejecuta
    con esas reacciones desactivadas —RF-12, por ejemplo— sin que nada falle de
    forma evidente. Usa ``snapshot_handlers`` / ``restore_handlers``.
    """
    _handlers.clear()


def snapshot_handlers():
    """Copia el registro actual, para restaurarlo al terminar un test."""
    return {name: list(handlers) for name, handlers in _handlers.items()}


def restore_handlers(snapshot):
    """Devuelve el registro al estado capturado por ``snapshot_handlers``."""
    _handlers.clear()
    _handlers.update({name: list(handlers) for name, handlers in snapshot.items()})


def registered_events():
    """Eventos con al menos un suscriptor. Útil para diagnóstico."""
    return sorted(name for name, handlers in _handlers.items() if handlers)
