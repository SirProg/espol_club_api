"""
Provisión de cuentas de Administrador GBP (CU-AC7, resuelve PPD-02).

No hay auto-registro para GBP: es un perfil institucional, no comunitario. La
bandera ``is_gbp_admin`` nunca se expondrá en el serializer de registro, así que
esta es la única vía de alta junto con el admin de Django.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

Student = get_user_model()


class Command(BaseCommand):
    help = "Crea o promueve una cuenta de Administrador GBP."

    def add_arguments(self, parser):
        parser.add_argument("enrollment", help="Código institucional, p. ej. GBP-001")
        parser.add_argument("--email", required=True, help="Correo @espol.edu.ec")
        parser.add_argument("--first-name", required=True)
        parser.add_argument("--last-name", required=True)
        parser.add_argument(
            "--password",
            help="Si se omite, la cuenta queda sin contraseña utilizable y "
            "deberá usar el flujo de recuperación.",
        )
        parser.add_argument(
            "--staff",
            action="store_true",
            help="Además, habilita el acceso al admin de Django.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        enrollment = options["enrollment"].strip().upper()
        email = options["email"].strip().lower()

        existing = Student.objects.filter(enrollment=enrollment).first()
        if existing:
            if existing.is_gbp_admin:
                raise CommandError(
                    f"La cuenta {enrollment} ya es Administrador GBP."
                )
            existing.is_gbp_admin = True
            existing.is_verified = True
            if options["staff"]:
                existing.is_staff = True
            existing.save(
                update_fields=["is_gbp_admin", "is_verified", "is_staff", "updated_at"]
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cuenta {enrollment} promovida a Administrador GBP."
                )
            )
            return

        user = Student(
            enrollment=enrollment,
            email=email,
            first_name=options["first_name"].strip(),
            last_name=options["last_name"].strip(),
            is_gbp_admin=True,
            is_verified=True,
            is_staff=options["staff"],
        )

        try:
            # El personal GBP no tiene facultad, carrera ni semestre: se excluyen
            # de la validación en vez de exigirlos.
            user.full_clean(exclude=["password", "faculty", "career", "semester"])
        except ValidationError as exc:
            raise CommandError("; ".join(f"{k}: {v[0]}" for k, v in exc.message_dict.items()))

        if options["password"]:
            user.set_password(options["password"])
        else:
            user.set_unusable_password()

        user.save()

        self.stdout.write(
            self.style.SUCCESS(f"Administrador GBP creado: {enrollment} ({email}).")
        )
        if not options["password"]:
            self.stdout.write(
                self.style.WARNING(
                    "Sin contraseña asignada: usa el flujo de recuperación para "
                    "establecerla."
                )
            )
