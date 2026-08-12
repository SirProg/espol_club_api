"""
Marcado de inasistencias (§5.4, transición Q3).

Frecuencia recomendada: horaria.

Recorre el mismo conjunto de eventos finalizados que ``expire_qr_tokens``, pero
se mantiene como comando aparte porque los dos ejes de estado son independientes:
uno describe la credencial y el otro la participación. Fusionarlos obligaría a
reprocesar ambos cuando solo hiciera falta uno.
"""

from apps.events.models import EventRegistration
from apps.events.services.registration import mark_no_shows
from apps.notifications.management.commands._base import ScheduledCommand


class Command(ScheduledCommand):
    help = "Marca como ausentes a los inscritos sin asistencia registrada."
    unit = "inscripciones marcadas como ausencia"

    def preview(self, now):
        return EventRegistration.objects.filter(
            attendance_status=EventRegistration.AttendanceStatus.REGISTERED,
            event__end_datetime__lt=now,
        ).count()

    def run(self, now):
        return mark_no_shows(now=now)
