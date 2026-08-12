"""
Comandos del calendario académico (CU-PA1..PA4).

Actor de todos ellos: Administrador GBP (RF-45). La autorización se resuelve en
la capa de vistas; aquí solo viven las reglas.
"""

from apps.academic.models import PaoPeriod
from core.events import emit
from core.exceptions import BusinessRuleViolation
from core.services import CLEAN_WITHOUT_UNIQUENESS, command


@command
def create_pao(*, pao_period, start_date, end_date, activate=False):
    """CU-PA1. Crea el período cerrado; opcionalmente lo activa acto seguido."""
    period = PaoPeriod(
        pao_period=pao_period.strip().upper(),
        start_date=start_date,
        end_date=end_date,
        status=PaoPeriod.Status.CLOSED,
    )
    period.full_clean(**CLEAN_WITHOUT_UNIQUENESS)
    period.save()

    if activate:
        return activate_pao(period.pk)
    return period


@command
def update_pao(*, pao_period, start_date=None, end_date=None):
    """
    CU-PA2. Ajusta las fechas del período.

    El identificador no se edita: es la llave primaria y está referenciado por
    membresías y trámites. Cambiarlo sería reescribir historia.
    """
    period = PaoPeriod.objects.get(pk=pao_period)
    if start_date is not None:
        period.start_date = start_date
    if end_date is not None:
        period.end_date = end_date
    period.full_clean(**CLEAN_WITHOUT_UNIQUENESS)
    period.save(update_fields=["start_date", "end_date", "updated_at"])
    return period


@command
def activate_pao(pao_period):
    """
    CU-PA3 / transición P2. Activa un período y cierra todos los demás.

    El orden de las dos escrituras no es negociable: primero se cierran los
    otros, después se activa este. Al revés, el índice único de I-08 dispararía
    contra el período que está a punto de cerrarse.
    """
    period = PaoPeriod.objects.select_for_update().get(pk=pao_period)

    PaoPeriod.objects.filter(status=PaoPeriod.Status.ACTIVE).exclude(
        pk=period.pk
    ).update(status=PaoPeriod.Status.CLOSED)

    if not period.is_active:
        period.status = PaoPeriod.Status.ACTIVE
        period.save(update_fields=["status", "updated_at"])

    emit("pao.activated", pao_period=period)
    return period


@command
def close_pao(pao_period):
    """
    Cierra un período sin activar otro.

    Deja al sistema sin PAO activo: las operaciones que dependen de uno fallarán
    con ConfigurationError hasta que GBP active el siguiente. Es una situación
    legítima entre semestres, no un error.
    """
    period = PaoPeriod.objects.select_for_update().get(pk=pao_period)
    if not period.is_active:
        raise BusinessRuleViolation(
            "El período ya está cerrado.", code="pao_already_closed"
        )
    period.status = PaoPeriod.Status.CLOSED
    period.save(update_fields=["status", "updated_at"])
    emit("pao.closed", pao_period=period)
    return period
