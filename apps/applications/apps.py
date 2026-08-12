from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.applications"
    label = "applications"
    verbose_name = "Solicitudes de membresía"

    def ready(self):
        from apps.applications.services import count_form_responses
        from apps.dynamicforms.responses import register_response_counter
        from core.services import register_constraint_message

        # Primer contador real de RF-24: hasta ahora ningún flujo generaba
        # respuestas, así que la inmutabilidad de los formularios nunca se
        # activaba de verdad.
        register_response_counter("solicitudes", count_form_responses)

        register_constraint_message(
            "uniq_pending_application_per_club",
            "Ya tienes una solicitud pendiente en este club.",
            code="already_pending",
        )
        register_constraint_message(
            "chk_rejection_requires_feedback",
            "Debes explicar el motivo del rechazo (RN-5).",
            code="rejection_feedback_required",
        )
