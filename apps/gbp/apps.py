from django.apps import AppConfig


class GbpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gbp"
    label = "gbp"
    verbose_name = "Gerencia de Bienestar Politécnico"

    def ready(self):
        from core.services import register_constraint_message

        register_constraint_message(
            "chk_process_rejection_requires_feedback",
            "Debes explicar el motivo del rechazo (RN-5).",
            code="rejection_feedback_required",
        )
