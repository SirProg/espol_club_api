"""
Suscripciones de ``clubs`` a los eventos del dominio.

Es ``clubs`` quien escucha a ``accounts``, y no al revés. Esa dirección importa:
``accounts`` no debe saber que existen los clubes, o el grafo de dependencias
del §2.3 dejaría de ser acíclico y el registro de una cuenta arrastraría medio
sistema.
"""

import logging

from core.events import on

logger = logging.getLogger(__name__)


@on("student.verified")
def activate_leadership_on_verification(*, student, **kwargs):
    """
    RF-12 / transición C3 — el club sin líder despierta.

    Cuando GBP da de alta un club vinculando una matrícula que todavía no tiene
    cuenta, el club queda en ``Pending Leader`` con esa matrícula guardada
    (decisión D-01). Al verificarse esa cuenta, el liderazgo se materializa
    aquí.

    Que sea un handler y no una llamada dentro de ``verify_email`` tiene una
    consecuencia deliberada: se ejecuta **después del commit**, así que un fallo
    activando el club no deshace la verificación de la cuenta. Verificarse es un
    derecho del estudiante; el club puede resolverse después.
    """
    from apps.clubs.services.leadership import activate_pending_leadership

    activated = activate_pending_leadership(student)
    if activated:
        logger.info(
            "Liderazgo activado para %s en: %s",
            student.enrollment,
            ", ".join(club.acronym for club in activated),
        )
