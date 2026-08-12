from django.apps import AppConfig


class DynamicFormsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # 'dynamicforms' y no 'forms': ese nombre colisiona con django.forms y
    # produce importaciones ambiguas difíciles de diagnosticar.
    name = "apps.dynamicforms"
    label = "dynamicforms"
    verbose_name = "Formularios dinámicos"

    def ready(self):
        from core.services import register_constraint_message

        register_constraint_message(
            "uniq_form_version_per_family",
            "Ya existe esa versión del formulario.",
            code="duplicate_form_version",
        )
