"""
Punto de entrada WSGI.

AlwaysData apunta su sitio a este archivo y espera encontrar el callable
``application``.

El módulo de settings se resuelve leyendo primero el ``.env``, de modo que
``DJANGO_SETTINGS_MODULE=config.settings.prod`` dentro de ese archivo surta
efecto. Si el panel del alojamiento define la variable en el entorno del sitio,
esa gana: el ``.env`` no pisa lo que ya está puesto.
"""

from config.bootstrap import load_environment

load_environment()

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
