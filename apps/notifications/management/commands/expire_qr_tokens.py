"""
Expiración de credenciales QR (RF-37, transición Q2).

Frecuencia recomendada: horaria.

Al alcanzar el ``end_datetime`` del evento, las credenciales sin usar dejan de
servir. Es lo que impide que un QR emitido para el taller de marzo siga siendo
válido en abril.
"""

from apps.events.models import EventRegistration
from apps.events.services.registration import expire_qr_tokens
from apps.notifications.management.commands._base import ScheduledCommand


class Command(ScheduledCommand):
    help = "Caduca las credenciales QR de eventos ya finalizados (RF-37)."
    unit = "credenciales expiradas"

    def preview(self, now):
        return EventRegistration.objects.filter(
            qr_status=EventRegistration.QrStatus.ACTIVE,
            event__end_datetime__lt=now,
        ).count()

    def run(self, now):
        return expire_qr_tokens(now=now)
