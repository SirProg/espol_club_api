from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
    verbose_name = "Cuentas"

    def ready(self):
        from core.services import register_constraint_message

        # Nombres reales de los índices en MariaDB: un campo con unique=True
        # produce un índice llamado como la columna, no como tabla_columna.
        register_constraint_message(
            "enrollment",
            "Ya existe una cuenta registrada con esa matrícula.",
            code="duplicate_enrollment",
        )
        register_constraint_message(
            "email",
            "Ya existe una cuenta registrada con ese correo.",
            code="duplicate_email",
        )
