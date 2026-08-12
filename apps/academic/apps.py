from django.apps import AppConfig


class AcademicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.academic"
    label = "academic"
    verbose_name = "Calendario académico"

    def ready(self):
        from core.services import register_constraint_message

        # Los mensajes viven junto a la app que declara el constraint, para que
        # la regla y su texto no se separen con el tiempo.
        register_constraint_message(
            "uniq_single_active_pao",
            "Ya existe un período académico activo. Solo puede haber uno a la vez.",
            code="single_active_pao",
        )
        register_constraint_message(
            "chk_pao_end_after_start",
            "La fecha de fin debe ser posterior a la fecha de inicio.",
            code="invalid_pao_dates",
        )
