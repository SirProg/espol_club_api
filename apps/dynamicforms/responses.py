"""
¿Este formulario ya tiene respuestas?

De esa pregunta depende toda la inmutabilidad de RF-24, y contestarla exige
saber quién guarda respuestas: las postulaciones (Etapa 6) y las inscripciones a
eventos (Etapa 7). Preguntárselo directamente obligaría a ``dynamicforms`` a
importar ambas apps, invirtiendo el grafo de dependencias del §2.3.

En su lugar, cada app que almacene respuestas **se registra** aquí desde su
``AppConfig.ready()``. ``dynamicforms`` sigue sin saber quiénes son; solo sabe
que alguien contesta.

Es el mismo patrón que el bus de eventos: la dependencia se invierte para que
apunte hacia el núcleo, no desde él.
"""

import logging

logger = logging.getLogger(__name__)

#: (nombre legible, callable(form) -> int)
_counters: list[tuple[str, callable]] = []


def register_response_counter(name, counter):
    """
    Registra un contador de respuestas.

    ``counter`` recibe un ``Form`` y devuelve cuántas respuestas hay contra esa
    versión concreta. El nombre solo sirve para diagnóstico.
    """
    _counters.append((name, counter))


def clear_response_counters():
    """
    Vacía el registro por completo.

    **Rara vez es lo que quieres en un test.** Los contadores reales los
    registran las apps en su ``ready()``, que corre una sola vez al arrancar el
    proceso: si un test los borra, no vuelven, y el resto de la suite se ejecuta
    con RF-24 desactivado sin que nada lo delate. Usa
    ``snapshot_response_counters`` / ``restore_response_counters``.
    """
    _counters.clear()


def snapshot_response_counters():
    """Copia el registro actual, para restaurarlo al terminar un test."""
    return list(_counters)


def restore_response_counters(snapshot):
    """Devuelve el registro al estado capturado por ``snapshot_response_counters``."""
    _counters[:] = list(snapshot)


def count_responses(form):
    """Total de respuestas registradas contra esta versión del formulario."""
    return sum(counter(form) for _, counter in _counters)


def response_breakdown(form):
    """Desglose por origen, para poder explicar por qué un formulario está bloqueado."""
    return {name: counter(form) for name, counter in _counters}


def form_has_responses(form):
    """
    RF-24 — un formulario con respuestas es inmutable.

    Si todavía no hay ningún contador registrado, devuelve ``False``: en las
    primeras etapas del proyecto no existe nada capaz de generar respuestas, y
    esa es la verdad, no una suposición optimista.
    """
    if not _counters:
        logger.debug(
            "No hay contadores de respuestas registrados; se asume que el "
            "formulario %s no tiene respuestas.",
            form.pk,
        )
        return False
    return count_responses(form) > 0
