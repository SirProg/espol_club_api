"""Consultas del calendario académico. No mutan estado."""

from apps.academic.models import PaoPeriod
from core.exceptions import ConfigurationError


def get_active_pao():
    """
    Período vigente.

    Lanza ``ConfigurationError`` en vez de devolver ``None``: aprobar una
    solicitud o renovar una nómina sin PAO activo es un error de configuración
    del administrador, y devolver None lo convertiría en un AttributeError
    varias capas más abajo, lejos de la causa.
    """
    period = PaoPeriod.objects.filter(status=PaoPeriod.Status.ACTIVE).first()
    if period is None:
        raise ConfigurationError(
            "No hay un período académico activo. GBP debe activar uno antes de "
            "continuar."
        )
    return period


def get_active_pao_or_none():
    """Variante tolerante, para pantallas de solo lectura que muestran un aviso."""
    return PaoPeriod.objects.filter(status=PaoPeriod.Status.ACTIVE).first()


def list_paos():
    """Todos los períodos, del más reciente al más antiguo."""
    return PaoPeriod.objects.all()


def get_pao(pao_period):
    return PaoPeriod.objects.filter(pk=pao_period).first()


def get_periods_after(period):
    """Períodos cronológicamente posteriores a ``period`` (soporte de M3)."""
    return PaoPeriod.objects.filter(sequence__gt=period.sequence)
