"""
Base de los procesos programados (LOGICA_NEGOCIO.md §10).

Los cuatro comparten tres exigencias:

* **Idempotencia.** Ejecutarlos dos veces produce el mismo estado y no duplica
  notificaciones. La segunda ejecución debe reportar cero.
* **``--dry-run``.** Un proceso que muta la nómina de toda la institución al
  cierre de un PAO tiene que poder inspeccionarse antes de correr. Sin esto no
  son auditables.
* **Reloj inyectado.** El "ahora" se pasa como parámetro y no se lee dentro del
  bucle, para que las pruebas sean deterministas y se pueda reprocesar una fecha
  pasada.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime


class ScheduledCommand(BaseCommand):
    """Esqueleto común de los procesos programados."""

    #: Descripción de qué cuenta el número que devuelve ``run``.
    unit = "registros"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Informa cuántos registros se tocarían, sin modificar nada.",
        )
        parser.add_argument(
            "--now",
            help="Instante de referencia ISO-8601. Por defecto, el actual. "
            "Permite reprocesar una fecha pasada.",
        )

    def resolve_now(self, options):
        if options.get("now"):
            parsed = parse_datetime(options["now"])
            if parsed is None:
                self.stderr.write("Formato de --now inválido; se usa el actual.")
                return timezone.now()
            return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
        return timezone.now()

    def handle(self, *args, **options):
        now = self.resolve_now(options)

        if options["dry_run"]:
            count = self.preview(now)
            self.stdout.write(
                self.style.WARNING(
                    f"[simulación] Se tocarían {count} {self.unit}. Sin cambios."
                )
            )
            return

        count = self.run(now)
        style = self.style.SUCCESS if count else self.style.NOTICE
        self.stdout.write(style(f"{count} {self.unit} actualizados."))

    def preview(self, now):
        raise NotImplementedError

    def run(self, now):
        raise NotImplementedError
