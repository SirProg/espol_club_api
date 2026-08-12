from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
    verbose_name = "Notificaciones"

    def ready(self):
        # Importar el módulo registra las suscripciones al bus de eventos.
        # Nadie importa 'notifications': ella escucha.
        from apps.notifications import handlers  # noqa: F401
        from core.services import register_constraint_message

        register_constraint_message(
            "uniq_notification_per_target",
            "La notificación ya fue emitida.",
            code="duplicate_notification",
        )
