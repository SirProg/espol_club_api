"""
Expiración de membresías no renovadas (RF-19, transición M3).

Frecuencia recomendada: diaria.

Una membresía congelada expira cuando su período está cerrado y el estudiante no
aparece en ninguno posterior de ese club. Es lo que distingue "no renovado
todavía" de "ya no pertenece".
"""

from apps.clubs.services.memberships import expire_stale_memberships
from apps.notifications.management.commands._base import ScheduledCommand


class Command(ScheduledCommand):
    help = "Expira las membresías congeladas que nadie renovó (RF-19)."
    unit = "membresías expiradas"

    def preview(self, now):
        from apps.academic.models import PaoPeriod
        from apps.clubs.models import Membership

        # Misma consulta que el servicio, sin escribir. Se replica en vez de
        # extraerse porque el servicio decide fila por fila y aquí solo hace
        # falta el orden de magnitud.
        frozen = Membership.objects.filter(
            status=Membership.Status.FROZEN,
            pao_period__status=PaoPeriod.Status.CLOSED,
        ).select_related("pao_period")

        return sum(
            1
            for membership in frozen
            if not Membership.objects.filter(
                student_id=membership.student_id,
                club_id=membership.club_id,
                pao_period__sequence__gt=membership.pao_period.sequence,
            ).exists()
        )

    def run(self, now):
        return expire_stale_memberships()
