"""
Congelamiento de membresías al cerrar el PAO (RF-20, RN-4, transición M2).

Frecuencia recomendada: diaria.

Es el proceso de mayor volumen del sistema —al cerrar un período toca la nómina
de toda la institución a la vez—, y por eso es el que más necesita ``--dry-run``.
"""

from apps.clubs.models import Membership
from apps.clubs.services.memberships import freeze_expired_memberships
from apps.notifications.management.commands._base import ScheduledCommand


class Command(ScheduledCommand):
    help = "Congela las membresías vigentes cuyo período ya venció (RF-20)."
    unit = "membresías congeladas"

    def preview(self, now):
        return Membership.objects.filter(
            status=Membership.Status.ACTIVE, valid_until__lt=now.date()
        ).count()

    def run(self, now):
        return freeze_expired_memberships(today=now.date())
