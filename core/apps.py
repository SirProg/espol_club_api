from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Núcleo compartido: contratos, no modelos.

    Se declara como app instalada aunque no tenga tablas propias porque Django
    solo descubre los ``management/commands`` de las apps de INSTALLED_APPS, y
    aquí viven los comandos de alcance transversal al proyecto.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    label = "core"
    verbose_name = "Núcleo"
