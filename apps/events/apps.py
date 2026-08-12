from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.events"
    label = "events"
    verbose_name = "Eventos"

    def ready(self):
        from apps.dynamicforms.responses import register_response_counter
        from apps.events.services.registration import count_form_responses
        from core.services import register_constraint_message

        # Segundo contador real de RF-24: las inscripciones a eventos también
        # dejan respuestas ligadas a una versión concreta del formulario.
        register_response_counter("inscripciones", count_form_responses)

        register_constraint_message(
            "uniq_event_attendance",
            "Esta credencial ya registró asistencia.",
            code="qr_already_used",
        )
        register_constraint_message(
            "uniq_event_registration",
            "Ya estás inscrito en este evento.",
            code="already_registered",
        )
        register_constraint_message(
            "uniq_event_staff",
            "Esa persona ya está asignada como staff del evento.",
            code="duplicate_staff",
        )
        register_constraint_message(
            "chk_event_end_after_start",
            "El fin del evento debe ser posterior al inicio.",
            code="invalid_event_dates",
        )
