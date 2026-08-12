from django.apps import AppConfig


class CatalogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # El paquete vive en apps/, pero la etiqueta debe ser corta: las referencias
    # por cadena ("catalogs.Faculty") se resuelven contra el label, no el name.
    name = "apps.catalogs"
    label = "catalogs"
    verbose_name = "Catálogos"
